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


class LineageGraphBuilder:
    """Builds a lineage graph from the codebase."""
    
    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self.edges: List[Dict] = []
        self.column_operations: List[Dict] = []
    
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
        
        for node in ast.walk(tree):
            # Column assignments: df["col"] = expression
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Subscript):
                        if isinstance(target.slice, ast.Constant) and isinstance(target.slice.value, str):
                            target_col = target.slice.value
                            source_cols = self._find_source_columns(node.value)
                            
                            # Create/update column node
                            col_node_id = f"column:{target_col}"
                            if col_node_id not in self.nodes:
                                self.add_node(col_node_id, "column", name=target_col, created_by=[])
                            
                            # Track where column is created/modified
                            self.nodes[col_node_id].setdefault("created_by", [])
                            self.nodes[col_node_id]["created_by"].append(
                                f"{rel_path}:{node.lineno}"
                            )
                            
                            # Add TRANSFORMS edges from source columns
                            for source_col in source_cols:
                                source_node_id = f"column:{source_col}"
                                if source_node_id not in self.nodes:
                                    self.add_node(source_node_id, "column", name=source_col)
                                
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
            
            # Merge operations create implicit column dependencies
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == "merge":
                    # Look for on= parameter
                    for kw in node.keywords:
                        if kw.arg == "on":
                            if isinstance(kw.value, ast.Constant):
                                join_col = kw.value.value
                                col_node_id = f"column:{join_col}"
                                if col_node_id not in self.nodes:
                                    self.add_node(col_node_id, "column", name=join_col)
                                self.nodes[col_node_id].setdefault("used_in_joins", [])
                                self.nodes[col_node_id]["used_in_joins"].append(
                                    f"{rel_path}:{node.lineno}"
                                )
    
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
        
        # Build the output
        graph = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "description": "Data lineage graph for Context Oracle - trace data flow",
            "nodes": self.nodes,
            "edges": self.edges,
            "stats": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "nodes_by_type": self._count_by_type(self.nodes),
                "edges_by_type": self._count_edges_by_type(self.edges)
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
        """Predict the impact of changing a script."""
        script_id = f"script:{script_name}"
        
        if script_id not in self.nodes:
            return {"error": f"Script {script_name} not found"}
        
        # Find all outputs of this script
        outputs = []
        for edge in self.edges:
            if edge["source"] == script_id and edge["type"] == "OUTPUT":
                outputs.append(edge["target"])
        
        # Find all scripts/columns that depend on these outputs
        affected_scripts = set()
        affected_columns = set()
        
        for output in outputs:
            downstream = self.trace_downstream(output)
            for item in downstream:
                if item["node"].startswith("script:"):
                    affected_scripts.add(item["node"].replace("script:", ""))
                elif item["node"].startswith("column:"):
                    affected_columns.add(item["node"].replace("column:", ""))
        
        # Calculate risk level
        risk_level = "low"
        if len(affected_scripts) >= 3 or len(affected_columns) >= 5:
            risk_level = "high"
        elif len(affected_scripts) >= 1 or len(affected_columns) >= 2:
            risk_level = "medium"
        
        return {
            "script": script_name,
            "outputs": [o.replace("file:", "") for o in outputs],
            "affected_scripts": list(affected_scripts),
            "affected_columns": list(affected_columns),
            "risk_level": risk_level,
            "recommendation": self._get_recommendation(risk_level, affected_scripts)
        }
    
    def _get_recommendation(self, risk_level: str, affected_scripts: Set[str]) -> str:
        """Generate recommendation based on risk level."""
        if risk_level == "high":
            return f"High-risk change: affects {len(affected_scripts)} downstream scripts. Test all stages thoroughly."
        elif risk_level == "medium":
            return "Medium-risk change: verify downstream transformations after modification."
        else:
            return "Low-risk change: limited downstream impact."


def build_lineage_graph():
    """Build and save the lineage graph."""
    builder = LineageGraphBuilder()
    graph = builder.build_graph()
    
    if "error" in graph:
        print(f"Error: {graph['error']}")
        return graph
    
    # Save the graph
    LINEAGE_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(graph, f, indent=2)
    
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
