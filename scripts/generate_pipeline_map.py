#!/usr/bin/env python3
"""
Pipeline Map Generator

Generates a comprehensive map of the data pipeline for AI agent context.
Outputs:
  - pipeline-map.json: Machine-readable pipeline structure
  - pipeline-map.md: Mermaid diagram for visualization

Usage:
    python3 scripts/generate_pipeline_map.py
"""

import ast
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Paths
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent
OUTPUT_JSON = PROJECT_ROOT / "pipeline-map.json"
OUTPUT_MD = PROJECT_ROOT / "pipeline-map.md"


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
        "line_count": len(content.splitlines()),
    }
    
    try:
        tree = ast.parse(content)
        
        # Extract module docstring
        if (ast.get_docstring(tree)):
            metadata["docstring"] = ast.get_docstring(tree)
        
        # Walk the AST
        for node in ast.walk(tree):
            # Extract imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    metadata["imports"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    metadata["imports"].append(node.module)
            
            # Extract function definitions
            elif isinstance(node, ast.FunctionDef):
                func_info = {
                    "name": node.name,
                    "docstring": ast.get_docstring(node),
                    "args": [arg.arg for arg in node.args.args],
                    "line": node.lineno,
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
    for match in re.finditer(r'(\w+_FILE)\s*=\s*PROJECT_ROOT\s*/\s*"data"\s*/\s*"(\w+)"\s*/\s*"([^"]+)"', content):
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
    dict_pattern = r'(\w+_MAPPING)\s*=\s*\{([^}]+)\}'
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
    list_pattern = r'(\w+)\s*=\s*\[([^\]]+)\]'
    for match in re.finditer(list_pattern, content, re.DOTALL):
        name, list_content = match.groups()
        items = re.findall(r'"([^"]+)"', list_content)
        if items and "EXCLUDED" in name or "SIMPLE" in name:
            mappings[name] = items
    
    return mappings


def get_schema_tables() -> List[Dict[str, Any]]:
    """Extract database schema information."""
    schema_dir = PROJECT_ROOT / "src" / "schema"
    if not schema_dir.exists():
        return []
    
    tables = []
    for schema_file in schema_dir.glob("*.ts"):
        if schema_file.name in ["_schema.ts", "index.ts"]:
            continue
        
        content = schema_file.read_text()
        
        # Extract table name
        table_match = re.search(r"\.table\('(\w+)'", content)
        if not table_match:
            continue
        
        table_name = table_match.group(1)
        
        # Extract columns
        columns = []
        col_pattern = r"(\w+):\s*(uuid|varchar|text|numeric|integer|date|timestamp|boolean)\("
        for match in re.finditer(col_pattern, content):
            col_name, col_type = match.groups()
            columns.append({"name": col_name, "type": col_type})
        
        tables.append({
            "name": table_name,
            "file": schema_file.name,
            "columns": columns,
        })
    
    return tables


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
                f.name for f in folder_path.iterdir() 
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
        "    subgraph RAW[\"Raw Data\"]",
    ]
    
    # Add raw files
    for i, f in enumerate(pipeline_map["data_files"]["raw"]):
        safe_name = f.replace(" ", "_").replace(".", "_")
        lines.append(f"        raw_{i}[\"{f}\"]")
    
    lines.append("    end")
    lines.append("")
    lines.append("    subgraph STAGE1[\"Stage 1: Clean\"]")
    
    # Add stage 1 scripts
    for script in pipeline_map["scripts"]:
        if script["stage"] == "stage1_clean":
            lines.append(f"        {script['name']}[\"{script['name']}\"]")
    
    lines.append("    end")
    lines.append("")
    lines.append("    subgraph INTERMEDIATE[\"Intermediate Data\"]")
    
    for i, f in enumerate(pipeline_map["data_files"]["intermediate"]):
        safe_name = f.replace(".", "_")
        lines.append(f"        int_{i}[\"{f}\"]")
    
    lines.append("    end")
    lines.append("")
    lines.append("    subgraph STAGE2[\"Stage 2: Transform\"]")
    
    for script in pipeline_map["scripts"]:
        if script["stage"] == "stage2_transform":
            lines.append(f"        {script['name']}[\"{script['name']}\"]")
    
    lines.append("    end")
    lines.append("")
    lines.append("    subgraph STAGE3[\"Stage 3: Prepare\"]")
    
    for script in pipeline_map["scripts"]:
        if script["stage"] == "stage3_prepare":
            lines.append(f"        {script['name']}[\"{script['name']}\"]")
    
    lines.append("    end")
    lines.append("")
    lines.append("    subgraph IMPORTREADY[\"Import-Ready Data\"]")
    
    for i, f in enumerate(pipeline_map["data_files"]["import-ready"]):
        safe_name = f.replace(".", "_")
        lines.append(f"        ready_{i}[\"{f}\"]")
    
    lines.append("    end")
    lines.append("")
    lines.append("    subgraph DB[\"Database Tables\"]")
    
    for table in pipeline_map["schema_tables"]:
        lines.append(f"        db_{table['name']}[(\"{table['name']}\")]")
    
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
        purpose = script.get("docstring", "").split("\n")[0] if script.get("docstring") else "-"
        inputs = ", ".join([p.split("/")[-1] for p in script["inputs"]]) or "-"
        outputs = ", ".join([p.split("/")[-1] for p in script["outputs"]]) or "-"
        lines.append(f"| {i} | `{script['name']}` | {script['stage']} | {purpose[:50]} | {inputs} | {outputs} |")
    
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
        for csv_col, db_col in list(pipeline_map["column_mappings"]["PO_LINE_ITEMS_MAPPING"].items())[:10]:
            lines.append(f"| {csv_col} | `{db_col}` |")
        lines.append("")
        lines.append(f"*...and {len(pipeline_map['column_mappings']['PO_LINE_ITEMS_MAPPING']) - 10} more*")
    
    lines.append("")
    
    # Add schema summary
    lines.append("## Database Schema")
    lines.append("")
    for table in pipeline_map["schema_tables"]:
        lines.append(f"### `{table['name']}`")
        lines.append("")
        lines.append("| Column | Type |")
        lines.append("|--------|------|")
        for col in table["columns"][:15]:
            lines.append(f"| `{col['name']}` | {col['type']} |")
        if len(table["columns"]) > 15:
            lines.append(f"| *...* | *{len(table['columns']) - 15} more* |")
        lines.append("")
    
    return "\n".join(lines)


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
        print(f"  Analyzing: pipeline.py")
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
    
    # Build the map
    pipeline_map = {
        "generated_at": datetime.now().isoformat(),
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
        
        "key_files": {
            "orchestrator": "scripts/pipeline.py",
            "column_config": "scripts/config/column_mappings.py",
            "schema_dir": "src/schema/",
        },
        
        "ai_agent_notes": {
            "to_add_new_column": [
                "1. Add column to src/schema/<table>.ts",
                "2. Run npm run db:push",
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
    with open(OUTPUT_JSON, "w") as f:
        json.dump(pipeline_map, f, indent=2)
    
    # Generate and save Mermaid
    print(f"Saving Mermaid diagram to: {OUTPUT_MD}")
    mermaid_content = generate_mermaid_diagram(pipeline_map)
    with open(OUTPUT_MD, "w") as f:
        f.write(mermaid_content)
    
    print("\n" + "=" * 60)
    print("Pipeline Map Generated Successfully!")
    print("=" * 60)
    print(f"\nFiles created:")
    print(f"  - {OUTPUT_JSON} (machine-readable)")
    print(f"  - {OUTPUT_MD} (visual diagram)")
    print(f"\nScripts analyzed: {len(scripts)}")
    print(f"Schema tables found: {len(schema_tables)}")
    print(f"Column mappings found: {len(column_mappings)}")
    
    return pipeline_map


if __name__ == "__main__":
    generate_pipeline_map()
