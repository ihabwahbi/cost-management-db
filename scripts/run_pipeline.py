"""
Run Full Data Processing Pipeline

This script executes all numbered pipeline scripts in order:
  01_clean_gr_data.py
  02_build_po_lookup.py
  03_prepare_po_transactions.py

Usage:
  python scripts/run_pipeline.py
"""

import subprocess
import sys
import os
from datetime import datetime

# Get the scripts directory
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Pipeline scripts in execution order
PIPELINE_SCRIPTS = [
    '01_clean_gr_data.py',
    '02_build_po_lookup.py',
    '03_prepare_po_transactions.py',
]


def run_script(script_name):
    """Run a single pipeline script."""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    
    print(f"\n{'#' * 70}")
    print(f"# RUNNING: {script_name}")
    print(f"{'#' * 70}\n")
    
    result = subprocess.run(
        [sys.executable, script_path],
        cwd=os.path.dirname(SCRIPTS_DIR),  # Run from project root
        capture_output=False,  # Show output in real-time
    )
    
    if result.returncode != 0:
        print(f"\nERROR: {script_name} failed with exit code {result.returncode}")
        return False
    
    return True


def main():
    """Run the full pipeline."""
    start_time = datetime.now()
    
    print("=" * 70)
    print("DATA PROCESSING PIPELINE")
    print("=" * 70)
    print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Scripts to run: {len(PIPELINE_SCRIPTS)}")
    
    # Run each script in order
    for script_name in PIPELINE_SCRIPTS:
        success = run_script(script_name)
        if not success:
            print("\nPIPELINE FAILED - stopping execution")
            sys.exit(1)
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print(f"Finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total duration: {duration:.1f} seconds")
    print("\nOutput files:")
    print("  - data/intermediate/gr_cleaned.csv")
    print("  - data/intermediate/po_cost_recognition_lookup.csv")
    print("  - data/import_ready/po_transactions.csv")
    print("=" * 70)


if __name__ == '__main__':
    main()
