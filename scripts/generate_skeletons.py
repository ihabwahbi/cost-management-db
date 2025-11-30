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
from typing import Dict, List, Any, Optional

# Paths
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent
PIPELINE_CONTEXT_DIR = PROJECT_ROOT / "pipeline-context"
SKELETONS_DIR = PIPELINE_CONTEXT_DIR / "skeletons"


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


def generate_skeleton(source_code: str) -> str:
    """Generate skeleton from source code."""
    tree = ast.parse(source_code)
    transformer = SkeletonTransformer()
    skeleton_tree = transformer.visit(tree)
    
    # Fix missing lineno/col_offset for new nodes
    ast.fix_missing_locations(skeleton_tree)
    
    return ast.unparse(skeleton_tree)


def count_tokens_approx(text: str) -> int:
    """Approximate token count (rough estimate: ~4 chars per token)."""
    return len(text) // 4


def generate_skeleton_file(source_path: Path, output_path: Path) -> Dict[str, Any]:
    """Generate skeleton for a single file."""
    content = source_path.read_text()
    
    try:
        skeleton_code = generate_skeleton(content)
        
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
    """Generate skeletons for all pipeline scripts."""
    print("=" * 60)
    print("Generating Code Skeletons")
    print("=" * 60)
    
    # Ensure output directory exists
    SKELETONS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Collect scripts to process
    stage_dirs = ["stage1_clean", "stage2_transform", "stage3_prepare"]
    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
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
            
            print(f"  Processing: {script_path.name}")
            
            stats = generate_skeleton_file(script_path, output_path)
            
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
        json.dump(results, f, indent=2)
    
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
