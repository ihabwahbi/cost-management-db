#!/usr/bin/env python3
"""
Schema Lock: Track output schema changes.

Uses inverted contract generation:
- Code generates schema, we track changes via diff
- No manual YAML sync needed

Usage:
    python scripts/validators/schema_lock.py --check    # Verify schemas match lock
    python scripts/validators/schema_lock.py --update   # Update lock file
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

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


PROJECT_ROOT = Path(__file__).parent.parent.parent
LOCK_FILE = PROJECT_ROOT / "schema_lock.json"


def compute_schema_hash(columns: List[str]) -> str:
    """Deterministic hash of column list."""
    normalized = sorted([c.lower().strip() for c in columns])
    return hashlib.sha256(json.dumps(normalized).encode()).hexdigest()[:16]


def get_current_schemas(oracle: OracleClient) -> Dict[str, Dict]:
    """
    Extract current schemas from Oracle lineage.

    Returns a dict of script_name -> {columns, hash, count}
    """
    schemas = {}

    # Get all scripts
    all_scripts = oracle.get_all_scripts()

    for script in sorted(all_scripts):
        # Get columns written by this script
        columns_written = oracle.get_script_columns_written(script)

        if columns_written:
            sorted_columns = sorted(columns_written)
            schemas[script] = {
                "columns": sorted_columns,
                "hash": compute_schema_hash(sorted_columns),
                "count": len(sorted_columns),
            }

    return schemas


def check_lock(verbose: bool = True) -> bool:  # noqa: C901
    """Check if current schemas match lock file."""
    oracle = OracleClient()

    if not oracle.is_available:
        if verbose:
            print("Warning: Oracle not available, skipping schema check")
        return True  # Graceful degradation

    current = get_current_schemas(oracle)

    if not LOCK_FILE.exists():
        if verbose:
            print("schema_lock.json not found. Run with --update to create.")
        return False

    locked = json.loads(LOCK_FILE.read_text())
    locked_schemas = locked.get("schemas", {})

    mismatches = []
    new_scripts = []
    removed_scripts = []

    # Check for new or changed scripts
    for script, schema in current.items():
        if script not in locked_schemas:
            new_scripts.append(f"NEW: {script} ({schema['count']} columns)")
        elif schema["hash"] != locked_schemas[script]["hash"]:
            old_cols = set(locked_schemas[script]["columns"])
            new_cols = set(schema["columns"])
            added = new_cols - old_cols
            removed = old_cols - new_cols

            details = []
            if added:
                details.append(f"+{list(added)[:3]}")
            if removed:
                details.append(f"-{list(removed)[:3]}")

            mismatches.append(
                f"CHANGED: {script} (+{len(added)} -{len(removed)} cols) "
                f"{' '.join(details)}"
            )

    # Check for removed scripts
    for script in locked_schemas:
        if script not in current:
            removed_scripts.append(f"REMOVED: {script}")

    all_issues = new_scripts + mismatches + removed_scripts

    if all_issues:
        if verbose:
            print("Schema changes detected:")
            for issue in all_issues:
                print(f"  {issue}")
            print("\nRun: python scripts/validators/schema_lock.py --update")
        return False

    if verbose:
        print(f"Schema lock valid: {len(current)} scripts verified")
    return True


def update_lock(verbose: bool = True) -> None:
    """Update lock file with current schemas."""
    oracle = OracleClient()

    if not oracle.is_available:
        print("Error: Oracle not available. Run generate_context_oracle.py first.")
        sys.exit(1)

    current = get_current_schemas(oracle)

    lock_data = {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schemas": current,
        "total_scripts": len(current),
        "total_columns": sum(s["count"] for s in current.values()),
    }

    LOCK_FILE.write_text(json.dumps(lock_data, indent=2))

    if verbose:
        print(
            f"Schema lock updated: {len(current)} scripts, "
            f"{lock_data['total_columns']} columns tracked"
        )


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Schema Lock Validator")
    parser.add_argument(
        "--update", action="store_true", help="Update lock file with current schemas"
    )
    parser.add_argument(
        "--check", action="store_true", help="Check if schemas match lock file"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress output (exit code only)"
    )

    args = parser.parse_args()
    verbose = not args.quiet

    if args.update:
        update_lock(verbose)
        sys.exit(0)
    elif args.check or not args.update:
        # Default to check
        success = check_lock(verbose)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
