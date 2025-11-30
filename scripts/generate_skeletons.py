#!/usr/bin/env python3
"""
Code Skeleton Generator

Generates compressed code representations (skeletons) that retain 100% of
interface information while reducing token usage by 5-10x.

Preserves:
  - Function/class signatures
  - Docstrings
  - Type hints
  - Module-level docstrings
  - Constants and imports
  - Column annotations (columns read/written by each script)

Removes:
  - Function bodies (replaced with `...`)
  - Implementation details

Output: pipeline-context/skeletons/

Usage:
    python3 scripts/generate_skeletons.py
"""

import ast
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set

# Paths
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent
PIPELINE_CONTEXT_DIR = PROJECT_ROOT / "pipeline-context"
SKELETONS_DIR = PIPELINE_CONTEXT_DIR / "skeletons"
LINEAGE_FILE = PIPELINE_CONTEXT_DIR / "lineage" / "graph.json"


def load_column_access() -> Dict[str, Dict[str, List[str]]]:
    """
    Load column access patterns from lineage graph.
    Returns: {script_name: {"reads": [cols], "writes": [cols]}}
    """
    if not LINEAGE_FILE.exists():
        return {}
    
    try:
        with open(LINEAGE_FILE) as f:
            graph = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}
    
    column_access = graph.get("column_access", {})
    
    # Reorganize by script
    script_columns: Dict[str, Dict[str, Set[str]]] = {}
    
    for column, accesses in column_access.items():
        for access in accesses:
            script = access.get("script", "")
            access_type = access.get("type", "")
            
            if not script:
                continue
            
            if script not in script_columns:
                script_columns[script] = {"reads": set(), "writes": set()}
            
            if access_type == "READS":
                script_columns[script]["reads"].add(column)
            elif access_type == "WRITES":
                script_columns[script]["writes"].add(column)
    
    # Convert sets to sorted lists
    return {
        script: {
            "reads": sorted(cols["reads"]),
            "writes": sorted(cols["writes"])
        }
        for script, cols in script_columns.items()
    }


class SkeletonTransformer(ast.NodeTransformer):
    """Transform AST to skeleton form by removing function bodies."""
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Keep signature and docstring, replace body with `...`"""
        new_body = []
        
        # Keep docstring if present
        if (node.body and 
            isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            new_body.append(node.body[0])
        
        # Add ellipsis as body
        new_body.append(ast.Expr(value=ast.Constant(value=...)))
        
        node.body = new_body
        return node
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        """Same treatment for async functions."""
        new_body = []
        
        if (node.body and 
            isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            new_body.append(node.body[0])
        
        new_body.append(ast.Expr(value=ast.Constant(value=...)))
        
        node.body = new_body
        return node
    
    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        """Keep class structure, skeletonize methods."""
        self.generic_visit(node)
        return node


def generate_skeleton(source_code: str, script_name: str = "", column_info: Optional[Dict] = None) -> str:
    """
    Generate skeleton from source code.
    
    If column_info is provided, adds column annotations to the module docstring.
    """
    tree = ast.parse(source_code)
    
    # Add column annotations to module docstring if available
    if column_info:
        reads = column_info.get("reads", [])
        writes = column_info.get("writes", [])
        
        if reads or writes:
            annotation = _build_column_annotation(reads, writes)
            tree = _add_column_annotation_to_docstring(tree, annotation)
    
    transformer = SkeletonTransformer()
    skeleton_tree = transformer.visit(tree)
    
    # Fix missing lineno/col_offset for new nodes
    ast.fix_missing_locations(skeleton_tree)
    
    return ast.unparse(skeleton_tree)


def _build_column_annotation(reads: List[str], writes: List[str]) -> str:
    """Build column annotation text."""
    lines = ["\n\nColumn Operations:"]
    
    if writes:
        lines.append(f"  WRITES: {', '.join(writes[:10])}")
        if len(writes) > 10:
            lines.append(f"          ...and {len(writes) - 10} more")
    
    if reads:
        lines.append(f"  READS:  {', '.join(reads[:10])}")
        if len(reads) > 10:
            lines.append(f"          ...and {len(reads) - 10} more")
    
    return "\n".join(lines)


def _add_column_annotation_to_docstring(tree: ast.Module, annotation: str) -> ast.Module:
    """Add column annotation to module docstring."""
    if not tree.body:
        return tree
    
    # Check if first node is a docstring
    first = tree.body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
        # Append annotation to existing docstring
        first.value.value = first.value.value.rstrip() + annotation
    else:
        # No docstring - create one with just the annotation
        docstring = ast.Expr(value=ast.Constant(value=f'"""{annotation.strip()}"""'))
        tree.body.insert(0, docstring)
    
    return tree


def count_tokens_approx(text: str) -> int:
    """Approximate token count (rough estimate: ~4 chars per token)."""
    return len(text) // 4


def generate_skeleton_file(source_path: Path, output_path: Path, column_info: Optional[Dict] = None) -> Dict[str, Any]:
    """Generate skeleton for a single file with column annotations."""
    content = source_path.read_text()
    script_name = source_path.stem
    
    try:
        skeleton_code = generate_skeleton(content, script_name, column_info)
        
        # Calculate stats
        original_tokens = count_tokens_approx(content)
        skeleton_tokens = count_tokens_approx(skeleton_code)
        compression_ratio = original_tokens / skeleton_tokens if skeleton_tokens > 0 else 0
        
        # Write skeleton file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(skeleton_code)
        
        return {
            "success": True,
            "original_lines": len(content.splitlines()),
            "skeleton_lines": len(skeleton_code.splitlines()),
            "original_tokens": original_tokens,
            "skeleton_tokens": skeleton_tokens,
            "compression_ratio": round(compression_ratio, 2)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def generate_all_skeletons() -> Dict[str, Any]:
    """Generate skeletons for all pipeline scripts with column annotations."""
    print("=" * 60)
    print("Generating Code Skeletons")
    print("=" * 60)
    
    # Ensure output directory exists
    SKELETONS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load column access data for annotations
    script_columns = load_column_access()
    if script_columns:
        print(f"  Loaded column access data for {len(script_columns)} scripts")
    
    # Collect scripts to process
    stage_dirs = ["stage1_clean", "stage2_transform", "stage3_prepare"]
    results = {
        "scripts": [],
        "totals": {
            "original_lines": 0,
            "skeleton_lines": 0,
            "original_tokens": 0,
            "skeleton_tokens": 0,
        }
    }
    
    for stage_dir in stage_dirs:
        source_dir = SCRIPTS_DIR / stage_dir
        output_dir = SKELETONS_DIR / stage_dir
        
        if not source_dir.exists():
            continue
        
        print(f"\n[{stage_dir}]")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for script_path in sorted(source_dir.glob("*.py")):
            skeleton_name = f"{script_path.stem}.skeleton.py"
            output_path = output_dir / skeleton_name
            script_name = script_path.stem
            
            print(f"  Processing: {script_path.name}")
            
            # Get column info for this script
            column_info = script_columns.get(script_name)
            stats = generate_skeleton_file(script_path, output_path, column_info)
            
            if stats["success"]:
                script_info = {
                    "name": script_path.stem,
                    "source_path": str(script_path.relative_to(PROJECT_ROOT)),
                    "skeleton_path": str(output_path.relative_to(PROJECT_ROOT)),
                    "original_lines": stats["original_lines"],
                    "skeleton_lines": stats["skeleton_lines"],
                    "original_tokens": stats["original_tokens"],
                    "skeleton_tokens": stats["skeleton_tokens"],
                    "compression_ratio": stats["compression_ratio"]
                }
                results["scripts"].append(script_info)
                
                # Update totals
                results["totals"]["original_lines"] += stats["original_lines"]
                results["totals"]["skeleton_lines"] += stats["skeleton_lines"]
                results["totals"]["original_tokens"] += stats["original_tokens"]
                results["totals"]["skeleton_tokens"] += stats["skeleton_tokens"]
                
                print(f"    {stats['original_lines']} -> {stats['skeleton_lines']} lines ({stats['compression_ratio']}x)")
            else:
                print(f"    Error: {stats['error']}")
    
    # Also generate skeleton for config files
    config_dir = SCRIPTS_DIR / "config"
    if config_dir.exists():
        print(f"\n[config]")
        config_output_dir = SKELETONS_DIR / "config"
        config_output_dir.mkdir(parents=True, exist_ok=True)
        
        for script_path in config_dir.glob("*.py"):
            skeleton_name = f"{script_path.stem}.skeleton.py"
            output_path = config_output_dir / skeleton_name
            
            print(f"  Processing: {script_path.name}")
            
            # For config files, we keep everything (no function bodies to remove)
            # Just copy with minimal processing
            content = script_path.read_text()
            output_path.write_text(content)
            
            print(f"    Copied (config file)")
    
    # Calculate overall compression ratio
    if results["totals"]["skeleton_tokens"] > 0:
        results["totals"]["compression_ratio"] = round(
            results["totals"]["original_tokens"] / results["totals"]["skeleton_tokens"], 2
        )
    else:
        results["totals"]["compression_ratio"] = 0
    
    # Save index
    index_path = SKELETONS_DIR / "index.json"
    with open(index_path, "w") as f:
        json.dump(results, f, indent=2, sort_keys=True)
    
    print("\n" + "=" * 60)
    print("Skeleton Generation Complete!")
    print("=" * 60)
    print(f"\nOutput directory: {SKELETONS_DIR}")
    print(f"\nTotals:")
    print(f"  Original: {results['totals']['original_lines']} lines, ~{results['totals']['original_tokens']} tokens")
    print(f"  Skeleton: {results['totals']['skeleton_lines']} lines, ~{results['totals']['skeleton_tokens']} tokens")
    print(f"  Compression: {results['totals']['compression_ratio']}x")
    
    return results


if __name__ == "__main__":
    generate_all_skeletons()
