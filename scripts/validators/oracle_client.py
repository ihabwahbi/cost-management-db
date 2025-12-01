"""
Oracle Client: Clean interface to Oracle artifacts.

Provides dependency injection for testing and graceful degradation.

Usage:
    from scripts.validators.oracle_client import OracleClient

    oracle = OracleClient()
    if oracle.is_available:
        functions = oracle.get_functions()
        columns = oracle.get_columns()
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class OracleClient:
    """Unified access to Context Oracle artifacts."""

    def __init__(self, context_dir: Optional[Path] = None):
        if context_dir is None:
            # Auto-detect project root
            self.context_dir = Path(__file__).parent.parent.parent / "pipeline-context"
        else:
            self.context_dir = context_dir

        self._registry: Optional[Dict] = None
        self._lineage: Optional[Dict] = None
        self._patterns: Optional[Dict] = None
        self._skeletons_index: Optional[Dict] = None

    @property
    def is_available(self) -> bool:
        """Check if Oracle artifacts exist."""
        registry_path = self.context_dir / "registry" / "symbols.json"
        lineage_path = self.context_dir / "lineage" / "graph.json"
        return registry_path.exists() and lineage_path.exists()

    # ========== Registry Access ==========

    def get_functions(self) -> List[Dict]:
        """Get all registered functions."""
        return self._load_registry().get("functions", [])

    def get_constants(self) -> List[Dict]:
        """Get all registered constants."""
        return self._load_registry().get("constants", [])

    def get_columns(self) -> Dict[str, Dict]:
        """Get all tracked columns."""
        return self._load_registry().get("columns", {})

    def get_tables(self) -> List[Dict]:
        """Get all database tables."""
        return self._load_registry().get("tables", [])

    def get_function_by_name(self, name: str) -> Optional[Dict]:
        """Get a function by name."""
        for func in self.get_functions():
            if func["name"] == name:
                return func
        return None

    def get_column_info(self, column_name: str) -> Optional[Dict]:
        """Get column information."""
        columns = self.get_columns()
        return columns.get(column_name)

    # ========== Lineage Access ==========

    def get_nodes(self) -> Dict[str, Dict]:
        """Get all nodes in lineage graph."""
        return self._load_lineage().get("nodes", {})

    def get_edges(self) -> List[Dict]:
        """Get all edges in lineage graph."""
        return self._load_lineage().get("edges", [])

    def get_column_access(self) -> Dict[str, List[Dict]]:
        """Get column access patterns."""
        return self._load_lineage().get("column_access", {})

    def get_column_writers(self, column: str) -> Set[str]:
        """Get scripts that write to a column."""
        column_access = self.get_column_access()
        writers = set()
        for access in column_access.get(column, []):
            if access.get("type") == "WRITES":
                writers.add(access.get("script", ""))
        return writers

    def get_column_readers(self, column: str) -> Set[str]:
        """Get scripts that read a column."""
        column_access = self.get_column_access()
        readers = set()
        for access in column_access.get(column, []):
            if access.get("type") == "READS":
                readers.add(access.get("script", ""))
        return readers

    def get_script_outputs(self, script: str) -> Set[str]:
        """Get files output by a script."""
        edges = self.get_edges()
        outputs = set()
        script_id = f"script:{script}"
        for edge in edges:
            if edge.get("source") == script_id and edge.get("type") == "OUTPUT":
                target = edge.get("target", "")
                if target.startswith("file:"):
                    outputs.add(target.replace("file:", ""))
        return outputs

    def get_script_inputs(self, script: str) -> Set[str]:
        """Get files input to a script."""
        edges = self.get_edges()
        inputs = set()
        script_id = f"script:{script}"
        for edge in edges:
            if edge.get("target") == script_id and edge.get("type") == "INPUT":
                source = edge.get("source", "")
                if source.startswith("file:"):
                    inputs.add(source.replace("file:", ""))
        return inputs

    def get_script_dependencies(self, script: str) -> Set[str]:
        """Get scripts that this script depends on."""
        edges = self.get_edges()
        deps = set()
        script_id = f"script:{script}"
        for edge in edges:
            if edge.get("source") == script_id and edge.get("type") == "DEPENDS_ON":
                target = edge.get("target", "")
                if target.startswith("script:"):
                    deps.add(target.replace("script:", ""))
        return deps

    def get_all_scripts(self) -> Set[str]:
        """Get all script names from lineage."""
        nodes = self.get_nodes()
        scripts = set()
        for node_id in nodes:
            if node_id.startswith("script:"):
                scripts.add(node_id.replace("script:", ""))
        return scripts

    # ========== Patterns Access ==========

    def get_pattern(self, pattern_name: str) -> Optional[Dict]:
        """Get a specific pattern by name."""
        patterns = self._load_patterns()
        return patterns.get("patterns", {}).get(pattern_name)

    def get_all_patterns(self) -> Dict[str, Dict]:
        """Get all available patterns."""
        return self._load_patterns().get("patterns", {})

    # ========== Skeletons Access ==========

    def get_skeletons_index(self) -> Dict:
        """Get the skeletons index."""
        if self._skeletons_index is None:
            path = self.context_dir / "skeletons" / "index.json"
            if path.exists():
                self._skeletons_index = json.loads(path.read_text())
            else:
                self._skeletons_index = {}
        return self._skeletons_index

    def get_skeleton_for_script(self, script_name: str) -> Optional[str]:
        """Get skeleton content for a script."""
        index = self.get_skeletons_index()
        for _stage, scripts in index.get("files", {}).items():
            for script_info in scripts:
                if script_info.get("script") == script_name:
                    skeleton_path = (
                        self.context_dir
                        / "skeletons"
                        / script_info.get("skeleton_path", "")
                    )
                    if skeleton_path.exists():
                        return skeleton_path.read_text()
        return None

    # ========== Column Schema Extraction ==========

    def get_script_columns_written(self, script_name: str) -> Set[str]:
        """Get columns written by a script."""
        column_access = self.get_column_access()
        written = set()
        for col_name, accesses in column_access.items():
            for access in accesses:
                if (
                    access.get("script") == script_name
                    and access.get("type") == "WRITES"
                ):
                    written.add(col_name)
        return written

    def get_script_columns_read(self, script_name: str) -> Set[str]:
        """Get columns read by a script."""
        column_access = self.get_column_access()
        read = set()
        for col_name, accesses in column_access.items():
            for access in accesses:
                if (
                    access.get("script") == script_name
                    and access.get("type") == "READS"
                ):
                    read.add(col_name)
        return read

    # ========== Health Check ==========

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of Oracle artifacts."""
        status = {
            "available": self.is_available,
            "registry": {"exists": False, "functions": 0, "columns": 0, "tables": 0},
            "lineage": {"exists": False, "nodes": 0, "edges": 0},
            "patterns": {"exists": False, "count": 0},
            "skeletons": {"exists": False, "count": 0},
        }

        # Check registry
        registry_path = self.context_dir / "registry" / "symbols.json"
        if registry_path.exists():
            registry = self._load_registry()
            status["registry"] = {
                "exists": True,
                "functions": len(registry.get("functions", [])),
                "columns": len(registry.get("columns", {})),
                "tables": len(registry.get("tables", [])),
                "constants": len(registry.get("constants", [])),
            }

        # Check lineage
        lineage_path = self.context_dir / "lineage" / "graph.json"
        if lineage_path.exists():
            lineage = self._load_lineage()
            status["lineage"] = {
                "exists": True,
                "nodes": len(lineage.get("nodes", {})),
                "edges": len(lineage.get("edges", [])),
                "column_access": len(lineage.get("column_access", {})),
            }

        # Check patterns
        patterns_path = self.context_dir / "patterns" / "index.json"
        if patterns_path.exists():
            patterns = self._load_patterns()
            status["patterns"] = {
                "exists": True,
                "count": len(patterns.get("patterns", {})),
            }

        # Check skeletons
        skeletons_path = self.context_dir / "skeletons" / "index.json"
        if skeletons_path.exists():
            index = self.get_skeletons_index()
            total_files = sum(
                len(scripts) for scripts in index.get("files", {}).values()
            )
            status["skeletons"] = {
                "exists": True,
                "count": total_files,
            }

        return status

    # ========== Private Methods ==========

    def _load_registry(self) -> Dict:
        """Load the symbol registry."""
        if self._registry is None:
            path = self.context_dir / "registry" / "symbols.json"
            if path.exists():
                self._registry = json.loads(path.read_text())
            else:
                self._registry = {}
        return self._registry

    def _load_lineage(self) -> Dict:
        """Load the lineage graph."""
        if self._lineage is None:
            path = self.context_dir / "lineage" / "graph.json"
            if path.exists():
                self._lineage = json.loads(path.read_text())
            else:
                self._lineage = {}
        return self._lineage

    def _load_patterns(self) -> Dict:
        """Load the pattern library."""
        if self._patterns is None:
            path = self.context_dir / "patterns" / "index.json"
            if path.exists():
                self._patterns = json.loads(path.read_text())
            else:
                self._patterns = {}
        return self._patterns


if __name__ == "__main__":
    # Quick test
    oracle = OracleClient()
    print(f"Oracle available: {oracle.is_available}")
    if oracle.is_available:
        status = oracle.get_health_status()
        print(f"Health: {json.dumps(status, indent=2)}")
