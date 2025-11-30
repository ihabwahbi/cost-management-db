#!/usr/bin/env python3
"""
Symbol Registry Builder

Builds a comprehensive symbol index for the Context Oracle.
This registry enables anti-hallucination verification - agents can verify
any symbol reference exists before using it in code.

Extracts:
  - functions: All function definitions with signatures, docstrings, line numbers
  - constants: All UPPER_CASE constants from config files
  - columns: CSV column names from data files + DB columns from schema
  - tables: Database table definitions from TypeScript schema

Output: pipeline-context/registry/symbols.json

Usage:
    python3 scripts/build_symbol_registry.py
"""

import ast
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Set, Optional
from dataclasses import dataclass, asdict

# Paths
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent
PIPELINE_CONTEXT_DIR = PROJECT_ROOT / "pipeline-context"
OUTPUT_FILE = PIPELINE_CONTEXT_DIR / "registry" / "symbols.json"
TS_EXTRACTOR = SCRIPTS_DIR / "extract-schema.ts"


@dataclass
class FunctionSymbol:
    """Function definition extracted from Python."""
    name: str
    file: str
    line: int
    signature: str
    docstring: Optional[str]
    args: List[str]
    return_type: Optional[str]
    calls: List[str]  # Functions this function calls
    called_by: List[str]  # Functions that call this


@dataclass
class ConstantSymbol:
    """Constant definition (UPPER_CASE variables)."""
    name: str
    file: str
    line: int
    value_type: str
    value_preview: str  # Truncated preview for large values


@dataclass
class ColumnSymbol:
    """CSV or database column."""
    name: str
    source_type: str  # "csv" | "database" | "intermediate"
    sources: List[str]  # Files where this column appears
    dtype: Optional[str]
    used_in: List[str]  # Scripts that reference this column
    created_by: Optional[str]  # Script:line that creates this column


@dataclass
class TableSymbol:
    """Database table definition."""
    name: str
    file: str
    columns: List[str]
    primary_key: Optional[str]
    foreign_keys: List[Dict[str, str]]


def extract_functions_from_file(file_path: Path) -> List[FunctionSymbol]:
    """Extract all function definitions from a Python file."""
    content = file_path.read_text()
    rel_path = str(file_path.relative_to(PROJECT_ROOT))
    functions = []
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return functions
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Build signature
            args = [arg.arg for arg in node.args.args]
            
            # Get return annotation if present
            return_type = None
            if node.returns:
                try:
                    return_type = ast.unparse(node.returns)
                except Exception:
                    pass
            
            # Build signature string
            arg_strs = []
            for i, arg in enumerate(node.args.args):
                arg_str = arg.arg
                if arg.annotation:
                    try:
                        arg_str += f": {ast.unparse(arg.annotation)}"
                    except Exception:
                        pass
                arg_strs.append(arg_str)
            
            sig = f"def {node.name}({', '.join(arg_strs)})"
            if return_type:
                sig += f" -> {return_type}"
            
            # Extract function calls within this function
            calls = []
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name):
                        calls.append(child.func.id)
                    elif isinstance(child.func, ast.Attribute):
                        calls.append(child.func.attr)
            
            functions.append(FunctionSymbol(
                name=node.name,
                file=rel_path,
                line=node.lineno,
                signature=sig,
                docstring=ast.get_docstring(node),
                args=args,
                return_type=return_type,
                calls=list(set(calls)),
                called_by=[]  # Populated later
            ))
    
    return functions


def extract_constants_from_file(file_path: Path) -> List[ConstantSymbol]:
    """Extract UPPER_CASE constants from a Python file."""
    content = file_path.read_text()
    rel_path = str(file_path.relative_to(PROJECT_ROOT))
    constants = []
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return constants
    
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    # Check if UPPER_CASE (constant naming convention)
                    if name.isupper() or (name[0].isupper() and '_' in name and name.replace('_', '').isupper()):
                        # Determine value type and preview
                        value_type = type(node.value).__name__
                        if isinstance(node.value, ast.Dict):
                            value_type = "dict"
                            try:
                                preview = ast.unparse(node.value)[:100]
                            except Exception:
                                preview = "{...}"
                        elif isinstance(node.value, ast.List):
                            value_type = "list"
                            try:
                                preview = ast.unparse(node.value)[:100]
                            except Exception:
                                preview = "[...]"
                        elif isinstance(node.value, ast.Constant):
                            value_type = type(node.value.value).__name__
                            preview = str(node.value.value)[:100]
                        else:
                            try:
                                preview = ast.unparse(node.value)[:100]
                            except Exception:
                                preview = "..."
                        
                        constants.append(ConstantSymbol(
                            name=name,
                            file=rel_path,
                            line=node.lineno,
                            value_type=value_type,
                            value_preview=preview
                        ))
    
    return constants


def extract_column_operations(file_path: Path) -> Dict[str, List[Dict]]:
    """Extract column references and modifications from a Python file."""
    content = file_path.read_text()
    rel_path = str(file_path.relative_to(PROJECT_ROOT))
    
    column_refs: Dict[str, List[Dict]] = {}
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return column_refs
    
    for node in ast.walk(tree):
        # df["column"] or df['column'] patterns
        if isinstance(node, ast.Subscript):
            if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                col_name = node.slice.value
                if col_name not in column_refs:
                    column_refs[col_name] = []
                
                # Check if this is an assignment (column creation/modification)
                # We can't easily tell from just this node, so mark as "reference"
                column_refs[col_name].append({
                    "file": rel_path,
                    "line": node.lineno,
                    "type": "reference"
                })
        
        # Look for column assignments: df["col"] = ...
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Subscript):
                    if isinstance(target.slice, ast.Constant) and isinstance(target.slice.value, str):
                        col_name = target.slice.value
                        if col_name not in column_refs:
                            column_refs[col_name] = []
                        column_refs[col_name].append({
                            "file": rel_path,
                            "line": node.lineno,
                            "type": "created"
                        })
    
    return column_refs


def get_csv_columns() -> Dict[str, Dict]:
    """Extract column names from CSV files."""
    try:
        import pandas as pd
    except ImportError:
        return {}
    
    columns = {}
    data_dir = PROJECT_ROOT / "data"
    
    for folder in ["raw", "intermediate", "import-ready"]:
        folder_path = data_dir / folder
        if not folder_path.exists():
            continue
        
        for csv_file in folder_path.glob("*.csv"):
            try:
                # Read just the header
                df = pd.read_csv(csv_file, nrows=0)
                file_path = f"data/{folder}/{csv_file.name}"
                
                for col in df.columns:
                    if col not in columns:
                        columns[col] = {
                            "sources": [],
                            "dtype": None,
                            "source_type": folder
                        }
                    columns[col]["sources"].append(file_path)
                    
                    # Update source_type to most processed version
                    type_order = {"raw": 0, "intermediate": 1, "import-ready": 2}
                    if type_order.get(folder, 0) > type_order.get(columns[col]["source_type"], 0):
                        columns[col]["source_type"] = folder
                        
            except Exception:
                pass
    
    # Get dtypes from a sample read
    for folder in ["import-ready", "intermediate", "raw"]:
        folder_path = data_dir / folder
        if not folder_path.exists():
            continue
        
        for csv_file in folder_path.glob("*.csv"):
            try:
                df = pd.read_csv(csv_file, nrows=100)
                for col, dtype in df.dtypes.items():
                    if col in columns and columns[col]["dtype"] is None:
                        columns[col]["dtype"] = str(dtype)
            except Exception:
                pass
    
    return columns


def get_schema_tables() -> List[TableSymbol]:
    """Extract database tables from TypeScript schema."""
    if not TS_EXTRACTOR.exists():
        return []
    
    try:
        result = subprocess.run(
            ["npx", "ts-node", str(TS_EXTRACTOR)],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=60,
        )
        
        if result.returncode != 0:
            return []
        
        tables_data = json.loads(result.stdout)
        tables = []
        
        for table in tables_data:
            foreign_keys = []
            columns = []
            primary_key = None
            
            for col in table.get("columns", []):
                columns.append(col["name"])
                if col.get("primary_key"):
                    primary_key = col["name"]
                if col.get("references"):
                    foreign_keys.append({
                        "column": col["name"],
                        "references": col["references"]
                    })
            
            tables.append(TableSymbol(
                name=table["name"],
                file=f"src/schema/{table['file']}",
                columns=columns,
                primary_key=primary_key,
                foreign_keys=foreign_keys
            ))
        
        return tables
        
    except Exception as e:
        print(f"Warning: Schema extraction failed: {e}")
        return []


def build_call_graph(functions: List[FunctionSymbol]) -> None:
    """Populate the called_by field for all functions."""
    # Build function name to function mapping
    func_map = {f.name: f for f in functions}
    
    for func in functions:
        for called_name in func.calls:
            if called_name in func_map:
                if func.name not in func_map[called_name].called_by:
                    func_map[called_name].called_by.append(func.name)


def find_similar_symbols(query: str, symbols: Dict[str, Any], limit: int = 5) -> List[Dict]:
    """Find symbols similar to query (for suggestion generation)."""
    from difflib import SequenceMatcher
    
    all_names = []
    
    # Collect all symbol names with their types
    for func in symbols.get("functions", []):
        all_names.append({"name": func["name"], "type": "function", "file": func["file"]})
    
    for const in symbols.get("constants", []):
        all_names.append({"name": const["name"], "type": "constant", "file": const["file"]})
    
    for col_name, col_data in symbols.get("columns", {}).items():
        all_names.append({"name": col_name, "type": "column", "sources": col_data.get("sources", [])})
    
    for table in symbols.get("tables", []):
        all_names.append({"name": table["name"], "type": "table", "file": table["file"]})
    
    # Calculate similarity scores
    scored = []
    query_lower = query.lower()
    
    for item in all_names:
        name_lower = item["name"].lower()
        
        # Use SequenceMatcher for fuzzy matching
        ratio = SequenceMatcher(None, query_lower, name_lower).ratio()
        
        # Boost exact substring matches
        if query_lower in name_lower or name_lower in query_lower:
            ratio = max(ratio, 0.8)
        
        scored.append((ratio, item))
    
    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    
    return [item for score, item in scored[:limit] if score > 0.3]


def generate_symbol_registry():
    """Generate the complete symbol registry."""
    print("=" * 60)
    print("Building Symbol Registry")
    print("=" * 60)
    
    # Collect all Python files
    python_files = []
    stage_dirs = ["stage1_clean", "stage2_transform", "stage3_prepare", "config"]
    
    for stage_dir in stage_dirs:
        stage_path = SCRIPTS_DIR / stage_dir
        if stage_path.exists():
            python_files.extend(stage_path.glob("*.py"))
    
    # Add pipeline.py and this script
    pipeline_script = SCRIPTS_DIR / "pipeline.py"
    if pipeline_script.exists():
        python_files.append(pipeline_script)
    
    # Extract functions
    print("\n[1/5] Extracting functions...")
    all_functions = []
    for py_file in python_files:
        print(f"  Processing: {py_file.name}")
        all_functions.extend(extract_functions_from_file(py_file))
    
    # Build call graph
    print("\n[2/5] Building call graph...")
    build_call_graph(all_functions)
    
    # Extract constants
    print("\n[3/5] Extracting constants...")
    all_constants = []
    config_path = SCRIPTS_DIR / "config" / "column_mappings.py"
    if config_path.exists():
        all_constants.extend(extract_constants_from_file(config_path))
    
    # Extract columns from CSVs and scripts
    print("\n[4/5] Extracting columns...")
    csv_columns = get_csv_columns()
    
    # Merge column usage from scripts
    all_column_refs = {}
    for py_file in python_files:
        refs = extract_column_operations(py_file)
        for col_name, usages in refs.items():
            if col_name not in all_column_refs:
                all_column_refs[col_name] = []
            all_column_refs[col_name].extend(usages)
    
    # Build column symbols
    columns = {}
    
    # Start with CSV columns
    for col_name, col_data in csv_columns.items():
        columns[col_name] = {
            "name": col_name,
            "source_type": col_data["source_type"],
            "sources": col_data["sources"],
            "dtype": col_data["dtype"],
            "used_in": [],
            "created_by": None
        }
    
    # Add script usage info
    for col_name, refs in all_column_refs.items():
        if col_name not in columns:
            columns[col_name] = {
                "name": col_name,
                "source_type": "script",
                "sources": [],
                "dtype": None,
                "used_in": [],
                "created_by": None
            }
        
        for ref in refs:
            file_name = Path(ref["file"]).stem
            if file_name not in columns[col_name]["used_in"]:
                columns[col_name]["used_in"].append(file_name)
            
            if ref["type"] == "created" and columns[col_name]["created_by"] is None:
                columns[col_name]["created_by"] = f"{ref['file']}:{ref['line']}"
    
    # Extract tables
    print("\n[5/5] Extracting database tables...")
    tables = get_schema_tables()
    
    # Build the registry
    registry = {
        "version": "1.0.0",
        "description": "Symbol registry for Context Oracle - verify before use",
        
        "functions": [asdict(f) for f in all_functions],
        "constants": [asdict(c) for c in all_constants],
        "columns": columns,
        "tables": [asdict(t) for t in tables],
        
        "stats": {
            "total_functions": len(all_functions),
            "total_constants": len(all_constants),
            "total_columns": len(columns),
            "total_tables": len(tables),
        }
    }
    
    # Save the registry
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(registry, f, indent=2)
    
    print("\n" + "=" * 60)
    print("Symbol Registry Generated!")
    print("=" * 60)
    print(f"\nOutput: {OUTPUT_FILE}")
    print(f"\nStatistics:")
    print(f"  Functions: {len(all_functions)}")
    print(f"  Constants: {len(all_constants)}")
    print(f"  Columns: {len(columns)}")
    print(f"  Tables: {len(tables)}")
    
    return registry


if __name__ == "__main__":
    generate_symbol_registry()
