#!/usr/bin/env python3
"""
Stage 3: Prepare GRIR Exposures for Import

Maps intermediate GRIR columns to database schema columns.

Dependencies: stage2_transform/06_calculate_grir.py must run first
Input: data/intermediate/grir_exposures.csv
Output: data/import-ready/grir_exposures.csv
"""

import sys
from pathlib import Path

# Add scripts directory to path for config imports
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import pandas as pd
from config.column_mappings import GRIR_EXPOSURES_MAPPING, REQUIRED_COLUMNS

# Paths
PROJECT_ROOT = SCRIPTS_DIR.parent
INPUT_FILE = PROJECT_ROOT / "data" / "intermediate" / "grir_exposures.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "import-ready" / "grir_exposures.csv"


def load_data(filepath: Path) -> pd.DataFrame:
    """Load GRIR exposures data."""
    print(f"Loading data from: {filepath}")
    df = pd.read_csv(filepath)
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
    return df


def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map CSV columns to database column names."""
    print("Mapping columns to database schema...")
    
    output_df = pd.DataFrame()
    
    # Map columns using the mapping dictionary
    for csv_col, db_col in GRIR_EXPOSURES_MAPPING.items():
        if csv_col in df.columns:
            output_df[db_col] = df[csv_col]
            print(f"  {csv_col} -> {db_col}")
        else:
            print(f"  WARNING: Column '{csv_col}' not found in source data")
    
    # Round numeric columns
    if "grir_qty" in output_df.columns:
        output_df["grir_qty"] = output_df["grir_qty"].round(4)
    
    if "grir_value" in output_df.columns:
        output_df["grir_value"] = output_df["grir_value"].round(2)
    
    return output_df


def validate_output(df: pd.DataFrame) -> bool:
    """Validate required columns are present."""
    print("Validating output...")
    
    required = REQUIRED_COLUMNS.get("grir_exposures", [])
    missing = [col for col in required if col not in df.columns]
    
    if missing:
        print(f"  ERROR: Missing required columns: {missing}")
        return False
    
    # Check for nulls in required columns
    for col in required:
        null_count = df[col].isna().sum()
        if null_count > 0:
            print(f"  WARNING: Column '{col}' has {null_count:,} null values")
    
    print(f"  All {len(required)} required columns present")
    return True


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save import-ready DataFrame to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"  Saved to: {filepath}")
    print(f"  Final row count: {len(df):,}")
    
    # Summary stats
    if len(df) > 0 and "grir_value" in df.columns:
        print(f"  Total GRIR Value: ${df['grir_value'].sum():,.2f}")
        
        if "time_bucket" in df.columns:
            print(f"\n  Time bucket summary:")
            for bucket in ["<1 month", "1-3 months", "3-6 months", "6-12 months", ">1 year"]:
                bucket_df = df[df["time_bucket"] == bucket]
                if len(bucket_df) > 0:
                    print(f"    {bucket}: {len(bucket_df):,} POs (${bucket_df['grir_value'].sum():,.2f})")


def main():
    print("=" * 60)
    print("Stage 3: Prepare GRIR Exposures for Import")
    print("=" * 60)
    
    # Check dependency
    if not INPUT_FILE.exists():
        print(f"ERROR: Dependency not found: {INPUT_FILE}")
        print("Run 06_calculate_grir.py first")
        return False
    
    print("\n[1/4] Loading data...")
    df = load_data(INPUT_FILE)
    
    if len(df) == 0:
        print("\n  No GRIR exposures found - creating empty output file")
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(columns=list(GRIR_EXPOSURES_MAPPING.values())).to_csv(OUTPUT_FILE, index=False)
        print(f"  Saved empty file to: {OUTPUT_FILE}")
        return True
    
    print("\n[2/4] Mapping columns...")
    output_df = map_columns(df)
    
    print("\n[3/4] Validating output...")
    if not validate_output(output_df):
        return False
    
    print("\n[4/4] Saving import-ready file...")
    save_data(output_df, OUTPUT_FILE)
    
    print("\n" + "=" * 60)
    print("Stage 3 Complete: GRIR Exposures ready for import")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
