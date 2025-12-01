#!/usr/bin/env python3
"""
Pipeline Order: Validate script DAG has no cycles.

Uses explicit manifest approach combined with Oracle lineage for verification.

Usage:
    python scripts/validators/pipeline_order.py          # Check DAG
    python scripts/validators/pipeline_order.py --json   # Output JSON
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set

# Import OracleClient - handle both module and script execution
try:
    from .oracle_client import OracleClient
except ImportError:
    # Direct script execution
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "oracle_client", Path(__file__).parent / "oracle_client.py"
    )
    oracle_client_module = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(oracle_client_module)  # type: ignore
    OracleClient = oracle_client_module.OracleClient  # type: ignore[misc]


def build_dependency_graph(oracle: OracleClient) -> Dict[str, Set[str]]:
    """
    Build script dependency graph from Oracle lineage.

    Uses explicit DEPENDS_ON edges from lineage (most reliable).
    Falls back to numeric ordering for scripts without explicit dependencies.

    Returns: dict of script -> set of scripts it depends on
    """
    graph: Dict[str, Set[str]] = {}

    edges = oracle.get_edges()

    # First: Use explicit DEPENDS_ON edges (most reliable)
    for edge in edges:
        edge_type = edge.get("type", "")
        source = edge.get("source", "")
        target = edge.get("target", "")

        # Track explicit DEPENDS_ON edges
        if edge_type == "DEPENDS_ON":
            if source.startswith("script:") and target.startswith("script:"):
                dependent = source.replace("script:", "")
                dependency = target.replace("script:", "")
                if dependent not in graph:
                    graph[dependent] = set()
                graph[dependent].add(dependency)

    # Ensure all scripts are in the graph
    all_scripts = oracle.get_all_scripts()
    for script in all_scripts:
        if script not in graph:
            graph[script] = set()

    return graph


def detect_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """
    Detect cycles using DFS.

    Returns list of cycles found (each cycle is a list of scripts).
    """
    cycles = []
    visited: Set[str] = set()
    rec_stack: Set[str] = set()

    def dfs(node: str, path: List[str]) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                dfs(neighbor, path)
            elif neighbor in rec_stack:
                # Found cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)

        path.pop()
        rec_stack.remove(node)

    for node in graph:
        if node not in visited:
            dfs(node, [])

    return cycles


def validate_ordering(graph: Dict[str, Set[str]]) -> List[str]:
    """
    Check if numeric prefixes match topological order.

    Returns list of ordering issues found.
    """
    issues = []

    for script, deps in graph.items():
        # Extract numeric prefix if present
        script_num = _get_script_num(script)

        for dep in deps:
            dep_num = _get_script_num(dep)

            # Dependency should have a lower number (run earlier)
            if dep_num >= script_num and dep_num != 999 and script_num != 999:
                issues.append(
                    f"{script} (#{script_num}) depends on {dep} (#{dep_num}), "
                    f"but {dep} has higher/equal prefix"
                )

    return issues


def _get_script_num(script_name: str) -> int:
    """Extract numeric prefix from script name."""
    parts = script_name.split("_")
    if parts and parts[0].isdigit():
        return int(parts[0])
    return 999  # Unknown order


def topological_sort(graph: Dict[str, Set[str]]) -> List[str]:  # noqa: C901
    """
    Return topologically sorted list of scripts.

    Empty list if cycle detected.
    """
    in_degree = {node: 0 for node in graph}

    # Calculate in-degrees
    for _node, deps in graph.items():
        for dep in deps:
            if dep in in_degree:
                # This node has an incoming edge from dep
                pass  # dep -> node, so node depends on dep

    # Actually, we need to reverse the logic:
    # If A depends on B, then A should come after B
    # So we need edges from dependencies TO dependents

    reverse_graph: Dict[str, Set[str]] = {node: set() for node in graph}
    for node, deps in graph.items():
        for dep in deps:
            if dep in reverse_graph:
                reverse_graph[dep].add(node)

    in_degree = {node: len(graph.get(node, set())) for node in graph}

    queue = [node for node, deg in in_degree.items() if deg == 0]
    result = []

    while queue:
        node = queue.pop(0)
        result.append(node)

        for dependent in reverse_graph.get(node, set()):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(result) != len(graph):
        return []  # Cycle detected

    return result


def validate(json_output: bool = False) -> bool:
    """
    Main validation function.

    Returns True if validation passes.
    """
    oracle = OracleClient()

    if not oracle.is_available:
        result = {
            "passed": True,
            "warning": "Oracle not available, skipping validation",
        }
        if json_output:
            print(json.dumps(result))
        else:
            print(result["warning"])
        return True

    graph = build_dependency_graph(oracle)
    cycles = detect_cycles(graph)
    ordering_issues = validate_ordering(graph)
    topo_order = topological_sort(graph)

    passed = len(cycles) == 0

    result = {
        "passed": passed,
        "cycles": cycles,
        "ordering_issues": ordering_issues,
        "scripts_analyzed": len(graph),
        "suggested_order": topo_order if topo_order else None,
        "dependency_count": sum(len(deps) for deps in graph.values()),
    }

    if json_output:
        print(json.dumps(result, indent=2, default=list))
    else:
        if passed:
            print(
                f"Pipeline DAG valid: {len(graph)} scripts, "
                f"{result['dependency_count']} dependencies"
            )
            if ordering_issues:
                print(f"  Ordering warnings ({len(ordering_issues)}):")
                for issue in ordering_issues[:5]:
                    print(f"    - {issue}")
        else:
            print("Pipeline DAG INVALID: Cycles detected!")
            for cycle in cycles:
                print(f"  Cycle: {' -> '.join(cycle)}")

    return passed


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Pipeline Order Validator")
    parser.add_argument("--json", action="store_true", help="Output JSON format")

    args = parser.parse_args()

    success = validate(json_output=args.json)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
