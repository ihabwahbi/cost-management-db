#!/usr/bin/env python3
"""
Stage 1: Extract WBS Data from Operation Activities Report

Reads the FDP Operation Activities dashboard export and extracts/cleans WBS-related fields.
This script maintains 1:1 row traceability with the source file.

Note: Ops Activities has single WBS per row (no comma-separated entries).
Note: Has explicit "Sub Business Line" column with full names (not bracket codes).
Note: No Plant Code column - will be enriched from Projects in Stage 2.

Caching: Extracts data from xlsx to CSV cache. Only reprocesses xlsx if:
- Source file changed (different filename, mtime, or size)
- Script code changed (including config dependencies)
- Use --force to bypass cache

Dependencies: None (reads from raw)
Input: data/raw/fdp/OperationActivityDashboard_Export_*.xlsx
Output: data/intermediate/wbs_from_ops_activities.csv
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Add scripts directory to path for config imports
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import pandas as pd
from utils.xlsx_cache import XlsxCacheManager

# Paths
PROJECT_ROOT = SCRIPTS_DIR.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "fdp"
OUTPUT_FILE = PROJECT_ROOT / "data" / "intermediate" / "wbs_from_ops_activities.csv"
SOURCE_PATTERN = "OperationActivityDashboard_Export_*.xlsx"

# Columns to keep from Operation Activities export
SOURCE_COLUMNS = [
    "Project Number",
    "Operation Number",
    "Ops Activity Number",
    "Ops Activity Name",
    "Customer",
    "Rig",
    "SAP WBS # / SO #",
    "Sub Business Line",  # Explicit column with full names
    "Ops District",
]


def find_input_file() -> Optional[Path]:
    """Find the Operation Activities dashboard export file."""
    pattern = "OperationActivityDashboard_Export_*.xlsx"
    files = list(RAW_DIR.glob(pattern))
    if not files:
        print(f"  ERROR: No files matching {pattern} in {RAW_DIR}")
        return None
    if len(files) > 1:
        print(f"  WARNING: Multiple files found, using most recent")
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return files[0]


def load_data(filepath: Path) -> pd.DataFrame:
    """Load the Excel file and select relevant columns."""
    print(f"Loading data from: {filepath.name}")
    df = pd.read_excel(filepath)
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
    
    # Keep only relevant columns
    available_cols = [c for c in SOURCE_COLUMNS if c in df.columns]
    missing_cols = set(SOURCE_COLUMNS) - set(available_cols)
    if missing_cols:
        print(f"  WARNING: Missing columns: {missing_cols}")
    
    df = df[available_cols].copy()
    print(f"  Selected {len(available_cols)} columns for WBS extraction")
    return df


def filter_rows_with_wbs(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to only rows that have WBS data."""
    initial_count = len(df)
    wbs_col = "SAP WBS # / SO #"
    
    # Keep rows where WBS column is not null/empty
    mask = df[wbs_col].notna() & (df[wbs_col].astype(str).str.strip() != "")
    df_filtered = df[mask].copy()
    
    removed_count = initial_count - len(df_filtered)
    print(f"  Removed {removed_count:,} rows without WBS data ({removed_count/initial_count*100:.1f}%)")
    print(f"  Kept {len(df_filtered):,} rows with WBS data")
    return df_filtered


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to standardized intermediate format."""
    rename_map = {
        "Project Number": "project_number",
        "Operation Number": "operation_number",
        "Ops Activity Number": "ops_activity_number",
        "Ops Activity Name": "wbs_name",
        "Customer": "client_name",
        "Rig": "rig",
        "SAP WBS # / SO #": "sap_wbs_raw",
        "Sub Business Line": "sub_business_line_raw",  # Keep for priority in Stage 2
        "Ops District": "ops_district",
    }
    
    df = df.rename(columns=rename_map)
    print(f"  Standardized {len(rename_map)} column names")
    return df


def add_source_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Add source tracking and placeholder columns."""
    df["wbs_source"] = "Operation Activity"
    
    # Location will be mapped from Ops District in Stage 2
    df["location"] = None
    
    print(f"  Added source metadata (wbs_source='Operation Activity')")
    return df


def select_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Select and order final output columns."""
    output_cols = [
        "sap_wbs_raw",
        "wbs_source",
        "project_number",
        "operation_number",
        "ops_activity_number",
        "wbs_name",
        "client_name",
        "rig",
        "ops_district",
        "location",
        "sub_business_line_raw",  # Keep explicit SBL for priority in Stage 2
    ]
    
    # Only include columns that exist
    available = [c for c in output_cols if c in df.columns]
    df = df[available]
    print(f"  Selected {len(available)} output columns")
    return df


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save the cleaned DataFrame to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"  Saved to: {filepath}")
    print(f"  Final row count: {len(df):,}")


def main(force: bool = False) -> bool:
    print("=" * 60)
    print("Stage 1: Extract WBS Data from Operation Activities Report")
    print("=" * 60)
    
    # Initialize cache manager
    cache = XlsxCacheManager(
        source_dir=RAW_DIR,
        source_pattern=SOURCE_PATTERN,
        output_file=OUTPUT_FILE,
        script_path=Path(__file__),
        extra_deps=[]
    )
    
    # Check cache validity
    print(f"\n[0/6] Checking cache...")
    if not force and cache.is_valid():
        print(f"\n  Using cached output (xlsx unchanged)")
        print(f"  {cache.get_cache_info()}")
        print("\n" + "=" * 60)
        print("Stage 1 Complete: WBS from Operation Activities (cached)")
        print("=" * 60)
        return True
    
    if force:
        print("  Cache bypassed (--force flag)")
    
    # Find input file (use cache manager's source file)
    print("\n[1/6] Finding input file...")
    input_file = cache.source_file
    if input_file is None:
        print(f"  ERROR: No files matching {SOURCE_PATTERN} in {RAW_DIR}")
        print("ERROR: Cannot proceed without input file")
        return False
    print(f"  Found: {input_file.name}")
    
    print(f"\n[2/6] Loading data...")
    df = load_data(input_file)
    
    print(f"\n[3/6] Filtering rows with WBS...")
    df = filter_rows_with_wbs(df)
    
    if len(df) == 0:
        print("WARNING: No rows with WBS data found - creating empty output")
        # Create empty dataframe with expected columns
        df = pd.DataFrame(columns=[
            "sap_wbs_raw", "wbs_source", "project_number", "operation_number",
            "ops_activity_number", "wbs_name", "client_name", "rig",
            "plant_code", "location", "sub_business_line_raw"
        ])
        save_data(df, OUTPUT_FILE)
        cache.save_metadata()
        return True
    
    print(f"\n[4/6] Standardizing column names...")
    df = standardize_columns(df)
    
    print(f"\n[5/6] Adding source metadata...")
    df = add_source_metadata(df)
    
    print(f"\n[6/6] Selecting output columns...")
    df = select_output_columns(df)
    
    print(f"\n[Save] Writing output...")
    save_data(df, OUTPUT_FILE)
    
    # Save cache metadata
    cache.save_metadata()
    
    print("\n" + "=" * 60)
    print("Stage 1 Complete: WBS from Operation Activities extracted")
    print("=" * 60)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract WBS data from Operation Activities dashboard export"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force processing even if cache is valid"
    )
    args = parser.parse_args()
    
    success = main(force=args.force)
    sys.exit(0 if success else 1)
