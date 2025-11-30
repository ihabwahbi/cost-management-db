#!/usr/bin/env python3
"""
Lineage Oracle Builder

Builds a data lineage graph that tracks how data flows through the pipeline.
This enables:
  - trace_lineage(): Trace column/file dependencies upstream or downstream
  - predict_impact(): Predict what breaks when a file changes
  - find_path(): Find the data path from source to database

Graph Structure:
  Nodes: files, scripts, columns, tables
  Edges: INPUT, OUTPUT, TRANSFORMS, MAPS_TO, DEPENDS_ON

Output: pipeline-context/lineage/graph.json

Usage:
    python3 scripts/build_lineage_graph.py
"""

import ast
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict

# Paths
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent
PIPELINE_CONTEXT_DIR = PROJECT_ROOT / "pipeline-context"
LINEAGE_DIR = PIPELINE_CONTEXT_DIR / "lineage"
OUTPUT_FILE = LINEAGE_DIR / "graph.json"
PIPELINE_MAP_FILE = PROJECT_ROOT / "pipeline-map.json"


def sort_nested_lists(obj: Any) -> Any:
    """
    Recursively sort all lists in a nested data structure for deterministic JSON output.
    
    This ensures that json.dump produces identical output across runs,
    preventing pre-commit hook loops from non-deterministic list ordering.
    """
    if isinstance(obj, dict):
        return {k: sort_nested_lists(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        # Sort list items if they're sortable (strings, numbers)
        sorted_items = [sort_nested_lists(item) for item in obj]
        try:
            # Try to sort - works for lists of strings, numbers, etc.
            return sorted(sorted_items, key=lambda x: str(x) if not isinstance(x, (str, int, float)) else x)
        except TypeError:
            # If items aren't comparable, return as-is
            return sorted_items
    elif isinstance(obj, set):
        return sorted(sort_nested_lists(item) for item in obj)
    return obj


class LineageGraphBuilder:
    """Builds a lineage graph from the codebase."""
    
    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self.edges: List[Dict] = []
        self.column_operations: List[Dict] = []
        # Fix 2: Track variable-to-column mappings for data flow analysis
        self.variable_sources: Dict[str, Dict[str, Set[str]]] = {}  # {script: {var: {columns}}}
        # Fix 3: Track column access patterns for tiered impact
        self.column_access: Dict[str, List[Dict]] = defaultdict(list)  # {column: [{script, type}]}
    
    def add_node(self, node_id: str, node_type: str, **properties):
        """Add a node to the graph."""
        self.nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            **properties
        }
    
    def add_edge(self, source: str, target: str, edge_type: str, **properties):
        """Add an edge to the graph."""
        self.edges.append({
            "source": source,
            "target": target,
            "type": edge_type,
            **properties
        })
    
    def load_pipeline_map(self) -> Optional[Dict]:
        """Load the existing pipeline map."""
        if not PIPELINE_MAP_FILE.exists():
            print("Warning: pipeline-map.json not found. Run generate_pipeline_map.py first.")
            return None
        
        with open(PIPELINE_MAP_FILE) as f:
            return json.load(f)
    
    def extract_file_nodes(self, pipeline_map: Dict):
        """Extract file nodes from data_files."""
        data_files = pipeline_map.get("data_files", {})
        
        for folder, files in data_files.items():
            stage = {
                "raw": "source",
                "intermediate": "intermediate",
                "import-ready": "output"
            }.get(folder, folder)
            
            for filename in files:
                node_id = f"file:data/{folder}/{filename}"
                self.add_node(
                    node_id,
                    "file",
                    path=f"data/{folder}/{filename}",
                    stage=stage,
                    folder=folder
                )
    
    def extract_script_nodes(self, pipeline_map: Dict):
        """Extract script nodes and their I/O relationships."""
        for script in pipeline_map.get("scripts", []):
            node_id = f"script:{script['name']}"
            
            self.add_node(
                node_id,
                "script",
                name=script["name"],
                path=script.get("path", ""),
                stage=script.get("stage", ""),
                functions=[f["name"] for f in script.get("functions", [])]
            )
            
            # Add INPUT edges
            for input_file in script.get("inputs", []):
                file_node_id = f"file:{input_file}"
                # Ensure file node exists
                if file_node_id not in self.nodes:
                    self.add_node(file_node_id, "file", path=input_file)
                self.add_edge(file_node_id, node_id, "INPUT")
            
            # Add OUTPUT edges
            for output_file in script.get("outputs", []):
                file_node_id = f"file:{output_file}"
                if file_node_id not in self.nodes:
                    self.add_node(file_node_id, "file", path=output_file)
                self.add_edge(node_id, file_node_id, "OUTPUT")
            
            # Add DEPENDS_ON edges (script dependencies)
            for dep in script.get("dependencies", []):
                self.add_edge(f"script:{dep}", node_id, "DEPENDS_ON")
    
    def extract_table_nodes(self, pipeline_map: Dict):
        """Extract database table nodes."""
        for table in pipeline_map.get("schema_tables", []):
            node_id = f"table:{table['name']}"
            
            columns = []
            for col in table.get("columns", []):
                columns.append(col["name"])
                
                # Also create column nodes for DB columns
                col_node_id = f"db_column:{table['name']}.{col['name']}"
                self.add_node(
                    col_node_id,
                    "db_column",
                    table=table["name"],
                    column=col["name"],
                    data_type=col.get("type", ""),
                    constraints={
                        "primary_key": col.get("primary_key", False),
                        "not_null": col.get("not_null", False),
                        "references": col.get("references"),
                    }
                )
            
            self.add_node(
                node_id,
                "table",
                name=table["name"],
                file=table.get("file", ""),
                columns=columns
            )
    
    def extract_column_nodes_from_scripts(self):
        """Extract column operations from Python scripts."""
        stage_dirs = ["stage1_clean", "stage2_transform", "stage3_prepare"]
        
        for stage_dir in stage_dirs:
            stage_path = SCRIPTS_DIR / stage_dir
            if not stage_path.exists():
                continue
            
            for script_path in stage_path.glob("*.py"):
                self._extract_columns_from_file(script_path)
    
    def _extract_columns_from_file(self, file_path: Path):
        """Extract column operations from a single Python file."""
        content = file_path.read_text()
        rel_path = str(file_path.relative_to(PROJECT_ROOT))
        script_name = file_path.stem
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return
        
        # Fix 2: First pass - build variable-to-column mapping for this script
        script_vars = self._build_variable_mapping(tree, script_name)
        self.variable_sources[script_name] = script_vars
        
        for node in ast.walk(tree):
            # Column assignments: df["col"] = expression
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Subscript):
                        target_col = self._extract_column_from_subscript(target)
                        if target_col:
                            # Fix 2: Get source columns including variable tracing
                            source_cols = self._find_source_columns_with_vars(node.value, script_vars)
                            
                            # Create/update column node
                            col_node_id = f"column:{target_col}"
                            if col_node_id not in self.nodes:
                                self.add_node(col_node_id, "column", name=target_col, created_by=[])
                            
                            # Track where column is created/modified
                            self.nodes[col_node_id].setdefault("created_by", [])
                            self.nodes[col_node_id]["created_by"].append(
                                f"{rel_path}:{node.lineno}"
                            )
                            
                            # Fix 3: Track column access pattern (WRITES)
                            self.column_access[target_col].append({
                                "script": script_name,
                                "type": "WRITES",
                                "line": node.lineno,
                                "file": rel_path
                            })
                            
                            # Add TRANSFORMS edges from source columns
                            for source_col in source_cols:
                                source_node_id = f"column:{source_col}"
                                if source_node_id not in self.nodes:
                                    self.add_node(source_node_id, "column", name=source_col)
                                
                                # Fix 3: Track column access pattern (READS)
                                self.column_access[source_col].append({
                                    "script": script_name,
                                    "type": "READS",
                                    "line": node.lineno,
                                    "file": rel_path
                                })
                                
                                # Try to extract operation
                                try:
                                    operation = ast.unparse(node.value)[:100]
                                except Exception:
                                    operation = "..."
                                
                                self.add_edge(
                                    source_node_id,
                                    col_node_id,
                                    "TRANSFORMS",
                                    script=script_name,
                                    file=rel_path,
                                    line=node.lineno,
                                    operation=operation
                                )
                            
                            # Fix 2: If no source columns found but value is a variable, create edge from variable sources
                            if not source_cols and isinstance(node.value, ast.Name):
                                var_name = node.value.id
                                if var_name in script_vars:
                                    for var_source_col in script_vars[var_name]:
                                        source_node_id = f"column:{var_source_col}"
                                        if source_node_id not in self.nodes:
                                            self.add_node(source_node_id, "column", name=var_source_col)
                                        
                                        self.add_edge(
                                            source_node_id,
                                            col_node_id,
                                            "TRANSFORMS",
                                            script=script_name,
                                            file=rel_path,
                                            line=node.lineno,
                                            operation=f"via variable '{var_name}'",
                                            traced_variable=var_name
                                        )
            
            # Merge operations create implicit column dependencies
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == "merge":
                    # Look for on= parameter
                    for kw in node.keywords:
                        if kw.arg == "on":
                            if isinstance(kw.value, ast.Constant):
                                join_col_val = kw.value.value
                                if isinstance(join_col_val, str):
                                    join_col: str = join_col_val
                                    col_node_id = f"column:{join_col}"
                                    if col_node_id not in self.nodes:
                                        self.add_node(col_node_id, "column", name=join_col)
                                    self.nodes[col_node_id].setdefault("used_in_joins", [])
                                    self.nodes[col_node_id]["used_in_joins"].append(
                                        f"{rel_path}:{node.lineno}"
                                    )
                                    # Fix 3: Track as READS for merge operations
                                    self.column_access[join_col].append({
                                        "script": script_name,
                                        "type": "READS",
                                        "line": node.lineno,
                                        "file": rel_path,
                                        "context": "merge_join"
                                    })
    
    def _extract_column_from_subscript(self, target: ast.Subscript) -> Optional[str]:
        """
        Extract column name from subscript target.
        
        Fix 1: Handles both:
          - df["col"] = value  (slice is Constant)
          - df.loc[mask, "col"] = value  (slice is Tuple)
        """
        # Simple case: df["col"]
        if isinstance(target.slice, ast.Constant):
            val = target.slice.value
            if isinstance(val, str):
                return val
        
        # Fix 1: Handle df.loc[mask, "col"] - slice is a Tuple
        if isinstance(target.slice, ast.Tuple):
            for elt in target.slice.elts:
                if isinstance(elt, ast.Constant):
                    val = elt.value
                    if isinstance(val, str):
                        # Return the first string constant (the column name)
                        return val
        
        return None
    
    def _build_variable_mapping(self, tree: ast.AST, script_name: str) -> Dict[str, Set[str]]:
        """
        Fix 2: Build a mapping of variable names to the columns they reference.
        
        This enables tracing through intermediate variables like:
            is_ops_vendor = po_df["Main Vendor SLB Vendor Category"] == "OPS"
            output_df["fmt_po"] = is_ops_vendor
        
        We can now trace: fmt_po <- Main Vendor SLB Vendor Category
        
        Also handles:
            vendor_category_col = "Main Vendor SLB Vendor Category"
            is_ops = df[vendor_category_col] == "OPS"
        """
        var_to_cols: Dict[str, Set[str]] = {}
        # Track string constant variables for column name resolution
        string_vars: Dict[str, str] = {}
        
        # First pass: collect string constant assignments
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        # Check if assigning a string constant (likely a column name)
                        if isinstance(node.value, ast.Constant):
                            val = node.value.value
                            if isinstance(val, str):
                                string_vars[var_name] = val
        
        # Second pass: build variable-to-column mapping
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        # Find all column references in the right-hand side
                        cols = self._find_source_columns_extended(node.value, string_vars)
                        if cols:
                            var_to_cols[var_name] = cols
        
        return var_to_cols
    
    def _find_source_columns_extended(self, node: ast.AST, string_vars: Dict[str, str]) -> Set[str]:
        """
        Find all column references including those using variable names.
        
        Handles:
            df["column"]           -> "column"
            df[column_var]         -> resolve column_var from string_vars
        """
        columns = set()
        
        for child in ast.walk(node):
            if isinstance(child, ast.Subscript):
                # Case 1: Direct string literal df["column"]
                if isinstance(child.slice, ast.Constant):
                    val = child.slice.value
                    if isinstance(val, str):
                        columns.add(val)
                # Case 2: Variable reference df[column_var]
                elif isinstance(child.slice, ast.Name):
                    var_name = child.slice.id
                    if var_name in string_vars:
                        columns.add(string_vars[var_name])
        
        return columns
    
    def _find_source_columns_with_vars(self, node: ast.AST, script_vars: Dict[str, Set[str]]) -> Set[str]:
        """
        Fix 2: Find source columns, including those referenced through variables.
        """
        columns = self._find_source_columns(node)
        
        # Also check for variable references
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                var_name = child.id
                if var_name in script_vars:
                    columns.update(script_vars[var_name])
        
        return columns
    
    def _find_source_columns(self, node: ast.AST) -> Set[str]:
        """Find all column references in an expression."""
        columns = set()
        
        for child in ast.walk(node):
            if isinstance(child, ast.Subscript):
                if isinstance(child.slice, ast.Constant) and isinstance(child.slice.value, str):
                    columns.add(child.slice.value)
        
        return columns
    
    def extract_column_mappings(self, pipeline_map: Dict):
        """Map CSV columns to DB columns using column_mappings."""
        column_mappings = pipeline_map.get("column_mappings", {})
        
        for mapping_name, mappings in column_mappings.items():
            if isinstance(mappings, dict):
                # Determine target table from mapping name
                if "PO_LINE_ITEMS" in mapping_name:
                    target_table = "po_line_items"
                elif "PO_TRANSACTIONS" in mapping_name:
                    target_table = "po_transactions"
                else:
                    continue
                
                for csv_col, db_col in mappings.items():
                    csv_node_id = f"column:{csv_col}"
                    db_node_id = f"db_column:{target_table}.{db_col}"
                    
                    # Ensure nodes exist
                    if csv_node_id not in self.nodes:
                        self.add_node(csv_node_id, "column", name=csv_col)
                    
                    if db_node_id in self.nodes:
                        self.add_edge(
                            csv_node_id,
                            db_node_id,
                            "MAPS_TO",
                            table=target_table
                        )
    
    def build_graph(self) -> Dict:
        """Build the complete lineage graph."""
        print("=" * 60)
        print("Building Lineage Graph")
        print("=" * 60)
        
        # Load pipeline map
        print("\n[1/6] Loading pipeline map...")
        pipeline_map = self.load_pipeline_map()
        if not pipeline_map:
            return {"error": "Pipeline map not found"}
        
        # Extract nodes
        print("[2/6] Extracting file nodes...")
        self.extract_file_nodes(pipeline_map)
        
        print("[3/6] Extracting script nodes...")
        self.extract_script_nodes(pipeline_map)
        
        print("[4/6] Extracting table nodes...")
        self.extract_table_nodes(pipeline_map)
        
        print("[5/6] Extracting column operations from scripts...")
        self.extract_column_nodes_from_scripts()
        
        print("[6/6] Mapping columns to database...")
        self.extract_column_mappings(pipeline_map)
        
        # Build the output (no timestamp to avoid unnecessary git changes)
        graph = {
            "version": "2.0.0",  # Version bump for new features
            "description": "Data lineage graph for Context Oracle - trace data flow with variable tracking",
            "nodes": self.nodes,
            "edges": self.edges,
            # Fix 3: Include column access patterns for tiered impact analysis
            "column_access": {col: accesses for col, accesses in self.column_access.items()},
            # Fix 2: Include variable-to-column mappings
            "variable_sources": {
                script: {var: list(cols) for var, cols in var_map.items()}
                for script, var_map in self.variable_sources.items()
            },
            "stats": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "nodes_by_type": self._count_by_type(self.nodes),
                "edges_by_type": self._count_edges_by_type(self.edges),
                "columns_tracked": len(self.column_access),
                "variables_traced": sum(len(v) for v in self.variable_sources.values())
            }
        }
        
        return graph
    
    def _count_by_type(self, nodes: Dict) -> Dict[str, int]:
        """Count nodes by type."""
        counts = defaultdict(int)
        for node in nodes.values():
            counts[node.get("type", "unknown")] += 1
        return dict(counts)
    
    def _count_edges_by_type(self, edges: List) -> Dict[str, int]:
        """Count edges by type."""
        counts = defaultdict(int)
        for edge in edges:
            counts[edge.get("type", "unknown")] += 1
        return dict(counts)
    
    # Query methods for the lineage oracle
    
    def trace_upstream(self, node_id: str, max_depth: int = 10) -> List[Dict]:
        """Trace all nodes upstream from the given node."""
        visited = set()
        result = []
        
        def _trace(current_id: str, depth: int):
            if current_id in visited or depth > max_depth:
                return
            visited.add(current_id)
            
            for edge in self.edges:
                if edge["target"] == current_id:
                    source = edge["source"]
                    result.append({
                        "node": source,
                        "edge_type": edge["type"],
                        "depth": depth,
                        **{k: v for k, v in edge.items() if k not in ["source", "target", "type"]}
                    })
                    _trace(source, depth + 1)
        
        _trace(node_id, 0)
        return result
    
    def trace_downstream(self, node_id: str, max_depth: int = 10) -> List[Dict]:
        """Trace all nodes downstream from the given node."""
        visited = set()
        result = []
        
        def _trace(current_id: str, depth: int):
            if current_id in visited or depth > max_depth:
                return
            visited.add(current_id)
            
            for edge in self.edges:
                if edge["source"] == current_id:
                    target = edge["target"]
                    result.append({
                        "node": target,
                        "edge_type": edge["type"],
                        "depth": depth,
                        **{k: v for k, v in edge.items() if k not in ["source", "target", "type"]}
                    })
                    _trace(target, depth + 1)
        
        _trace(node_id, 0)
        return result
    
    def predict_impact(self, script_name: str) -> Dict:
        """
        Predict the impact of changing a script.
        
        Fix 3: Returns tiered impact classification:
          - direct_writers: Scripts that WRITE to the same columns
          - column_readers: Scripts that READ columns this script WRITES
          - file_consumers: Scripts that consume output files
          - passthrough: Scripts that just pass data through
        """
        script_id = f"script:{script_name}"
        
        if script_id not in self.nodes:
            return {"error": f"Script {script_name} not found"}
        
        # Find all outputs of this script
        outputs = []
        for edge in self.edges:
            if edge["source"] == script_id and edge["type"] == "OUTPUT":
                outputs.append(edge["target"])
        
        # Fix 3: Find columns this script WRITES
        columns_written = set()
        for col, accesses in self.column_access.items():
            for access in accesses:
                if access["script"] == script_name and access["type"] == "WRITES":
                    columns_written.add(col)
        
        # Fix 3: Tiered impact classification
        direct_writers = set()      # Scripts that also WRITE to same columns
        column_readers = set()       # Scripts that READ columns we WRITE
        file_consumers = set()       # Scripts that consume our output files
        passthrough_scripts = set()  # Scripts that just pass through
        
        # Find scripts that interact with columns we write
        for col in columns_written:
            if col in self.column_access:
                for access in self.column_access[col]:
                    other_script = access["script"]
                    if other_script != script_name:
                        if access["type"] == "WRITES":
                            direct_writers.add(other_script)
                        elif access["type"] == "READS":
                            column_readers.add(other_script)
        
        # Find scripts that consume output files
        for output in outputs:
            downstream = self.trace_downstream(output)
            for item in downstream:
                if item["node"].startswith("script:"):
                    other_script = item["node"].replace("script:", "")
                    if other_script != script_name:
                        # If not already a column reader/writer, it's a file consumer
                        if other_script not in column_readers and other_script not in direct_writers:
                            file_consumers.add(other_script)
        
        # All affected scripts
        all_affected = direct_writers | column_readers | file_consumers
        
        # Find passthrough (scripts in dependency chain but not directly interacting)
        for edge in self.edges:
            if edge["type"] == "DEPENDS_ON":
                dep_script = edge["source"].replace("script:", "")
                if dep_script == script_name:
                    downstream_script = edge["target"].replace("script:", "")
                    if downstream_script not in all_affected:
                        passthrough_scripts.add(downstream_script)
        
        # Calculate risk level based on tiered impact
        risk_level = "low"
        if len(column_readers) >= 2 or len(direct_writers) >= 1:
            risk_level = "high"
        elif len(column_readers) >= 1 or len(file_consumers) >= 2:
            risk_level = "medium"
        
        return {
            "script": script_name,
            "outputs": [o.replace("file:", "") for o in outputs],
            "columns_modified": list(columns_written),
            # Fix 3: Tiered classification
            "tiered_impact": {
                "direct_writers": list(direct_writers),
                "column_readers": list(column_readers),
                "file_consumers": list(file_consumers),
                "passthrough": list(passthrough_scripts)
            },
            # Legacy format for backward compatibility
            "affected_scripts": list(all_affected),
            "affected_columns": list(columns_written),
            "risk_level": risk_level,
            "recommendation": self._get_recommendation(risk_level, column_readers, direct_writers, columns_written)
        }
    
    def _get_recommendation(self, risk_level: str, column_readers: Set[str], 
                           direct_writers: Set[str], columns_written: Set[str]) -> str:
        """Generate recommendation based on tiered impact."""
        if risk_level == "high":
            parts = []
            if direct_writers:
                parts.append(f"{len(direct_writers)} scripts also write to same columns")
            if column_readers:
                parts.append(f"{len(column_readers)} scripts read columns you modify")
            detail = "; ".join(parts) if parts else f"affects {len(columns_written)} columns"
            return f"High-risk change: {detail}. Test affected scripts: {list(column_readers)[:3]}"
        elif risk_level == "medium":
            return f"Medium-risk change: {len(column_readers)} downstream readers. Verify transformations."
        else:
            return "Low-risk change: limited downstream impact."


def build_lineage_graph():
    """Build and save the lineage graph."""
    builder = LineageGraphBuilder()
    graph = builder.build_graph()
    
    if "error" in graph:
        print(f"Error: {graph['error']}")
        return graph
    
    # Save the graph (sort nested lists for deterministic output)
    LINEAGE_DIR.mkdir(parents=True, exist_ok=True)
    sorted_graph = sort_nested_lists(graph)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(sorted_graph, f, indent=2, sort_keys=True)
    
    print("\n" + "=" * 60)
    print("Lineage Graph Generated!")
    print("=" * 60)
    print(f"\nOutput: {OUTPUT_FILE}")
    print(f"\nStatistics:")
    print(f"  Total nodes: {graph['stats']['total_nodes']}")
    print(f"  Total edges: {graph['stats']['total_edges']}")
    print(f"\n  Nodes by type:")
    for node_type, count in graph['stats']['nodes_by_type'].items():
        print(f"    {node_type}: {count}")
    print(f"\n  Edges by type:")
    for edge_type, count in graph['stats']['edges_by_type'].items():
        print(f"    {edge_type}: {count}")
    
    # Demo: predict impact
    print("\n" + "-" * 60)
    print("Demo: Impact prediction for 05_calculate_cost_impact")
    print("-" * 60)
    impact = builder.predict_impact("05_calculate_cost_impact")
    print(f"  Outputs: {impact.get('outputs', [])}")
    print(f"  Affected scripts: {impact.get('affected_scripts', [])}")
    print(f"  Affected columns: {len(impact.get('affected_columns', []))} columns")
    print(f"  Risk level: {impact.get('risk_level', 'unknown')}")
    print(f"  Recommendation: {impact.get('recommendation', '')}")
    
    return graph


if __name__ == "__main__":
    build_lineage_graph()
