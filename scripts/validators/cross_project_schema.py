#!/usr/bin/env python3
"""
Cross-Project Schema: Verify schemas are in sync with webapp.

This project owns the data schemas. The webapp (cost-management) imports them.
This validator ensures both projects have identical schema definitions.

FULLY DYNAMIC - no hardcoded table names. Handles:
- New tables added to either project
- Renamed/deleted tables
- Webapp-only tables (auto-detected)

Usage:
    python scripts/validators/cross_project_schema.py --check   # Verify sync
    python scripts/validators/cross_project_schema.py --sync    # Copy to webapp
    python scripts/validators/cross_project_schema.py --diff    # Show differences
"""

import hashlib
import sys
from pathlib import Path
from typing import Dict, Set, Tuple

PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_SCHEMA_DIR = PROJECT_ROOT / "src" / "schema"
WEBAPP_SCHEMA_DIR = (
    PROJECT_ROOT.parent / "cost-management" / "packages" / "db" / "src" / "schema"
)


def get_schema_files(schema_dir: Path) -> Set[str]:
    """Get all schema .ts files in a directory (excluding index.ts)."""
    if not schema_dir.exists():
        return set()
    return {f.name for f in schema_dir.glob("*.ts") if f.name != "index.ts"}


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA-256 hash of file content (normalized)."""
    if not filepath.exists():
        return ""
    content = filepath.read_text().strip()
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def get_webapp_only_files() -> Set[str]:
    """
    Dynamically detect webapp-only schema files.

    These are files that exist in webapp but NOT in DB project.
    Future-proof: no hardcoding needed.
    """
    db_files = get_schema_files(DB_SCHEMA_DIR)
    webapp_files = get_schema_files(WEBAPP_SCHEMA_DIR)
    return webapp_files - db_files


def get_orphaned_files() -> Set[str]:
    """
    Detect orphaned files in webapp.

    These are files that:
    - Exist in webapp
    - Don't exist in DB project
    - Are NOT webapp-only (i.e., they USED to come from DB but were deleted/renamed)

    We detect this by checking if the file follows data schema patterns.
    Webapp-only = auth-related (contains auth keywords in name)
    """
    db_files = get_schema_files(DB_SCHEMA_DIR)
    webapp_files = get_schema_files(WEBAPP_SCHEMA_DIR)

    # Files in webapp but not in DB
    extra_in_webapp = webapp_files - db_files

    # Heuristic: auth-related files are webapp-only, others are orphaned
    auth_keywords = {"user", "auth", "session", "registration", "token", "credential"}

    webapp_only = set()
    orphaned = set()

    for f in extra_in_webapp:
        stem = f.replace(".ts", "").replace("-", "_").lower()
        if any(kw in stem for kw in auth_keywords):
            webapp_only.add(f)
        else:
            orphaned.add(f)

    return orphaned


def _compare_schemas(db_files: Set[str]) -> Dict:
    """Compare DB and webapp schema files, return results dict."""
    results = {
        "ok": [],
        "drift": [],
        "missing_in_webapp": [],
        "orphaned_in_webapp": list(get_orphaned_files()),
        "webapp_only": list(get_webapp_only_files()),
    }

    for filename in sorted(db_files):
        db_file = DB_SCHEMA_DIR / filename
        webapp_file = WEBAPP_SCHEMA_DIR / filename
        db_hash = compute_file_hash(db_file)
        webapp_hash = compute_file_hash(webapp_file)

        if not webapp_file.exists():
            results["missing_in_webapp"].append(filename)
        elif db_hash != webapp_hash:
            results["drift"].append(filename)
        else:
            results["ok"].append(filename)

    return results


def _print_check_results(results: Dict) -> None:
    """Print check_sync results to console."""
    has_issues = bool(results["drift"] or results["missing_in_webapp"])

    if has_issues:
        print("Cross-project schema drift detected:")
        for f in results["drift"]:
            print(f"  [DRIFT] {f}")
        for f in results["missing_in_webapp"]:
            print(f"  [MISSING] {f} (not in webapp)")
        print()
        print("Run: python scripts/validators/cross_project_schema.py --sync")
    else:
        print(f"Cross-project schemas in sync: {len(results['ok'])} files verified")

    if results["orphaned_in_webapp"]:
        print("\nWarnings:")
        for f in results["orphaned_in_webapp"]:
            print(f"  [ORPHANED] {f} (not in DB - renamed/deleted?)")

    true_webapp_only = set(results["webapp_only"]) - set(results["orphaned_in_webapp"])
    if true_webapp_only:
        names = ", ".join(sorted(true_webapp_only))
        print(f"\nWebapp-only schemas (auto-detected): {names}")


def check_sync(verbose: bool = True) -> Tuple[bool, Dict]:
    """
    Check if schemas are in sync between projects.

    Returns (success, details_dict)
    """
    if not WEBAPP_SCHEMA_DIR.exists():
        if verbose:
            print(f"Warning: Webapp schema dir not found at {WEBAPP_SCHEMA_DIR}")
            print("Skipping cross-project validation (webapp not present)")
        return True, {"skipped": True, "reason": "webapp not found"}

    db_files = get_schema_files(DB_SCHEMA_DIR)
    results = _compare_schemas(db_files)
    has_issues = bool(results["drift"] or results["missing_in_webapp"])

    if verbose:
        _print_check_results(results)

    return not has_issues, results


def _sync_file(filename: str, verbose: bool) -> bool:
    """Sync a single file from DB to webapp. Returns True if synced."""
    db_file = DB_SCHEMA_DIR / filename
    webapp_file = WEBAPP_SCHEMA_DIR / filename

    if not db_file.exists():
        return False

    db_hash = compute_file_hash(db_file)
    webapp_hash = compute_file_hash(webapp_file)

    if db_hash != webapp_hash:
        webapp_file.write_text(db_file.read_text())
        if verbose:
            print(f"  [SYNCED] {filename}")
        return True
    if verbose:
        print(f"  [OK] {filename}")
    return False


def sync_schemas(verbose: bool = True) -> bool:
    """
    Sync schema files from DB project to webapp.

    Returns True if sync was successful.
    """
    if not WEBAPP_SCHEMA_DIR.exists():
        print(f"Error: Webapp schema dir not found at {WEBAPP_SCHEMA_DIR}")
        return False

    db_files = get_schema_files(DB_SCHEMA_DIR)
    synced = sum(1 for f in sorted(db_files) if _sync_file(f, verbose))

    orphaned = get_orphaned_files()
    if orphaned:
        print("\nOrphaned files detected (manual cleanup needed):")
        for f in sorted(orphaned):
            print(f"  [ORPHANED] {f} - delete from webapp if no longer needed")

    rebuild_webapp_index()

    if verbose:
        if synced > 0:
            print(f"\nSynced {synced} file(s)")
            print("\nNext: cd ../cost-management && pnpm run db:push")
        else:
            print("\nAll files already in sync")

    return True


def rebuild_webapp_index():
    """
    Rebuild webapp schema index.ts.

    FULLY DYNAMIC - discovers all schema files in webapp directory
    and exports them. No hardcoding needed.
    """
    index_file = WEBAPP_SCHEMA_DIR / "index.ts"

    # Get all schema files actually present in webapp (excluding index.ts)
    all_schemas = sorted(
        [f.stem for f in WEBAPP_SCHEMA_DIR.glob("*.ts") if f.name != "index.ts"]
    )

    # Separate _schema (must be first) from others
    other_schemas = [s for s in all_schemas if s != "_schema"]

    # Detect webapp-only for comment grouping
    db_files = get_schema_files(DB_SCHEMA_DIR)
    db_stems = {f.replace(".ts", "") for f in db_files}

    data_schemas = [s for s in other_schemas if f"{s}.ts" in db_files or s in db_stems]
    webapp_schemas = [
        s for s in other_schemas if s not in data_schemas and s != "_schema"
    ]

    # Build index content
    lines = [
        "/**",
        " * Database schema definitions for dev_v3 schema",
        " *",
        " * Auto-generated by cross_project_schema.py",
        " * Data schemas synced from cost-management-db",
        " */",
        "",
        "export * from './_schema';",
        "",
        "// Data schemas (owned by cost-management-db)",
    ]

    for schema in data_schemas:
        lines.append(f"export * from './{schema}';")

    if webapp_schemas:
        lines.extend(
            [
                "",
                "// Webapp-only schemas (owned by this project)",
            ]
        )
        for schema in webapp_schemas:
            lines.append(f"export * from './{schema}';")

    lines.append("")
    index_file.write_text("\n".join(lines))


def show_diff(verbose: bool = True) -> None:
    """Show detailed diff between schema files."""
    import difflib

    if not WEBAPP_SCHEMA_DIR.exists():
        print("Webapp schema dir not found")
        return

    db_files = get_schema_files(DB_SCHEMA_DIR)

    for filename in sorted(db_files):
        db_file = DB_SCHEMA_DIR / filename
        webapp_file = WEBAPP_SCHEMA_DIR / filename

        if not db_file.exists() or not webapp_file.exists():
            if not webapp_file.exists():
                print(f"\n=== {filename} ===")
                print("[MISSING in webapp]")
            continue

        db_content = db_file.read_text().splitlines(keepends=True)
        webapp_content = webapp_file.read_text().splitlines(keepends=True)

        diff = list(
            difflib.unified_diff(
                webapp_content,
                db_content,
                fromfile=f"webapp/{filename}",
                tofile=f"db/{filename}",
            )
        )

        if diff:
            print(f"\n=== {filename} ===")
            print("".join(diff))


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Cross-Project Schema Validator")
    parser.add_argument(
        "--check", action="store_true", help="Check if schemas are in sync"
    )
    parser.add_argument("--sync", action="store_true", help="Sync schemas to webapp")
    parser.add_argument("--diff", action="store_true", help="Show detailed differences")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output")

    args = parser.parse_args()
    verbose = not args.quiet

    if args.sync:
        success = sync_schemas(verbose)
        sys.exit(0 if success else 1)
    elif args.diff:
        show_diff(verbose)
        sys.exit(0)
    else:
        # Default: check
        success, _ = check_sync(verbose)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
