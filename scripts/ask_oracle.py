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


def output_json(data: Dict) -> None:
    """Output JSON to stdout (strict, minified for agents)."""
    print(json.dumps(data, separators=(',', ':')))


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
    """Predict impact of changing a script."""
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
    
    # Find all downstream dependencies
    affected_scripts = set()
    affected_columns = set()
    affected_tables = set()
    
    for output in outputs:
        output_id = f"file:{output}"
        downstream = trace_downstream(edges, output_id)
        
        for item in downstream:
            node = item["node"]
            if node.startswith("script:"):
                affected_scripts.add(node.replace("script:", ""))
            elif node.startswith("column:"):
                affected_columns.add(node.replace("column:", ""))
            elif node.startswith("table:"):
                affected_tables.add(node.replace("table:", ""))
    
    # Calculate risk level
    risk_level = "low"
    if len(affected_scripts) >= 3 or len(affected_tables) >= 2:
        risk_level = "high"
    elif len(affected_scripts) >= 1 or len(affected_columns) >= 2:
        risk_level = "medium"
    
    # Generate recommendation
    if risk_level == "high":
        recommendation = f"High-risk change: affects {len(affected_scripts)} downstream scripts and {len(affected_tables)} tables. Test all stages thoroughly."
    elif risk_level == "medium":
        recommendation = "Medium-risk change: verify downstream transformations after modification."
    else:
        recommendation = "Low-risk change: limited downstream impact."
    
    return {
        "script": script_name,
        "outputs": outputs,
        "affected_scripts": sorted(affected_scripts),
        "affected_columns": sorted(affected_columns),
        "affected_tables": sorted(affected_tables),
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
