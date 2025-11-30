#!/usr/bin/env python3
"""
Pattern Library Builder

Extracts and defines code patterns from the existing codebase.
Patterns help AI agents follow established conventions when writing new code.

Patterns include:
  - pipeline_script: Structure for data transformation scripts
  - drizzle_schema: TypeScript schema file structure
  - data_filtering: Function pattern for filtering DataFrame rows
  - column_mapping: Pattern for CSV to DB column mappings

Output: pipeline-context/patterns/index.json

Usage:
    python3 scripts/extract_patterns.py
"""

import ast
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Paths
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent
PIPELINE_CONTEXT_DIR = PROJECT_ROOT / "pipeline-context"
PATTERNS_DIR = PIPELINE_CONTEXT_DIR / "patterns"
OUTPUT_FILE = PATTERNS_DIR / "index.json"


def extract_function_example(file_path: Path, function_name: str) -> Optional[str]:
    """Extract a specific function's source code from a file."""
    content = file_path.read_text()
    lines = content.splitlines()
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return None
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            start_line = node.lineno - 1  # 0-indexed
            end_line = node.end_lineno if node.end_lineno else start_line + 1
            return "\n".join(lines[start_line:end_line])
    
    return None


def analyze_pipeline_script_structure(file_path: Path) -> Dict[str, Any]:
    """Analyze a pipeline script to extract its structure."""
    content = file_path.read_text()
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return {}
    
    structure = {
        "has_docstring": False,
        "imports": [],
        "constants": [],
        "functions": [],
        "has_main_guard": False,
    }
    
    # Check module docstring
    if ast.get_docstring(tree):
        structure["has_docstring"] = True
    
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    structure["imports"].append(alias.name)
            else:
                if node.module:
                    structure["imports"].append(node.module)
        
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    structure["constants"].append(target.id)
        
        elif isinstance(node, ast.FunctionDef):
            structure["functions"].append(node.name)
        
        elif isinstance(node, ast.If):
            # Check for if __name__ == '__main__'
            try:
                if (isinstance(node.test, ast.Compare) and
                    isinstance(node.test.left, ast.Name) and
                    node.test.left.id == '__name__'):
                    structure["has_main_guard"] = True
            except Exception:
                pass
    
    return structure


def extract_drizzle_schema_pattern() -> Dict[str, Any]:
    """Extract pattern from TypeScript Drizzle schema files."""
    schema_dir = PROJECT_ROOT / "src" / "schema"
    
    if not schema_dir.exists():
        return {}
    
    # Read a sample schema file
    sample_file = schema_dir / "po-line-items.ts"
    if sample_file.exists():
        content = sample_file.read_text()
    else:
        # Find any .ts file
        ts_files = list(schema_dir.glob("*.ts"))
        if ts_files:
            content = ts_files[0].read_text()
        else:
            return {}
    
    return {
        "name": "drizzle_schema",
        "description": "Pattern for Drizzle ORM table definitions",
        "file_type": "typescript",
        "structure": [
            "Import types from 'drizzle-orm/pg-core'",
            "Import devV3Schema from './_schema'",
            "Import related tables if needed",
            "",
            "Export const tableName = devV3Schema.table('snake_case_name', {",
            "  // Primary key",
            "  id: uuid('id').primaryKey().defaultRandom(),",
            "  ",
            "  // Business fields with snake_case DB names",
            "  fieldName: type('db_column_name').constraints(),",
            "  ",
            "  // Timestamps",
            "  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),",
            "  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),",
            "}, (table) => [",
            "  // Indexes",
            "]);",
            "",
            "// Type exports",
            "export type TableName = typeof tableName.$inferSelect;",
            "export type NewTableName = typeof tableName.$inferInsert;",
        ],
        "conventions": [
            "Always import devV3Schema from './_schema' - never create new pgSchema instances",
            "Use snake_case for database column names",
            "Use camelCase for TypeScript property names",
            "Include id as uuid().primaryKey().defaultRandom()",
            "Include createdAt and updatedAt timestamps",
            "Export both Select and Insert types",
            "Add indexes for frequently queried columns",
        ],
        "examples": [
            "src/schema/po-line-items.ts",
            "src/schema/po-transactions.ts",
            "src/schema/projects.ts",
        ],
        "template_reference": "pipeline-context/skeletons/config/column_mappings.skeleton.py"
    }


def build_pattern_library() -> Dict[str, Any]:
    """Build the complete pattern library."""
    print("=" * 60)
    print("Building Pattern Library")
    print("=" * 60)
    
    patterns = {
        "version": "1.0.0",
        "description": "Pattern library for Context Oracle - follow conventions",
        "patterns": {}
    }
    
    # Pattern 1: Pipeline Script
    print("\n[1/4] Extracting pipeline_script pattern...")
    
    # Analyze all pipeline scripts to find common structure
    stage_dirs = ["stage1_clean", "stage2_transform", "stage3_prepare"]
    script_structures = []
    
    for stage_dir in stage_dirs:
        stage_path = SCRIPTS_DIR / stage_dir
        if stage_path.exists():
            for script_path in stage_path.glob("*.py"):
                structure = analyze_pipeline_script_structure(script_path)
                if structure:
                    script_structures.append({
                        "file": str(script_path.relative_to(PROJECT_ROOT)),
                        "structure": structure
                    })
    
    # Find common functions across scripts
    common_functions = ["load_data", "save_data", "main"]
    for struct in script_structures:
        for func in struct["structure"].get("functions", []):
            if func not in common_functions and "filter" in func.lower():
                common_functions.append(func)
                break
    
    # Get example from 01_po_line_items.py
    example_script = SCRIPTS_DIR / "stage1_clean" / "01_po_line_items.py"
    if example_script.exists():
        docstring_example = ast.get_docstring(ast.parse(example_script.read_text())) or ""
    else:
        docstring_example = ""
    
    patterns["patterns"]["pipeline_script"] = {
        "name": "pipeline_script",
        "description": "Pattern for data pipeline transformation scripts",
        "file_type": "python",
        "structure": [
            "Module docstring with Dependencies/Input/Output",
            "sys.path setup for imports",
            "Import statements (sys, pathlib, pandas)",
            "Project-relative imports (from config.column_mappings)",
            "PROJECT_ROOT and file path constants",
            "load_data() function - loads input file",
            "transformation functions (filter_*, calculate_*, map_*)",
            "save_data() function - saves output file",
            "main() orchestrator function",
            "if __name__ == '__main__' guard with sys.exit",
        ],
        "conventions": [
            "Use PROJECT_ROOT for all file paths",
            "Print progress messages with row counts",
            "Return DataFrame from transformation functions",
            "Use .copy() when filtering to avoid SettingWithCopyWarning",
            "Document dependencies in module docstring",
            "Name files with numeric prefix for execution order",
        ],
        "docstring_template": '''"""
Stage {N}: {Title}

{Description}

Dependencies: {list of scripts that must run first}
Input: {input file paths}
Output: {output file paths}
"""''',
        "function_templates": {
            "load_data": '''def load_data(filepath: Path) -> pd.DataFrame:
    """Load the raw CSV file."""
    df = pd.read_csv(filepath, low_memory=False)
    print(f"  Loaded {len(df):,} rows from {filepath.name}")
    return df''',
            "save_data": '''def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save the cleaned DataFrame to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"  Saved {len(df):,} rows to {filepath.name}")''',
            "filter_template": '''def filter_{what}(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with {condition}."""
    initial_count = len(df)
    mask = {mask_expression}
    df_filtered = df[mask].copy()
    removed_count = initial_count - len(df_filtered)
    print(f"  Removed {removed_count:,} rows with {reason}")
    return df_filtered''',
            "main": '''def main():
    print("=" * 60)
    print("Stage {N}: {Title}")
    print("=" * 60)
    
    # Load
    print("\\nLoading data...")
    df = load_data(INPUT_FILE)
    
    # Transform
    print("\\nApplying transformations...")
    df = transform_1(df)
    df = transform_2(df)
    
    # Save
    print("\\nSaving output...")
    save_data(df, OUTPUT_FILE)
    
    print("\\nDone!")
    return True''',
        },
        "examples": [
            "scripts/stage1_clean/01_po_line_items.py",
            "scripts/stage1_clean/02_gr_postings.py",
            "scripts/stage2_transform/05_calculate_cost_impact.py",
        ],
        "skeleton_reference": "pipeline-context/skeletons/stage1_clean/01_po_line_items.skeleton.py"
    }
    
    # Pattern 2: Drizzle Schema
    print("[2/4] Extracting drizzle_schema pattern...")
    patterns["patterns"]["drizzle_schema"] = extract_drizzle_schema_pattern()
    
    # Pattern 3: Data Filtering Function
    print("[3/4] Extracting data_filtering pattern...")
    
    filter_example = extract_function_example(
        SCRIPTS_DIR / "stage1_clean" / "01_po_line_items.py",
        "filter_valuation_classes"
    )
    
    patterns["patterns"]["data_filtering"] = {
        "name": "data_filtering",
        "description": "Pattern for filtering DataFrame rows based on conditions",
        "file_type": "python",
        "signature": "def filter_{what}(df: pd.DataFrame) -> pd.DataFrame:",
        "structure": [
            "Docstring describing what is filtered",
            "Get initial_count = len(df)",
            "Create boolean mask",
            "Apply filter: df_filtered = df[mask].copy()",
            "Calculate removed_count",
            "Print progress message",
            "Return filtered DataFrame",
        ],
        "conventions": [
            "Always use .copy() to avoid SettingWithCopyWarning",
            "Always print the count of removed rows",
            "Use descriptive function names: filter_zero_quantity, filter_valuation_classes",
            "Return the filtered DataFrame (don't modify in place)",
        ],
        "template": '''def filter_{what}(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with {condition}."""
    initial_count = len(df)
    mask = {mask_expression}
    df_filtered = df[mask].copy()
    removed_count = initial_count - len(df_filtered)
    print(f"  Removed {removed_count:,} rows with {reason}")
    return df_filtered''',
        "example_code": filter_example,
        "examples": [
            "scripts/stage1_clean/01_po_line_items.py:filter_valuation_classes",
            "scripts/stage1_clean/01_po_line_items.py:filter_nis_levels",
            "scripts/stage1_clean/02_gr_postings.py:filter_zero_quantity",
        ]
    }
    
    # Pattern 4: Column Mapping
    print("[4/4] Extracting column_mapping pattern...")
    
    patterns["patterns"]["column_mapping"] = {
        "name": "column_mapping",
        "description": "Pattern for CSV to database column mappings",
        "file_type": "python",
        "file_location": "scripts/config/column_mappings.py",
        "structure": [
            "Module docstring explaining the mapping purpose",
            "Dictionary with CSV column as key, DB column as value",
            "Group related columns with comments",
            "Use # comments for columns not yet implemented",
            "Separate dictionaries for each table",
        ],
        "conventions": [
            "CSV column names: Original from source (mixed case, spaces)",
            "DB column names: snake_case matching Drizzle schema",
            "Group by category (header fields, vendor info, etc.)",
            "Keep commented-out columns for future reference",
        ],
        "template": '''# {TABLE_NAME}: Source CSV → Database columns
{TABLE_NAME}_MAPPING = {
    # Business key
    "CSV Column Name": "db_column_name",
    
    # Category 1
    "Another CSV Column": "another_db_column",
    
    # Category 2 (not yet implemented)
    # "Future Column": "future_column",
}''',
        "examples": [
            "scripts/config/column_mappings.py:PO_LINE_ITEMS_MAPPING",
            "scripts/config/column_mappings.py:PO_TRANSACTIONS_MAPPING",
        ]
    }
    
    # Save the pattern library
    PATTERNS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(patterns, f, indent=2)
    
    print("\n" + "=" * 60)
    print("Pattern Library Generated!")
    print("=" * 60)
    print(f"\nOutput: {OUTPUT_FILE}")
    print(f"\nPatterns defined: {len(patterns['patterns'])}")
    for name in patterns["patterns"]:
        print(f"  - {name}")
    
    return patterns


if __name__ == "__main__":
    build_pattern_library()
