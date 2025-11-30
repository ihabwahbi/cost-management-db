#!/usr/bin/env python3
"""
Context Oracle Master Generator

Generates all Context Oracle artifacts in the correct order:
  1. Pipeline Map (existing) - Script metadata, column mappings
  2. Symbol Registry - Functions, constants, columns, tables
  3. Code Skeletons - Compressed code views (3x+ compression)
  4. Pattern Library - Code patterns and conventions
  5. Lineage Graph - Data flow and impact prediction

Fix 4: Supports incremental updates - only regenerates for changed files.

Output: pipeline-context/

Usage:
    python3 scripts/generate_context_oracle.py
    python3 scripts/generate_context_oracle.py --skip-pipeline-map  # If already up to date
    python3 scripts/generate_context_oracle.py --incremental        # Only regenerate changed
    python3 scripts/generate_context_oracle.py --force              # Force full regeneration
"""

import sys
import argparse
import time
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Set, Optional

SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent
PIPELINE_CONTEXT_DIR = PROJECT_ROOT / "pipeline-context"
MANIFEST_FILE = PIPELINE_CONTEXT_DIR / ".manifest.json"

# Add scripts directory to path for imports
sys.path.insert(0, str(SCRIPTS_DIR))


# =============================================================================
# Fix 4: Incremental Update Support
# =============================================================================

def compute_file_hash(filepath: Path) -> str:
    """Compute MD5 hash of a file for change detection."""
    if not filepath.exists():
        return ""
    content = filepath.read_bytes()
    return hashlib.md5(content).hexdigest()


def smart_write_json(filepath: Path, data: Dict, exclude_keys: Optional[list] = None) -> bool:
    """
    Write JSON file only if content actually changed (excluding specified keys).
    
    This prevents unnecessary git changes from timestamp-only differences.
    Returns True if file was written, False if unchanged.
    """
    if exclude_keys is None:
        exclude_keys = ["generated_at", "last_generated"]
    
    def strip_excluded(obj):
        """Recursively remove excluded keys from dict."""
        if isinstance(obj, dict):
            return {k: strip_excluded(v) for k, v in obj.items() if k not in exclude_keys}
        elif isinstance(obj, list):
            return [strip_excluded(item) for item in obj]
        return obj
    
    new_content = strip_excluded(data)
    
    # Check if file exists and compare content
    if filepath.exists():
        try:
            with open(filepath) as f:
                existing = json.load(f)
            existing_content = strip_excluded(existing)
            
            # Compare without timestamps
            if json.dumps(new_content, sort_keys=True) == json.dumps(existing_content, sort_keys=True):
                return False  # No change needed
        except (json.JSONDecodeError, IOError):
            pass  # File corrupted or unreadable, write new
    
    # Write the file (with timestamps intact)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    return True


def get_source_files() -> Dict[str, Path]:
    """Get all source files that affect Oracle generation."""
    source_files = {}
    
    # Pipeline scripts
    for stage_dir in ["stage1_clean", "stage2_transform", "stage3_prepare", "config"]:
        stage_path = SCRIPTS_DIR / stage_dir
        if stage_path.exists():
            for py_file in stage_path.glob("*.py"):
                key = str(py_file.relative_to(PROJECT_ROOT))
                source_files[key] = py_file
    
    # Schema files
    schema_dir = PROJECT_ROOT / "src" / "schema"
    if schema_dir.exists():
        for ts_file in schema_dir.glob("*.ts"):
            key = str(ts_file.relative_to(PROJECT_ROOT))
            source_files[key] = ts_file
    
    # Generator scripts themselves
    for gen_script in SCRIPTS_DIR.glob("*.py"):
        if gen_script.name.startswith(("generate_", "build_", "extract_")):
            key = str(gen_script.relative_to(PROJECT_ROOT))
            source_files[key] = gen_script
    
    return source_files


def load_manifest() -> Dict:
    """Load the existing manifest of file hashes."""
    if not MANIFEST_FILE.exists():
        return {"files": {}, "last_generated": None}
    
    try:
        with open(MANIFEST_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"files": {}, "last_generated": None}


def get_latest_source_mtime() -> datetime:
    """Get the latest modification time of all source files.
    
    This makes the generated timestamp deterministic - it only changes
    when source files actually change, preventing infinite loops in
    pre-commit hooks.
    """
    latest_mtime = 0.0
    
    source_files = get_source_files()
    for path in source_files.values():
        if path.exists():
            mtime = path.stat().st_mtime
            if mtime > latest_mtime:
                latest_mtime = mtime
    
    return datetime.fromtimestamp(latest_mtime, tz=timezone.utc)


def save_manifest(manifest: Dict) -> None:
    """Save the manifest of file hashes.
    
    Uses deterministic timestamp based on source file mtimes to prevent
    pre-commit hook loops.
    """
    PIPELINE_CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    # Use deterministic timestamp based on source file mtimes
    manifest["last_generated"] = get_latest_source_mtime().isoformat()
    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, indent=2)


def detect_changes() -> Dict:
    """
    Detect which files have changed since last generation.
    
    Returns dict with:
      - changed: Set of changed file paths
      - added: Set of new file paths  
      - removed: Set of removed file paths
      - current_hashes: Dict of current file hashes
    """
    manifest = load_manifest()
    old_hashes = manifest.get("files", {})
    
    source_files = get_source_files()
    current_hashes = {key: compute_file_hash(path) for key, path in source_files.items()}
    
    changed: Set[str] = set()
    added: Set[str] = set()
    removed: Set[str] = set()
    
    # Find changed and added files
    for key, new_hash in current_hashes.items():
        old_hash = old_hashes.get(key)
        if old_hash is None:
            added.add(key)
        elif old_hash != new_hash:
            changed.add(key)
    
    # Find removed files
    for key in old_hashes:
        if key not in current_hashes:
            removed.add(key)
    
    return {
        "changed": changed,
        "added": added,
        "removed": removed,
        "current_hashes": current_hashes
    }


def needs_regeneration(changes: Dict[str, Set[str]]) -> bool:
    """Check if any regeneration is needed."""
    return bool(changes["changed"] or changes["added"] or changes["removed"])


def run_generator(name: str, generator_func, *args, **kwargs):
    """Run a generator function with timing and error handling."""
    print(f"\n{'='*60}")
    print(f"STEP: {name}")
    print(f"{'='*60}")
    
    start = time.time()
    try:
        result = generator_func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"\nCompleted {name} in {elapsed:.2f}s")
        return result
    except Exception as e:
        elapsed = time.time() - start
        print(f"\nFailed {name} after {elapsed:.2f}s: {e}")
        raise


def generate_all(skip_pipeline_map: bool = False, incremental: bool = False, force: bool = False):
    """
    Generate all Context Oracle artifacts.
    
    Args:
        skip_pipeline_map: Skip pipeline map generation
        incremental: Only regenerate if files changed (Fix 4)
        force: Force full regeneration even if no changes
    """
    # Fix 4: Check for changes in incremental mode
    if incremental and not force:
        changes = detect_changes()
        if not needs_regeneration(changes):
            print("No changes detected. Oracle artifacts are up to date.")
            return
        
        total_changed = len(changes["changed"]) + len(changes["added"])
        print(f"\n[Incremental Mode] Detected {total_changed} changed files:")
        for f in sorted(changes["changed"] | changes["added"])[:10]:
            print(f"  - {f}")
        if total_changed > 10:
            print(f"  ... and {total_changed - 10} more")
        print()
    else:
        changes = None
    
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║             CONTEXT ORACLE - MASTER GENERATOR                ║
    ║                                                               ║
    ║  Building the Intelligence Layer for AI Coding Agents        ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    start_time = time.time()
    
    # Step 1: Pipeline Map (foundation for everything else)
    if not skip_pipeline_map:
        from generate_pipeline_map import generate_pipeline_map
        run_generator("Pipeline Map", generate_pipeline_map)
    else:
        print("\n[Skipping Pipeline Map - using existing]")
    
    # Step 2: Symbol Registry
    from build_symbol_registry import generate_symbol_registry
    run_generator("Symbol Registry", generate_symbol_registry)
    
    # Step 3: Code Skeletons
    from generate_skeletons import generate_all_skeletons
    run_generator("Code Skeletons", generate_all_skeletons)
    
    # Step 4: Pattern Library
    from extract_patterns import build_pattern_library
    run_generator("Pattern Library", build_pattern_library)
    
    # Step 5: Lineage Graph
    from build_lineage_graph import build_lineage_graph
    run_generator("Lineage Graph", build_lineage_graph)
    
    # Fix 4: Update manifest with current file hashes
    if changes:
        manifest = {"files": changes["current_hashes"]}
    else:
        # Full regeneration - compute all hashes
        source_files = get_source_files()
        manifest = {"files": {key: compute_file_hash(path) for key, path in source_files.items()}}
    save_manifest(manifest)
    
    # Summary
    total_time = time.time() - start_time
    deterministic_timestamp = get_latest_source_mtime().isoformat()
    
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║               CONTEXT ORACLE - COMPLETE                      ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    print(f"Total time: {total_time:.2f}s")
    print(f"Generated at: {deterministic_timestamp}")
    print()
    print("Generated artifacts in pipeline-context/:")
    print("  registry/symbols.json     - Symbol Registry (functions, columns)")
    print("  skeletons/                - Code Skeletons (3.3x compression)")
    print("  patterns/index.json       - Pattern Library (patterns)")
    print("  lineage/graph.json        - Lineage Graph (with variable tracing)")
    print()
    print("The Three Pillars of the Context Oracle:")
    print("  1. Symbol Registry  → Verify before use (anti-hallucination)")
    print("  2. Pattern Library  → Follow conventions (anti-drift)")
    print("  3. Lineage Oracle   → Know impact (guided search)")
    print()
    if incremental:
        print("Fix 4: Manifest saved for incremental updates.")
    

def main():
    parser = argparse.ArgumentParser(
        description="Generate all Context Oracle artifacts"
    )
    parser.add_argument(
        "--skip-pipeline-map",
        action="store_true",
        help="Skip pipeline map generation (use existing)"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Fix 4: Only regenerate if source files changed"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force full regeneration even if no changes detected"
    )
    
    args = parser.parse_args()
    generate_all(
        skip_pipeline_map=args.skip_pipeline_map,
        incremental=args.incremental,
        force=args.force
    )


if __name__ == "__main__":
    main()
