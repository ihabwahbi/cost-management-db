#!/usr/bin/env python3
"""
Data Pipeline Orchestrator

Runs all data transformation scripts in the correct order to produce
import-ready CSV files from raw data.

Usage:
    python3 scripts/pipeline.py           # Run full pipeline
    python3 scripts/pipeline.py --stage1  # Run only stage 1
    python3 scripts/pipeline.py --stage2  # Run stages 1-2
    python3 scripts/pipeline.py --stage3  # Run all stages (same as full)

Pipeline Stages:
    Stage 1 (Clean):     Raw data → Intermediate (cleaned)
    Stage 2 (Transform): Intermediate → Intermediate (enriched + cost impact)
    Stage 3 (Prepare):   Intermediate → Import-ready (DB schema mapped)

Output:
    data/import-ready/po_line_items.csv   → po_line_items table
    data/import-ready/po_transactions.csv → po_transactions table
    data/import-ready/grir_exposures.csv  → grir_exposures table
"""

import subprocess
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Paths
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent

# Pipeline definition: (script_path, description)
STAGE1_SCRIPTS = [
    ("stage1_clean/01_po_line_items.py", "Clean PO Line Items"),
    ("stage1_clean/02_gr_postings.py", "Clean GR Postings"),
    ("stage1_clean/03_ir_postings.py", "Clean IR Postings"),
]

STAGE2_SCRIPTS = [
    ("stage2_transform/04_enrich_po_line_items.py", "Enrich PO Line Items"),
    ("stage2_transform/05_calculate_cost_impact.py", "Calculate Cost Impact"),
    ("stage2_transform/06_calculate_grir.py", "Calculate GRIR Exposures"),
]

STAGE3_SCRIPTS = [
    ("stage3_prepare/06_prepare_po_line_items.py", "Prepare PO Line Items for Import"),
    ("stage3_prepare/07_prepare_po_transactions.py", "Prepare PO Transactions for Import"),
    ("stage3_prepare/08_prepare_grir_exposures.py", "Prepare GRIR Exposures for Import"),
]


def run_script(script_path: Path, description: str) -> bool:
    """Run a Python script and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Script:  {script_path}")
    print("="*60)
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=PROJECT_ROOT,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Script failed with exit code {e.returncode}")
        return False


def run_stage(stage_name: str, scripts: list) -> bool:
    """Run all scripts in a stage."""
    print(f"\n{'#'*60}")
    print(f"# {stage_name}")
    print(f"{'#'*60}")
    
    for script_rel_path, description in scripts:
        script_path = SCRIPTS_DIR / script_rel_path
        if not script_path.exists():
            print(f"ERROR: Script not found: {script_path}")
            return False
        
        if not run_script(script_path, description):
            return False
    
    return True


def run_pipeline(max_stage: int = 3) -> bool:
    """Run the pipeline up to the specified stage."""
    start_time = datetime.now()
    
    print("\n" + "="*60)
    print(" DATA PIPELINE")
    print(" Started at:", start_time.strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)
    
    stages = [
        ("STAGE 1: CLEAN", STAGE1_SCRIPTS),
        ("STAGE 2: TRANSFORM", STAGE2_SCRIPTS),
        ("STAGE 3: PREPARE", STAGE3_SCRIPTS),
    ]
    
    for i, (stage_name, scripts) in enumerate(stages, 1):
        if i > max_stage:
            break
        
        if not run_stage(stage_name, scripts):
            print(f"\n{'!'*60}")
            print(f"! PIPELINE FAILED at {stage_name}")
            print(f"{'!'*60}")
            return False
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("\n" + "="*60)
    print(" PIPELINE COMPLETE")
    print(" Finished at:", end_time.strftime("%Y-%m-%d %H:%M:%S"))
    print(f" Duration: {duration.total_seconds():.1f} seconds")
    print("="*60)
    
    # Show output files
    print("\nOutput Files:")
    import_ready = PROJECT_ROOT / "data" / "import-ready"
    if import_ready.exists():
        for f in sorted(import_ready.glob("*.csv")):
            size = f.stat().st_size / 1024
            print(f"  {f.name}: {size:.1f} KB")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Run data transformation pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 scripts/pipeline.py           # Run full pipeline
    python3 scripts/pipeline.py --stage1  # Run only stage 1 (clean)
    python3 scripts/pipeline.py --stage2  # Run stages 1-2 (clean + transform)
        """
    )
    
    parser.add_argument("--stage1", action="store_true", 
                        help="Run only stage 1 (clean)")
    parser.add_argument("--stage2", action="store_true", 
                        help="Run stages 1-2 (clean + transform)")
    parser.add_argument("--stage3", action="store_true", 
                        help="Run all stages (default)")
    
    args = parser.parse_args()
    
    if args.stage1:
        max_stage = 1
    elif args.stage2:
        max_stage = 2
    else:
        max_stage = 3
    
    success = run_pipeline(max_stage)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
