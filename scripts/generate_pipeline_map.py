#!/usr/bin/env python3
"""
Pipeline Map Generator (Enhanced)

Generates a comprehensive map of the data pipeline for AI agent context.
Includes:
  - Script metadata with function signatures and line numbers
  - Pandas operation extraction (merge, groupby, filter, etc.)
  - Sample data profiles (dtypes, sample rows, null counts)
  - TypeScript schema extraction (via ts-morph or fallback regex)
  - Common error scenarios for debugging guidance

Outputs:
  - pipeline-map.json: Machine-readable pipeline structure
  - pipeline-map.md: Mermaid diagram for visualization

Usage:
    python3 scripts/generate_pipeline_map.py
"""

import ast
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Paths
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent
OUTPUT_JSON = PROJECT_ROOT / "pipeline-map.json"
OUTPUT_MD = PROJECT_ROOT / "pipeline-map.md"
TS_EXTRACTOR = SCRIPTS_DIR / "extract-schema.ts"


def sort_nested_lists(obj: Any) -> Any:
    """
    Recursively sort all lists in a nested data structure for deterministic JSON output.
    """
    if isinstance(obj, dict):
        return {k: sort_nested_lists(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        sorted_items = [sort_nested_lists(item) for item in obj]
        try:
            return sorted(
                sorted_items,
                key=lambda x: str(x) if not isinstance(x, (str, int, float)) else x,
            )
        except TypeError:
            return sorted_items
    elif isinstance(obj, set):
        return sorted(sort_nested_lists(item) for item in obj)
    return obj


# Pandas operations we care about for understanding transformations
PANDAS_OPS = {
    "merge": "Joins two DataFrames",
    "groupby": "Groups data for aggregation",
    "filter": "Filters rows based on condition",
    "drop": "Removes columns or rows",
    "dropna": "Removes null values",
    "fillna": "Fills null values",
    "rename": "Renames columns",
    "astype": "Converts column types",
    "apply": "Applies function to data",
    "map": "Maps values using dictionary or function",
    "sort_values": "Sorts by column values",
    "to_datetime": "Converts to datetime",
    "str": "String operations",
}


def extract_pandas_operations(tree: ast.AST, content: str) -> List[Dict[str, Any]]:
    """Extract pandas operations from AST for semantic understanding.

    Extracts operations with their arguments and actual code snippets where useful.
    """
    operations = []
    content_lines = content.splitlines()

    def get_code_snippet(lineno: int) -> str:
        """Get the actual line of code for context."""
        if 0 < lineno <= len(content_lines):
            return content_lines[lineno - 1].strip()
        return ""

    def extract_list_or_constant(node) -> Any:
        """Extract value from AST node (handles both single values and lists)."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.List):
            return [e.value for e in node.elts if isinstance(e, ast.Constant)]
        return None

    for node in ast.walk(tree):
        # Look for method calls like df.merge(), df.groupby(), etc.
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                method_name = node.func.attr
                if method_name in PANDAS_OPS:
                    op_info = {
                        "operation": method_name,
                        "description": PANDAS_OPS[method_name],
                        "line": node.lineno,
                        "code_snippet": get_code_snippet(node.lineno),
                    }

                    # Try to extract key arguments
                    if method_name == "merge":
                        for kw in node.keywords:
                            if kw.arg == "on":
                                on_val = extract_list_or_constant(kw.value)
                                if isinstance(on_val, list):
                                    op_info["on_columns"] = on_val
                                elif on_val:
                                    op_info["on_column"] = on_val
                            elif kw.arg == "how" and isinstance(kw.value, ast.Constant):
                                op_info["join_type"] = kw.value.value
                            elif kw.arg in ["left_on", "right_on"]:
                                val = extract_list_or_constant(kw.value)
                                if val:
                                    op_info[kw.arg] = val

                    elif method_name == "groupby":
                        if node.args:
                            val = extract_list_or_constant(node.args[0])
                            if isinstance(val, list):
                                op_info["group_columns"] = val
                            elif val:
                                op_info["group_column"] = val

                    elif method_name == "drop":
                        for kw in node.keywords:
                            if kw.arg == "columns":
                                cols = extract_list_or_constant(kw.value)
                                if cols:
                                    op_info["dropped_columns"] = (
                                        cols if isinstance(cols, list) else [cols]
                                    )

                    elif method_name == "rename":
                        for kw in node.keywords:
                            if kw.arg == "columns" and isinstance(kw.value, ast.Dict):
                                renames = {}
                                for k, v in zip(kw.value.keys, kw.value.values):
                                    if isinstance(k, ast.Constant) and isinstance(
                                        v, ast.Constant
                                    ):
                                        renames[k.value] = v.value
                                if renames:
                                    op_info["column_renames"] = renames

                    operations.append(op_info)

        # Look for column assignments: df['new_col'] = ...
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Subscript):
                    if isinstance(target.slice, ast.Constant):
                        col_name = target.slice.value
                        snippet = get_code_snippet(node.lineno)
                        operations.append(
                            {
                                "operation": "column_assign",
                                "description": f"Creates/modifies column '{col_name}'",
                                "column": col_name,
                                "line": node.lineno,
                                "code_snippet": snippet,
                            }
                        )

        # Look for boolean filtering: df[mask] or df[condition]
        if isinstance(node, ast.Assign):
            # Check if RHS is a subscript with a boolean condition
            if isinstance(node.value, ast.Subscript):
                slice_node = node.value.slice
                is_filter = False

                # df[mask] where mask is a variable
                if isinstance(slice_node, ast.Name):
                    is_filter = True
                # df[~mask]
                elif isinstance(slice_node, ast.UnaryOp) and isinstance(
                    slice_node.op, ast.Invert
                ):
                    is_filter = True
                # df[df['col'] == val]
                elif isinstance(slice_node, ast.Compare):
                    is_filter = True

                if is_filter:
                    snippet = get_code_snippet(node.lineno)
                    # Avoid duplicate if already captured as column_assign
                    if not any(
                        op.get("line") == node.lineno
                        and op.get("operation") == "column_assign"
                        for op in operations
                    ):
                        operations.append(
                            {
                                "operation": "boolean_filter",
                                "description": "Filters rows based on boolean condition",
                                "line": node.lineno,
                                "code_snippet": snippet,
                            }
                        )

    return operations


def extract_transformation_semantics(
    func_node: ast.FunctionDef, content: str
) -> Dict[str, Any]:
    """Extract semantic meaning from a function's implementation."""
    semantics = {
        "modifies_columns": [],
        "filters_data": False,
        "aggregates": False,
        "joins_data": False,
        "renames_columns": False,
        "type_conversions": False,
    }

    # Get the source code of the function for pattern matching
    try:
        func_source = ast.unparse(func_node) if hasattr(ast, "unparse") else ""
    except Exception:
        func_source = ""

    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            # Check for method calls
            if isinstance(node.func, ast.Attribute):
                method = node.func.attr

                if method in ["merge", "join"]:
                    semantics["joins_data"] = True
                elif method in ["groupby"]:
                    semantics["aggregates"] = True
                elif method in ["filter", "query"]:
                    semantics["filters_data"] = True
                elif method in ["drop", "dropna"]:
                    semantics["filters_data"] = True
                elif method in ["rename"]:
                    semantics["renames_columns"] = True
                elif method in ["astype", "to_datetime", "to_numeric"]:
                    semantics["type_conversions"] = True
                elif method in ["isin"]:
                    semantics["filters_data"] = True
                elif method == "copy":
                    # df[mask].copy() pattern - indicates filtering
                    pass

            # Check for pd.to_datetime, pd.to_numeric calls
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in ["to_datetime", "to_numeric"]:
                    semantics["type_conversions"] = True

        # Detect boolean indexing: df[mask], df[~mask], df[df['col'] == val]
        if isinstance(node, ast.Subscript):
            if isinstance(node.slice, ast.Name):
                # Pattern: df[mask] where mask is a boolean series
                semantics["filters_data"] = True
            elif isinstance(node.slice, ast.UnaryOp) and isinstance(
                node.slice.op, ast.Invert
            ):
                # Pattern: df[~mask]
                semantics["filters_data"] = True
            elif isinstance(node.slice, ast.Compare):
                # Pattern: df[df['col'] == value]
                semantics["filters_data"] = True

        # Track column modifications: df['col'] = ...
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Subscript) and isinstance(
                    target.slice, ast.Constant
                ):
                    col = target.slice.value
                    if col not in semantics["modifies_columns"]:
                        semantics["modifies_columns"].append(col)

    # Also check for common patterns in source
    if func_source:
        if ".copy()" in func_source and "[" in func_source:
            semantics["filters_data"] = True

    return semantics


def get_data_profiles() -> Dict[str, Any]:
    """Extract data profiles from CSV files (dtypes, sample rows, null counts).

    Efficiently reads each file only once using chunked reading for large files.
    """
    try:
        import pandas as pd
    except ImportError:
        return {"error": "pandas not available for profiling"}

    profiles = {}
    data_dir = PROJECT_ROOT / "data"

    # Size threshold for chunked reading (10MB)
    CHUNK_THRESHOLD = 10 * 1024 * 1024

    for folder in ["raw", "intermediate", "import-ready"]:
        folder_path = data_dir / folder
        if not folder_path.exists():
            continue

        for csv_file in folder_path.glob("*.csv"):
            try:
                file_size = csv_file.stat().st_size

                if file_size > CHUNK_THRESHOLD:
                    # Large file: use chunked reading
                    row_count = 0
                    null_counts: Dict[str, int] = {}
                    sample_row = {}
                    dtypes = {}
                    columns = []

                    for i, chunk in enumerate(
                        pd.read_csv(csv_file, chunksize=10000, low_memory=False)
                    ):
                        row_count += len(chunk)

                        # Get sample and dtypes from first chunk
                        if i == 0:
                            columns = list(chunk.columns)
                            dtypes = {
                                col: str(dtype) for col, dtype in chunk.dtypes.items()
                            }
                            sample_row = (
                                chunk.iloc[0].to_dict() if len(chunk) > 0 else {}
                            )

                        # Accumulate null counts
                        chunk_nulls = chunk.isnull().sum()
                        for col, count in chunk_nulls.items():
                            null_counts[col] = null_counts.get(col, 0) + int(count)

                    profile = {
                        "path": f"data/{folder}/{csv_file.name}",
                        "columns": columns,
                        "dtypes": dtypes,
                        "sample_row": sample_row,
                        "row_count": row_count,
                        "null_counts": {
                            col: count
                            for col, count in null_counts.items()
                            if count > 0
                        },
                    }
                else:
                    # Small file: read all at once (more efficient)
                    df = pd.read_csv(csv_file, low_memory=False)

                    null_counts = df.isnull().sum()
                    profile = {
                        "path": f"data/{folder}/{csv_file.name}",
                        "columns": list(df.columns),
                        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                        "sample_row": df.iloc[0].to_dict() if len(df) > 0 else {},
                        "row_count": len(df),
                        "null_counts": {
                            col: int(count)
                            for col, count in null_counts.items()
                            if count > 0
                        },
                    }

                profiles[csv_file.name] = profile

            except Exception as e:
                profiles[csv_file.name] = {"error": str(e)}

    return profiles


def extract_script_metadata(script_path: Path) -> Dict[str, Any]:
    """Extract metadata from a Python script using AST parsing."""
    content = script_path.read_text()

    metadata = {
        "name": script_path.stem,
        "path": str(script_path.relative_to(PROJECT_ROOT)),
        "stage": script_path.parent.name,
        "docstring": None,
        "inputs": [],
        "outputs": [],
        "dependencies": [],
        "functions": [],
        "imports": [],
        "pandas_operations": [],
        "line_count": len(content.splitlines()),
    }

    try:
        tree = ast.parse(content)

        # Extract module docstring
        if ast.get_docstring(tree):
            metadata["docstring"] = ast.get_docstring(tree)

        # Extract pandas operations for semantic understanding
        metadata["pandas_operations"] = extract_pandas_operations(tree, content)

        # Walk the AST
        for node in ast.walk(tree):
            # Extract imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    metadata["imports"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    metadata["imports"].append(node.module)

            # Extract function definitions with enhanced semantics
            elif isinstance(node, ast.FunctionDef):
                func_info = {
                    "name": node.name,
                    "docstring": ast.get_docstring(node),
                    "args": [arg.arg for arg in node.args.args],
                    "line": node.lineno,
                    "semantics": extract_transformation_semantics(node, content),
                }
                metadata["functions"].append(func_info)
    except SyntaxError:
        pass

    # Extract file paths from content using regex
    # Look for patterns like: PROJECT_ROOT / "data" / "raw" / "file.csv"
    path_patterns = [
        r'PROJECT_ROOT\s*/\s*"data"\s*/\s*"(\w+)"\s*/\s*"([^"]+)"',
        r'"data/(\w+)/([^"]+)"',
        r"'data/(\w+)/([^']+)'",
    ]

    for pattern in path_patterns:
        matches = re.findall(pattern, content)
        for folder, filename in matches:
            file_path = f"data/{folder}/{filename}"
            if folder == "raw":
                if file_path not in metadata["inputs"]:
                    metadata["inputs"].append(file_path)
            elif folder == "intermediate":
                # Determine if input or output by context
                if "INPUT" in content.upper() or "LOAD" in content.upper():
                    if file_path not in metadata["inputs"]:
                        metadata["inputs"].append(file_path)
                if "OUTPUT" in content.upper() or "SAVE" in content.upper():
                    if file_path not in metadata["outputs"]:
                        metadata["outputs"].append(file_path)
            elif folder == "import-ready":
                if file_path not in metadata["outputs"]:
                    metadata["outputs"].append(file_path)

    # Parse explicit INPUT_FILE and OUTPUT_FILE assignments
    input_match = re.search(r'INPUT_FILE\s*=.*?"([^"]+)"', content)
    output_match = re.search(r'OUTPUT_FILE\s*=.*?"([^"]+)"', content)

    # Also look for variable assignments with file paths
    for match in re.finditer(
        r'(\w+_FILE)\s*=\s*PROJECT_ROOT\s*/\s*"data"\s*/\s*"(\w+)"\s*/\s*"([^"]+)"',
        content,
    ):
        var_name, folder, filename = match.groups()
        file_path = f"data/{folder}/{filename}"
        if "INPUT" in var_name.upper() or folder == "raw":
            if file_path not in metadata["inputs"]:
                metadata["inputs"].append(file_path)
        elif "OUTPUT" in var_name.upper():
            if file_path not in metadata["outputs"]:
                metadata["outputs"].append(file_path)
        elif folder == "intermediate":
            # Check if it's used as both input and output
            pass

    return metadata


def analyze_dependencies(scripts: List[Dict]) -> List[Dict]:
    """Analyze dependencies between scripts based on file I/O."""
    # Build output -> script map
    output_map = {}
    for script in scripts:
        for output in script["outputs"]:
            output_map[output] = script["name"]

    # Find dependencies
    for script in scripts:
        deps = []
        for input_file in script["inputs"]:
            if input_file in output_map:
                producer = output_map[input_file]
                if producer != script["name"] and producer not in deps:
                    deps.append(producer)
        script["dependencies"] = deps

    return scripts


def get_column_mappings() -> Dict[str, Any]:
    """Extract column mappings from config."""
    config_path = SCRIPTS_DIR / "config" / "column_mappings.py"
    if not config_path.exists():
        return {}

    content = config_path.read_text()
    mappings = {}

    # Extract dictionary definitions
    dict_pattern = r"(\w+_MAPPING)\s*=\s*\{([^}]+)\}"
    for match in re.finditer(dict_pattern, content, re.DOTALL):
        name, dict_content = match.groups()
        # Parse the dictionary content
        items = {}
        for item_match in re.finditer(r'"([^"]+)":\s*"([^"]+)"', dict_content):
            key, value = item_match.groups()
            items[key] = value
        if items:
            mappings[name] = items

    # Extract list definitions
    list_pattern = r"(\w+)\s*=\s*\[([^\]]+)\]"
    for match in re.finditer(list_pattern, content, re.DOTALL):
        name, list_content = match.groups()
        items = re.findall(r'"([^"]+)"', list_content)
        if items and "EXCLUDED" in name or "SIMPLE" in name:
            mappings[name] = items

    return mappings


def get_schema_tables() -> List[Dict[str, Any]]:
    """Extract database schema using TypeScript AST parser (extract-schema.ts)."""
    if not TS_EXTRACTOR.exists():
        raise FileNotFoundError(
            f"TypeScript schema extractor not found: {TS_EXTRACTOR}"
        )

    result = subprocess.run(
        ["npx", "ts-node", str(TS_EXTRACTOR)],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=60,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Schema extraction failed: {result.stderr}")

    tables = json.loads(result.stdout)

    # Add extraction metadata
    for table in tables:
        table["extraction_method"] = "ts-ast"

    return tables


def get_common_errors() -> Dict[str, Any]:
    """Define common errors and their solutions for AI guidance."""
    return {
        "KeyError": {
            "pattern": "KeyError: '(.+)'",
            "causes": [
                "Column doesn't exist in DataFrame",
                "Previous script in pipeline didn't run",
                "Column name has different casing or spacing",
            ],
            "solutions": [
                "Check column_mappings.py for correct column names",
                "Run full pipeline: python3 scripts/pipeline.py",
                "Use df.columns.tolist() to see actual column names",
            ],
        },
        "MergeError": {
            "pattern": "merge.*dtype",
            "causes": [
                "Join columns have different dtypes (int vs str)",
                "One side has NaN values causing type inference issues",
            ],
            "solutions": [
                "Ensure both join columns are same type: df['col'] = df['col'].astype(str)",
                "Check for nulls before merge: df['col'].isnull().sum()",
            ],
        },
        "FileNotFoundError": {
            "pattern": "No such file or directory.*data/",
            "causes": [
                "Previous pipeline stage didn't run",
                "Raw data files missing",
            ],
            "solutions": [
                "Run earlier stages first: python3 scripts/pipeline.py --stage1",
                "Check data/raw/ for source files",
            ],
        },
        "ValueError_date": {
            "pattern": "time data.*does not match format",
            "causes": [
                "Date column has inconsistent formats",
                "Non-date values in date column",
            ],
            "solutions": [
                "Use pd.to_datetime with errors='coerce'",
                "Check for non-date values: df[pd.to_datetime(df['col'], errors='coerce').isna()]",
            ],
        },
        "SchemaValidationError": {
            "pattern": "column.*not found|missing required column",
            "causes": [
                "Database schema changed but CSV mapping not updated",
                "Column dropped in earlier transformation",
            ],
            "solutions": [
                "Compare column_mappings.py with src/schema/*.ts",
                "Run npm run type-check after schema changes",
            ],
        },
    }


def get_data_files() -> Dict[str, List[str]]:
    """Get list of data files in each folder."""
    data_dir = PROJECT_ROOT / "data"
    files = {
        "raw": [],
        "intermediate": [],
        "import-ready": [],
    }

    for folder in files.keys():
        folder_path = data_dir / folder
        if folder_path.exists():
            files[folder] = [
                f.name
                for f in folder_path.iterdir()
                if f.is_file() and not f.name.startswith(".")
            ]

    return files


def generate_mermaid_diagram(pipeline_map: Dict) -> str:
    """Generate Mermaid flowchart from pipeline map."""
    lines = [
        "# Pipeline Map",
        "",
        f"Generated: {pipeline_map['generated_at']}",
        "",
        "## Data Flow Diagram",
        "",
        "```mermaid",
        "flowchart TD",
        '    subgraph RAW["Raw Data"]',
    ]

    # Add raw files
    for i, f in enumerate(pipeline_map["data_files"]["raw"]):
        safe_name = f.replace(" ", "_").replace(".", "_")
        lines.append(f'        raw_{i}["{f}"]')

    lines.append("    end")
    lines.append("")
    lines.append('    subgraph STAGE1["Stage 1: Clean"]')

    # Add stage 1 scripts
    for script in pipeline_map["scripts"]:
        if script["stage"] == "stage1_clean":
            lines.append(f'        {script["name"]}["{script["name"]}"]')

    lines.append("    end")
    lines.append("")
    lines.append('    subgraph INTERMEDIATE["Intermediate Data"]')

    for i, f in enumerate(pipeline_map["data_files"]["intermediate"]):
        safe_name = f.replace(".", "_")
        lines.append(f'        int_{i}["{f}"]')

    lines.append("    end")
    lines.append("")
    lines.append('    subgraph STAGE2["Stage 2: Transform"]')

    for script in pipeline_map["scripts"]:
        if script["stage"] == "stage2_transform":
            lines.append(f'        {script["name"]}["{script["name"]}"]')

    lines.append("    end")
    lines.append("")
    lines.append('    subgraph STAGE3["Stage 3: Prepare"]')

    for script in pipeline_map["scripts"]:
        if script["stage"] == "stage3_prepare":
            lines.append(f'        {script["name"]}["{script["name"]}"]')

    lines.append("    end")
    lines.append("")
    lines.append('    subgraph IMPORTREADY["Import-Ready Data"]')

    for i, f in enumerate(pipeline_map["data_files"]["import-ready"]):
        safe_name = f.replace(".", "_")
        lines.append(f'        ready_{i}["{f}"]')

    lines.append("    end")
    lines.append("")
    lines.append('    subgraph DB["Database Tables"]')

    for table in pipeline_map["schema_tables"]:
        lines.append(f'        db_{table["name"]}[("{table["name"]}")]')

    lines.append("    end")
    lines.append("")

    # Add connections based on dependencies
    lines.append("    %% Data Flow Connections")

    # Raw -> Stage 1
    lines.append("    RAW --> STAGE1")
    lines.append("    STAGE1 --> INTERMEDIATE")
    lines.append("    INTERMEDIATE --> STAGE2")
    lines.append("    STAGE2 --> INTERMEDIATE")
    lines.append("    INTERMEDIATE --> STAGE3")
    lines.append("    STAGE3 --> IMPORTREADY")
    lines.append("    IMPORTREADY --> DB")

    lines.append("```")
    lines.append("")

    # Add script details
    lines.append("## Script Details")
    lines.append("")
    lines.append("| # | Script | Stage | Purpose | Inputs | Outputs |")
    lines.append("|---|--------|-------|---------|--------|---------|")

    for i, script in enumerate(pipeline_map["scripts"], 1):
        purpose = (
            script.get("docstring", "").split("\n")[0]
            if script.get("docstring")
            else "-"
        )
        inputs = ", ".join([p.split("/")[-1] for p in script["inputs"]]) or "-"
        outputs = ", ".join([p.split("/")[-1] for p in script["outputs"]]) or "-"
        lines.append(
            f"| {i} | `{script['name']}` | {script['stage']} | {purpose[:50]} | {inputs} | {outputs} |"
        )

    lines.append("")

    # Add dependency graph
    lines.append("## Script Dependencies")
    lines.append("")
    lines.append("```mermaid")
    lines.append("flowchart LR")

    for script in pipeline_map["scripts"]:
        for dep in script["dependencies"]:
            lines.append(f"    {dep} --> {script['name']}")

    lines.append("```")
    lines.append("")

    # Add column mappings summary
    lines.append("## Column Mappings")
    lines.append("")
    if "PO_LINE_ITEMS_MAPPING" in pipeline_map.get("column_mappings", {}):
        lines.append("### PO Line Items (CSV → DB)")
        lines.append("")
        lines.append("| CSV Column | DB Column |")
        lines.append("|------------|-----------|")
        for csv_col, db_col in list(
            pipeline_map["column_mappings"]["PO_LINE_ITEMS_MAPPING"].items()
        )[:10]:
            lines.append(f"| {csv_col} | `{db_col}` |")
        lines.append("")
        lines.append(
            f"*...and {len(pipeline_map['column_mappings']['PO_LINE_ITEMS_MAPPING']) - 10} more*"
        )

    lines.append("")

    # Add schema summary
    lines.append("## Database Schema")
    lines.append("")
    for table in pipeline_map["schema_tables"]:
        lines.append(f"### `{table['name']}`")
        lines.append("")
        lines.append("| Column | Type | Constraints |")
        lines.append("|--------|------|-------------|")
        for col in table["columns"][:15]:
            constraints = []
            if col.get("primary_key"):
                constraints.append("PK")
            if col.get("not_null"):
                constraints.append("NOT NULL")
            if col.get("references"):
                constraints.append(f"FK → {col['references']}")
            if col.get("has_default"):
                constraints.append("DEFAULT")
            constraint_str = ", ".join(constraints) if constraints else "-"
            lines.append(f"| `{col['name']}` | {col['type']} | {constraint_str} |")
        if len(table["columns"]) > 15:
            lines.append(f"| *...* | *{len(table['columns']) - 15} more* | |")
        lines.append("")

    # Add data profiles section
    if pipeline_map.get("data_profiles"):
        lines.append("## Data Profiles")
        lines.append("")
        lines.append("Sample data and types for each CSV file:")
        lines.append("")

        for filename, profile in pipeline_map["data_profiles"].items():
            if "error" in profile:
                continue
            lines.append(f"### `{filename}`")
            lines.append("")
            lines.append(f"- **Path**: `{profile.get('path', 'N/A')}`")
            lines.append(f"- **Rows**: {profile.get('row_count', 'N/A')}")
            lines.append("")

            # Show dtypes
            if profile.get("dtypes"):
                lines.append("| Column | Type |")
                lines.append("|--------|------|")
                for col, dtype in list(profile["dtypes"].items())[:10]:
                    lines.append(f"| `{col}` | {dtype} |")
                if len(profile["dtypes"]) > 10:
                    lines.append(f"| *...* | *{len(profile['dtypes']) - 10} more* |")
                lines.append("")

            # Show null counts if any
            if profile.get("null_counts"):
                lines.append("**Columns with nulls:**")
                for col, count in profile["null_counts"].items():
                    lines.append(f"- `{col}`: {count} nulls")
                lines.append("")

    # Add common errors section
    if pipeline_map.get("common_errors"):
        lines.append("## Common Errors & Solutions")
        lines.append("")
        for error_type, info in pipeline_map["common_errors"].items():
            lines.append(f"### {error_type}")
            lines.append("")
            lines.append("**Causes:**")
            for cause in info["causes"]:
                lines.append(f"- {cause}")
            lines.append("")
            lines.append("**Solutions:**")
            for solution in info["solutions"]:
                lines.append(f"- {solution}")
            lines.append("")

    # Add pandas operations summary
    lines.append("## Transformation Operations")
    lines.append("")
    lines.append("Key pandas operations used in each script:")
    lines.append("")
    for script in pipeline_map["scripts"]:
        if script.get("pandas_operations"):
            lines.append(f"### `{script['name']}`")
            lines.append("")
            lines.append("| Line | Operation | Details |")
            lines.append("|------|-----------|---------|")
            for op in script["pandas_operations"][:10]:
                details = ""
                if op.get("column"):
                    details = f"column: `{op['column']}`"
                elif op.get("on_column"):
                    details = f"on: `{op['on_column']}`"
                elif op.get("group_column"):
                    details = f"by: `{op['group_column']}`"
                elif op.get("group_columns"):
                    details = f"by: `{', '.join(op['group_columns'])}`"
                elif op.get("dropped_columns"):
                    details = f"cols: `{', '.join(op['dropped_columns'])}`"
                lines.append(
                    f"| {op['line']} | {op['operation']} | {details or op.get('description', '-')} |"
                )
            lines.append("")

    return "\n".join(lines)


def get_latest_source_mtime() -> datetime:
    """Get the latest modification time of all source files.

    This makes the generated timestamp deterministic - it only changes
    when source files actually change, preventing infinite loops in
    pre-commit hooks.
    """
    latest_mtime = 0.0

    # Check all pipeline scripts
    stage_dirs = ["stage1_clean", "stage2_transform", "stage3_prepare", "config"]
    for stage_dir in stage_dirs:
        stage_path = SCRIPTS_DIR / stage_dir
        if stage_path.exists():
            for script_file in stage_path.glob("*.py"):
                mtime = script_file.stat().st_mtime
                if mtime > latest_mtime:
                    latest_mtime = mtime

    # Check pipeline.py itself
    pipeline_script = SCRIPTS_DIR / "pipeline.py"
    if pipeline_script.exists():
        mtime = pipeline_script.stat().st_mtime
        if mtime > latest_mtime:
            latest_mtime = mtime

    # Check the schema extractor
    if TS_EXTRACTOR.exists():
        mtime = TS_EXTRACTOR.stat().st_mtime
        if mtime > latest_mtime:
            latest_mtime = mtime

    # Check schema files
    schema_dir = PROJECT_ROOT / "src" / "schema"
    if schema_dir.exists():
        for schema_file in schema_dir.glob("*.ts"):
            mtime = schema_file.stat().st_mtime
            if mtime > latest_mtime:
                latest_mtime = mtime

    return datetime.fromtimestamp(latest_mtime, tz=timezone.utc)


def generate_pipeline_map():
    """Generate the complete pipeline map."""
    print("=" * 60)
    print("Generating Pipeline Map")
    print("=" * 60)

    # Collect all scripts
    scripts = []
    stage_dirs = ["stage1_clean", "stage2_transform", "stage3_prepare"]

    for stage_dir in stage_dirs:
        stage_path = SCRIPTS_DIR / stage_dir
        if stage_path.exists():
            for script_file in sorted(stage_path.glob("*.py")):
                print(f"  Analyzing: {script_file.name}")
                metadata = extract_script_metadata(script_file)
                scripts.append(metadata)

    # Also analyze pipeline.py
    pipeline_script = SCRIPTS_DIR / "pipeline.py"
    if pipeline_script.exists():
        print("  Analyzing: pipeline.py")
        scripts.append(extract_script_metadata(pipeline_script))

    # Analyze dependencies
    print("\nAnalyzing dependencies...")
    scripts = analyze_dependencies(scripts)

    # Get column mappings
    print("Extracting column mappings...")
    column_mappings = get_column_mappings()

    # Get schema tables
    print("Extracting schema tables...")
    schema_tables = get_schema_tables()

    # Get data files
    print("Listing data files...")
    data_files = get_data_files()

    # Get data profiles (sample data, dtypes)
    print("Profiling data files...")
    data_profiles = get_data_profiles()

    # Get common error patterns
    print("Adding error guidance...")
    common_errors = get_common_errors()

    # Build the map
    # Use deterministic timestamp based on source file mtimes
    source_mtime = get_latest_source_mtime()
    pipeline_map = {
        "generated_at": source_mtime.isoformat(),
        "project": "cost-management-db",
        "description": "Data pipeline for transforming raw PO/GR/IR data into import-ready CSVs",
        "pipeline_stages": [
            {
                "name": "stage1_clean",
                "description": "Clean and filter raw data",
                "input_folder": "data/raw",
                "output_folder": "data/intermediate",
            },
            {
                "name": "stage2_transform",
                "description": "Enrich data and calculate derived values",
                "input_folder": "data/intermediate",
                "output_folder": "data/intermediate",
            },
            {
                "name": "stage3_prepare",
                "description": "Map columns to database schema",
                "input_folder": "data/intermediate",
                "output_folder": "data/import-ready",
            },
        ],
        "execution_order": [
            "01_po_line_items",
            "02_gr_postings",
            "03_ir_postings",
            "04_enrich_po_line_items",
            "05_calculate_cost_impact",
            "06_prepare_po_line_items",
            "07_prepare_po_transactions",
        ],
        "scripts": scripts,
        "column_mappings": column_mappings,
        "schema_tables": schema_tables,
        "data_files": data_files,
        "data_profiles": data_profiles,
        "common_errors": common_errors,
        "key_files": {
            "orchestrator": "scripts/pipeline.py",
            "column_config": "scripts/config/column_mappings.py",
            "schema_dir": "src/schema/",
        },
        "ai_agent_notes": {
            "to_add_new_column": [
                "1. Add column to src/schema/<table>.ts",
                "2. Run npm run db:drift, then apply the SQL manually",
                "3. Add CSV→DB mapping in scripts/config/column_mappings.py",
                "4. Update relevant stage script to include the column",
                "5. Run python3 scripts/pipeline.py to regenerate data",
            ],
            "to_add_new_transformation": [
                "1. Identify which stage the transformation belongs to",
                "2. Add function to appropriate stage script",
                "3. Update the main() function to call new transformation",
                "4. Test with python3 scripts/pipeline.py",
            ],
            "to_add_new_data_source": [
                "1. Place raw file in data/raw/",
                "2. Create new stage1 script (numbered appropriately)",
                "3. Add to STAGE1_SCRIPTS in pipeline.py",
                "4. Create column mappings if needed for import",
            ],
        },
    }

    # Save JSON
    print(f"\nSaving JSON to: {OUTPUT_JSON}")
    sorted_map = sort_nested_lists(pipeline_map)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(sorted_map, f, indent=2, sort_keys=True)

    # Generate and save Mermaid
    print(f"Saving Mermaid diagram to: {OUTPUT_MD}")
    mermaid_content = generate_mermaid_diagram(pipeline_map)
    with open(OUTPUT_MD, "w") as f:
        f.write(mermaid_content)

    print("\n" + "=" * 60)
    print("Pipeline Map Generated Successfully!")
    print("=" * 60)
    print("\nFiles created:")
    print(f"  - {OUTPUT_JSON} (machine-readable)")
    print(f"  - {OUTPUT_MD} (visual diagram)")
    print(f"\nScripts analyzed: {len(scripts)}")
    print(f"Schema tables found: {len(schema_tables)}")
    print(f"Column mappings found: {len(column_mappings)}")

    return pipeline_map


if __name__ == "__main__":
    generate_pipeline_map()
