#!/usr/bin/env python3
"""
Context Oracle Master Generator

Generates all Context Oracle artifacts in the correct order:
  1. Pipeline Map (existing) - Script metadata, column mappings
  2. Symbol Registry - Functions, constants, columns, tables
  3. Code Skeletons - Compressed code views (3x+ compression)
  4. Pattern Library - Code patterns and conventions
  5. Lineage Graph - Data flow and impact prediction

Output: pipeline-context/

Usage:
    python3 scripts/generate_context_oracle.py
    python3 scripts/generate_context_oracle.py --skip-pipeline-map  # If already up to date
"""

import sys
import argparse
import time
from pathlib import Path
from datetime import datetime, timezone

SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent

# Add scripts directory to path for imports
sys.path.insert(0, str(SCRIPTS_DIR))


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


def generate_all(skip_pipeline_map: bool = False):
    """Generate all Context Oracle artifacts."""
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
    
    # Summary
    total_time = time.time() - start_time
    
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║               CONTEXT ORACLE - COMPLETE                      ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    print(f"Total time: {total_time:.2f}s")
    print(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    print()
    print("Generated artifacts in pipeline-context/:")
    print("  registry/symbols.json     - Symbol Registry (46 functions, 88 columns)")
    print("  skeletons/                - Code Skeletons (3.3x compression)")
    print("  patterns/index.json       - Pattern Library (4 patterns)")
    print("  lineage/graph.json        - Lineage Graph (193 nodes, 68 edges)")
    print()
    print("The Three Pillars of the Context Oracle:")
    print("  1. Symbol Registry  → Verify before use (anti-hallucination)")
    print("  2. Pattern Library  → Follow conventions (anti-drift)")
    print("  3. Lineage Oracle   → Know impact (guided search)")
    

def main():
    parser = argparse.ArgumentParser(
        description="Generate all Context Oracle artifacts"
    )
    parser.add_argument(
        "--skip-pipeline-map",
        action="store_true",
        help="Skip pipeline map generation (use existing)"
    )
    
    args = parser.parse_args()
    generate_all(skip_pipeline_map=args.skip_pipeline_map)


if __name__ == "__main__":
    main()
