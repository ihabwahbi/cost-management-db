#!/usr/bin/env python3
"""
Context Oracle CLI Query Tool

A command-line interface to query the Context Oracle artifacts.
All output is strict JSON for easy agent consumption.

Subcommands:
  verify  - Verify if a symbol exists
  impact  - Predict impact of changing a script
  trace   - Trace column/file lineage  
  pattern - Get pattern for a task type
  search  - Search for similar symbols

Exit Codes:
  0 - Success (including logical errors like "not found")
  1 - System error (script crash, missing files)

Usage:
    python3 scripts/ask_oracle.py verify filter_valuation_classes
    python3 scripts/ask_oracle.py impact 05_calculate_cost_impact
    python3 scripts/ask_oracle.py trace open_po_value --direction upstream
    python3 scripts/ask_oracle.py pattern pipeline_script
    python3 scripts/ask_oracle.py search calculate
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher

# Paths
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent
PIPELINE_CONTEXT_DIR = PROJECT_ROOT / "pipeline-context"
REGISTRY_FILE = PIPELINE_CONTEXT_DIR / "registry" / "symbols.json"
LINEAGE_FILE = PIPELINE_CONTEXT_DIR / "lineage" / "graph.json"
PATTERNS_FILE = PIPELINE_CONTEXT_DIR / "patterns" / "index.json"
SKELETONS_INDEX = PIPELINE_CONTEXT_DIR / "skeletons" / "index.json"

# Source directories to monitor for freshness
SOURCE_DIRS = [
    SCRIPTS_DIR / "stage1_clean",
    SCRIPTS_DIR / "stage2_transform",
    SCRIPTS_DIR / "stage3_prepare",
    SCRIPTS_DIR / "config",
    PROJECT_ROOT / "src" / "schema",
]


def output_json(data: Dict) -> None:
    """Output JSON to stdout (strict, minified for agents)."""
    print(json.dumps(data, separators=(',', ':')))


def get_latest_source_mtime() -> float:
    """Get the most recent modification time of any source file."""
    latest_mtime = 0.0
    
    for source_dir in SOURCE_DIRS:
        if not source_dir.exists():
            continue
        # Check Python files in pipeline scripts
        for pattern in ["*.py", "*.ts"]:
            for filepath in source_dir.glob(pattern):
                mtime = filepath.stat().st_mtime
                if mtime > latest_mtime:
                    latest_mtime = mtime
    
    return latest_mtime


def get_artifacts_mtime() -> float:
    """Get the modification time of the artifacts (use registry as proxy)."""
    if not REGISTRY_FILE.exists():
        return 0.0
    return REGISTRY_FILE.stat().st_mtime


def check_and_regenerate_if_stale(silent: bool = False) -> bool:
    """
    Check if artifacts are stale and regenerate if needed.
    
    Returns True if regeneration occurred, False otherwise.
    Exits with code 1 if regeneration fails (prevents agent from using broken context).
    """
    import subprocess
    
    source_mtime = get_latest_source_mtime()
    artifacts_mtime = get_artifacts_mtime()
    
    # Also check if the generator script itself changed
    generator_script = SCRIPTS_DIR / "generate_context_oracle.py"
    if generator_script.exists():
        gen_mtime = generator_script.stat().st_mtime
        if gen_mtime > artifacts_mtime:
            source_mtime = max(source_mtime, gen_mtime)
    
    # Check root scripts directory for pipeline.py etc
    for root_script in SCRIPTS_DIR.glob("*.py"):
        if root_script.name.startswith("__"):
            continue
        script_mtime = root_script.stat().st_mtime
        if script_mtime > source_mtime:
            source_mtime = script_mtime
    
    needs_regen = artifacts_mtime == 0.0 or source_mtime > artifacts_mtime
    
    if needs_regen:
        if not silent:
            if artifacts_mtime == 0.0:
                print("Oracle artifacts not found. Generating...", file=sys.stderr)
            else:
                print("Oracle artifacts are stale. Regenerating...", file=sys.stderr)
        
        try:
            subprocess.run(
                [sys.executable, str(generator_script)],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
                check=True  # Raise CalledProcessError on failure
            )
        except subprocess.CalledProcessError as e:
            print(f"CRITICAL: Oracle generation failed!\n{e.stderr}", file=sys.stderr)
            sys.exit(1)  # Hard stop - don't let agent continue with broken context
        
        return True
    
    return False


def load_registry() -> Optional[Dict]:
    """Load the symbol registry."""
    if not REGISTRY_FILE.exists():
        return None
    with open(REGISTRY_FILE) as f:
        return json.load(f)


def load_lineage() -> Optional[Dict]:
    """Load the lineage graph."""
    if not LINEAGE_FILE.exists():
        return None
    with open(LINEAGE_FILE) as f:
        return json.load(f)


def load_patterns() -> Optional[Dict]:
    """Load the pattern library."""
    if not PATTERNS_FILE.exists():
        return None
    with open(PATTERNS_FILE) as f:
        return json.load(f)


# =============================================================================
# VERIFY - Check if a symbol exists
# =============================================================================

def find_similar(query: str, registry: Dict, limit: int = 3) -> List[Dict]:
    """Find symbols similar to query."""
    all_names = []
    
    for func in registry.get("functions", []):
        all_names.append({
            "name": func["name"], 
            "type": "function", 
            "location": f"{func['file']}:{func['line']}"
        })
    
    for const in registry.get("constants", []):
        all_names.append({
            "name": const["name"], 
            "type": "constant", 
            "location": f"{const['file']}:{const['line']}"
        })
    
    for col_name in registry.get("columns", {}):
        all_names.append({
            "name": col_name, 
            "type": "column",
            "location": None
        })
    
    for table in registry.get("tables", []):
        all_names.append({
            "name": table["name"], 
            "type": "table", 
            "location": table["file"]
        })
    
    # Score by similarity
    query_lower = query.lower()
    scored = []
    
    for item in all_names:
        name_lower = item["name"].lower()
        ratio = SequenceMatcher(None, query_lower, name_lower).ratio()
        
        # Boost substring matches
        if query_lower in name_lower or name_lower in query_lower:
            ratio = max(ratio, 0.8)
        
        if ratio > 0.3:
            scored.append((ratio, item))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:limit]]


def cmd_verify(args) -> Dict:
    """Verify if a symbol exists."""
    registry = load_registry()
    if not registry:
        return {"error": "Symbol registry not found. Run generate_context_oracle.py first."}
    
    name = args.name
    symbol_type = args.type
    
    # Search functions
    if symbol_type in ("function", "any"):
        for func in registry.get("functions", []):
            if func["name"] == name:
                return {
                    "found": True,
                    "type": "function",
                    "location": f"{func['file']}:{func['line']}",
                    "signature": func.get("signature"),
                    "docstring": func.get("docstring")
                }
    
    # Search constants
    if symbol_type in ("constant", "any"):
        for const in registry.get("constants", []):
            if const["name"] == name:
                return {
                    "found": True,
                    "type": "constant",
                    "location": f"{const['file']}:{const['line']}",
                    "value_type": const.get("value_type"),
                    "value_preview": const.get("value_preview")
                }
    
    # Search columns
    if symbol_type in ("column", "any"):
        columns = registry.get("columns", {})
        if name in columns:
            col = columns[name]
            return {
                "found": True,
                "type": "column",
                "sources": col.get("sources", []),
                "dtype": col.get("dtype"),
                "used_in": col.get("used_in", []),
                "created_by": col.get("created_by")
            }
    
    # Search tables
    if symbol_type in ("table", "any"):
        for table in registry.get("tables", []):
            if table["name"] == name:
                return {
                    "found": True,
                    "type": "table",
                    "location": table.get("file"),
                    "columns": table.get("columns", [])
                }
    
    # Not found - suggest similar
    similar = find_similar(name, registry)
    suggestion = None
    if similar:
        suggestion = f"Did you mean '{similar[0]['name']}'?"
    
    return {
        "found": False,
        "query": name,
        "query_type": symbol_type,
        "suggestion": suggestion,
        "similar": similar
    }


# =============================================================================
# IMPACT - Predict downstream impact of changing a script
# =============================================================================

def trace_downstream(edges: List[Dict], node_id: str, max_depth: int = 10) -> List[Dict]:
    """Trace all nodes downstream from the given node."""
    visited = set()
    result = []
    
    def _trace(current_id: str, depth: int):
        if current_id in visited or depth > max_depth:
            return
        visited.add(current_id)
        
        for edge in edges:
            if edge["source"] == current_id:
                target = edge["target"]
                result.append({
                    "node": target,
                    "edge_type": edge["type"],
                    "depth": depth
                })
                _trace(target, depth + 1)
    
    _trace(node_id, 0)
    return result


def cmd_impact(args) -> Dict:
    """
    Predict impact of changing a script.
    
    Fix 3: Returns tiered impact classification:
      - direct_writers: Scripts that WRITE to the same columns
      - column_readers: Scripts that READ columns this script WRITES
      - file_consumers: Scripts that consume output files
      - passthrough: Scripts that just pass data through
    """
    lineage = load_lineage()
    if not lineage:
        return {"error": "Lineage graph not found. Run generate_context_oracle.py first."}
    
    script_name = args.script
    # Strip common prefixes/suffixes
    script_name = script_name.replace(".py", "").replace("scripts/", "")
    for prefix in ["stage1_clean/", "stage2_transform/", "stage3_prepare/"]:
        script_name = script_name.replace(prefix, "")
    
    script_id = f"script:{script_name}"
    nodes = lineage.get("nodes", {})
    edges = lineage.get("edges", [])
    column_access = lineage.get("column_access", {})
    
    if script_id not in nodes:
        # Try to find similar script names
        script_names = [n.replace("script:", "") for n in nodes if n.startswith("script:")]
        return {
            "error": f"Script '{script_name}' not found",
            "available_scripts": script_names
        }
    
    # Find outputs of this script
    outputs = []
    for edge in edges:
        if edge["source"] == script_id and edge["type"] == "OUTPUT":
            outputs.append(edge["target"].replace("file:", ""))
    
    # Fix 3: Find columns this script WRITES
    columns_written = set()
    columns_read = set()
    for col, accesses in column_access.items():
        for access in accesses:
            if access.get("script") == script_name:
                if access.get("type") == "WRITES":
                    columns_written.add(col)
                elif access.get("type") == "READS":
                    columns_read.add(col)
    
    # Fix 3: Tiered impact classification
    direct_writers = set()      # Scripts that also WRITE to same columns
    column_readers = set()       # Scripts that READ columns we WRITE
    file_consumers = set()       # Scripts that consume our output files
    
    # Find scripts that interact with columns we write
    for col in columns_written:
        if col in column_access:
            for access in column_access[col]:
                other_script = access.get("script", "")
                if other_script and other_script != script_name:
                    if access.get("type") == "WRITES":
                        direct_writers.add(other_script)
                    elif access.get("type") == "READS":
                        column_readers.add(other_script)
    
    # Find scripts that consume output files (legacy traversal)
    for output in outputs:
        output_id = f"file:{output}"
        downstream = trace_downstream(edges, output_id)
        
        for item in downstream:
            node = item["node"]
            if node.startswith("script:"):
                other_script = node.replace("script:", "")
                if other_script != script_name:
                    # If not already a column reader/writer, it's a file consumer
                    if other_script not in column_readers and other_script not in direct_writers:
                        file_consumers.add(other_script)
    
    # All affected scripts
    all_affected = direct_writers | column_readers | file_consumers
    
    # Calculate risk level based on tiered impact
    risk_level = "low"
    if len(column_readers) >= 2 or len(direct_writers) >= 1:
        risk_level = "high"
    elif len(column_readers) >= 1 or len(file_consumers) >= 2:
        risk_level = "medium"
    
    # Generate detailed recommendation
    if risk_level == "high":
        parts = []
        if direct_writers:
            parts.append(f"{len(direct_writers)} scripts also write to same columns")
        if column_readers:
            parts.append(f"{len(column_readers)} scripts read columns you modify")
        detail = "; ".join(parts) if parts else f"affects {len(columns_written)} columns"
        scripts_to_test = list(column_readers)[:3]
        recommendation = f"High-risk change: {detail}. Test affected scripts: {scripts_to_test}"
    elif risk_level == "medium":
        recommendation = f"Medium-risk change: {len(column_readers)} downstream readers. Verify transformations."
    else:
        recommendation = "Low-risk change: limited downstream impact."
    
    return {
        "script": script_name,
        "outputs": outputs,
        "columns_modified": sorted(columns_written),
        "columns_read": sorted(columns_read),
        # Fix 3: Tiered classification
        "tiered_impact": {
            "direct_writers": sorted(direct_writers),
            "column_readers": sorted(column_readers),
            "file_consumers": sorted(file_consumers)
        },
        # Legacy format for backward compatibility
        "affected_scripts": sorted(all_affected),
        "risk_level": risk_level,
        "recommendation": recommendation
    }


# =============================================================================
# TRACE - Trace column/file lineage
# =============================================================================

def trace_upstream(edges: List[Dict], node_id: str, max_depth: int = 10) -> List[Dict]:
    """Trace all nodes upstream from the given node."""
    visited = set()
    result = []
    
    def _trace(current_id: str, depth: int):
        if current_id in visited or depth > max_depth:
            return
        visited.add(current_id)
        
        for edge in edges:
            if edge["target"] == current_id:
                source = edge["source"]
                edge_info = {
                    "node": source,
                    "edge_type": edge["type"],
                    "depth": depth
                }
                # Include operation if present
                if "operation" in edge:
                    edge_info["operation"] = edge["operation"]
                if "file" in edge and "line" in edge:
                    edge_info["location"] = f"{edge['file']}:{edge['line']}"
                
                result.append(edge_info)
                _trace(source, depth + 1)
    
    _trace(node_id, 0)
    return result


def cmd_trace(args) -> Dict:
    """Trace lineage of a column or file."""
    lineage = load_lineage()
    if not lineage:
        return {"error": "Lineage graph not found. Run generate_context_oracle.py first."}
    
    target = args.target
    direction = args.direction
    
    nodes = lineage.get("nodes", {})
    edges = lineage.get("edges", [])
    
    # Determine node type and ID
    node_id = None
    node_type = None
    
    # Try different node ID formats
    candidates = [
        f"column:{target}",
        f"file:{target}",
        f"script:{target}",
        f"table:{target}",
        target  # Raw ID
    ]
    
    for candidate in candidates:
        if candidate in nodes:
            node_id = candidate
            node_type = nodes[candidate].get("type", "unknown")
            break
    
    if not node_id:
        return {
            "error": f"Node '{target}' not found in lineage graph",
            "hint": "Try using a column name, file path, or script name"
        }
    
    result = {
        "target": target,
        "node_id": node_id,
        "node_type": node_type,
        "direction": direction
    }
    
    if direction in ("upstream", "both"):
        result["upstream"] = trace_upstream(edges, node_id)
    
    if direction in ("downstream", "both"):
        result["downstream"] = trace_downstream(edges, node_id)
    
    # Extract critical files (files that appear in lineage)
    critical_files = set()
    for item in result.get("upstream", []) + result.get("downstream", []):
        node = item["node"]
        if node.startswith("file:"):
            critical_files.add(node.replace("file:", ""))
        elif node.startswith("script:"):
            script_node = nodes.get(node, {})
            if "path" in script_node:
                critical_files.add(script_node["path"])
    
    result["critical_files"] = sorted(critical_files)
    
    return result


# =============================================================================
# PATTERN - Get code pattern for a task type
# =============================================================================

def cmd_pattern(args) -> Dict:
    """Get pattern for a task type."""
    patterns = load_patterns()
    if not patterns:
        return {"error": "Pattern library not found. Run generate_context_oracle.py first."}
    
    pattern_name = args.pattern
    all_patterns = patterns.get("patterns", {})
    
    if pattern_name in all_patterns:
        return {
            "found": True,
            "pattern": all_patterns[pattern_name]
        }
    
    # Not found - list available patterns
    return {
        "found": False,
        "query": pattern_name,
        "available_patterns": list(all_patterns.keys()),
        "hint": "Use one of the available pattern names"
    }


# =============================================================================
# SEARCH - Search for similar symbols
# =============================================================================

def cmd_search(args) -> Dict:
    """Search for symbols matching a query."""
    registry = load_registry()
    if not registry:
        return {"error": "Symbol registry not found. Run generate_context_oracle.py first."}
    
    query = args.query
    limit = args.limit
    symbol_type = args.type
    
    all_matches = []
    
    # Search functions
    if symbol_type in ("function", "any"):
        for func in registry.get("functions", []):
            name = func["name"]
            ratio = SequenceMatcher(None, query.lower(), name.lower()).ratio()
            if query.lower() in name.lower():
                ratio = max(ratio, 0.8)
            if ratio > 0.3:
                all_matches.append({
                    "name": name,
                    "type": "function",
                    "location": f"{func['file']}:{func['line']}",
                    "signature": func.get("signature"),
                    "score": ratio
                })
    
    # Search constants
    if symbol_type in ("constant", "any"):
        for const in registry.get("constants", []):
            name = const["name"]
            ratio = SequenceMatcher(None, query.lower(), name.lower()).ratio()
            if query.lower() in name.lower():
                ratio = max(ratio, 0.8)
            if ratio > 0.3:
                all_matches.append({
                    "name": name,
                    "type": "constant",
                    "location": f"{const['file']}:{const['line']}",
                    "score": ratio
                })
    
    # Search columns
    if symbol_type in ("column", "any"):
        for col_name, col_data in registry.get("columns", {}).items():
            ratio = SequenceMatcher(None, query.lower(), col_name.lower()).ratio()
            if query.lower() in col_name.lower():
                ratio = max(ratio, 0.8)
            if ratio > 0.3:
                all_matches.append({
                    "name": col_name,
                    "type": "column",
                    "sources": col_data.get("sources", [])[:2],  # Limit sources
                    "score": ratio
                })
    
    # Search tables
    if symbol_type in ("table", "any"):
        for table in registry.get("tables", []):
            name = table["name"]
            ratio = SequenceMatcher(None, query.lower(), name.lower()).ratio()
            if query.lower() in name.lower():
                ratio = max(ratio, 0.8)
            if ratio > 0.3:
                all_matches.append({
                    "name": name,
                    "type": "table",
                    "location": table.get("file"),
                    "score": ratio
                })
    
    # Sort by score and limit
    all_matches.sort(key=lambda x: x["score"], reverse=True)
    results = all_matches[:limit]
    
    # Remove score from output (internal use only)
    for r in results:
        del r["score"]
    
    return {
        "query": query,
        "count": len(results),
        "results": results
    }


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Context Oracle CLI Query Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/ask_oracle.py verify filter_valuation_classes
  python3 scripts/ask_oracle.py impact 05_calculate_cost_impact
  python3 scripts/ask_oracle.py trace open_po_value --direction upstream
  python3 scripts/ask_oracle.py pattern pipeline_script
  python3 scripts/ask_oracle.py search calculate --limit 10
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # verify subcommand
    verify_parser = subparsers.add_parser("verify", help="Verify if a symbol exists")
    verify_parser.add_argument("name", help="Symbol name to verify")
    verify_parser.add_argument(
        "--type", "-t",
        choices=["function", "constant", "column", "table", "any"],
        default="any",
        help="Type of symbol to search for (default: any)"
    )
    
    # impact subcommand
    impact_parser = subparsers.add_parser("impact", help="Predict impact of changing a script")
    impact_parser.add_argument("script", help="Script name (e.g., 05_calculate_cost_impact)")
    
    # trace subcommand
    trace_parser = subparsers.add_parser("trace", help="Trace column/file lineage")
    trace_parser.add_argument("target", help="Column, file, or script name to trace")
    trace_parser.add_argument(
        "--direction", "-d",
        choices=["upstream", "downstream", "both"],
        default="both",
        help="Direction to trace (default: both)"
    )
    
    # pattern subcommand
    pattern_parser = subparsers.add_parser("pattern", help="Get pattern for a task type")
    pattern_parser.add_argument("pattern", help="Pattern name (e.g., pipeline_script)")
    
    # search subcommand
    search_parser = subparsers.add_parser("search", help="Search for similar symbols")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "--limit", "-l",
        type=int,
        default=5,
        help="Maximum results to return (default: 5)"
    )
    search_parser.add_argument(
        "--type", "-t",
        choices=["function", "constant", "column", "table", "any"],
        default="any",
        help="Type of symbol to search for (default: any)"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    # Freshness Guard: Auto-regenerate stale artifacts before any command
    check_and_regenerate_if_stale(silent=False)
    
    try:
        if args.command == "verify":
            result = cmd_verify(args)
        elif args.command == "impact":
            result = cmd_impact(args)
        elif args.command == "trace":
            result = cmd_trace(args)
        elif args.command == "pattern":
            result = cmd_pattern(args)
        elif args.command == "search":
            result = cmd_search(args)
        else:
            result = {"error": f"Unknown command: {args.command}"}
        
        output_json(result)
        sys.exit(0)
        
    except Exception as e:
        # System error - exit code 1
        output_json({"error": f"System error: {str(e)}"})
        sys.exit(1)


if __name__ == "__main__":
    main()
