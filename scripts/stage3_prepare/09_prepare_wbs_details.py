#!/usr/bin/env python3
"""
Stage 3: Prepare WBS Details for Import

Maps intermediate columns to database schema columns and handles
duplicate WBS entries (same WBS from different sources).

Duplicate handling strategy:
- wbs_number is the primary key (globally unique across all FDP reports)
- If duplicates found (shouldn't happen), keep first occurrence

Array column handling:
- sub_business_lines: JSON array in CSV -> PostgreSQL text[] literal format
- Example: '["WLPS", "SLKN"]' -> '{WLPS,SLKN}'

Dependencies: scripts/stage2_transform/07_process_wbs.py
Input: data/intermediate/wbs_processed.csv
Output: data/import-ready/wbs_details.csv
"""

import sys
import json
from pathlib import Path

# Add scripts directory to path for config imports
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import pandas as pd
from config.column_mappings import WBS_DETAILS_MAPPING

# Paths
PROJECT_ROOT = SCRIPTS_DIR.parent
INPUT_FILE = PROJECT_ROOT / "data" / "intermediate" / "wbs_processed.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "import-ready" / "wbs_details.csv"


def load_data() -> pd.DataFrame:
    """Load intermediate WBS data."""
    print("Loading intermediate data...")
    df = pd.read_csv(INPUT_FILE)
    print(f"  WBS Details: {len(df):,} rows")
    return df


def json_to_pg_array(json_str: str) -> str:
    """
    Convert JSON array string to PostgreSQL text[] literal format.
    
    Examples:
    - '["WLPS"]' -> '{WLPS}'
    - '["WLPS", "SLKN", "WLES"]' -> '{WLPS,SLKN,WLES}'
    - None/NaN -> None
    """
    if pd.isna(json_str) or not json_str:
        return None
    
    try:
        arr = json.loads(json_str)
        if not arr or not isinstance(arr, list):
            return None
        # PostgreSQL array literal format: {val1,val2,val3}
        return "{" + ",".join(str(v) for v in arr if v) + "}"
    except (json.JSONDecodeError, TypeError):
        return None


def handle_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle duplicate WBS entries.
    
    Since wbs_number is the primary key (globally unique across all FDP reports),
    we check for any duplicates and fail if found.
    """
    print("Handling duplicates...")
    initial_count = len(df)
    
    # Check for duplicate wbs_number (should not exist based on data analysis)
    dup_mask = df.duplicated(subset=["wbs_number"], keep="first")
    dup_count = dup_mask.sum()
    
    if dup_count > 0:
        print(f"  WARNING: Found {dup_count:,} duplicate wbs_number values")
        print("  Keeping first occurrence of each duplicate")
        df = df[~dup_mask].copy()
    else:
        print("  No duplicates found (wbs_number is unique)")
    
    print(f"  Final count: {len(df):,} rows (removed {initial_count - len(df):,})")
    return df


def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map intermediate columns to database column names."""
    print("Mapping columns to database schema...")
    
    # Build the output dataframe with mapped columns
    output_df = pd.DataFrame()
    
    for csv_col, db_col in WBS_DETAILS_MAPPING.items():
        if csv_col in df.columns:
            output_df[db_col] = df[csv_col]
        else:
            print(f"  Warning: Column '{csv_col}' not found in source data")
            output_df[db_col] = None
    
    # Convert sub_business_lines from JSON to PostgreSQL array literal format
    if "sub_business_lines" in output_df.columns:
        original_filled = output_df["sub_business_lines"].notna().sum()
        output_df["sub_business_lines"] = output_df["sub_business_lines"].apply(json_to_pg_array)
        converted_filled = output_df["sub_business_lines"].notna().sum()
        print(f"  Converted sub_business_lines: {original_filled:,} -> {converted_filled:,} (JSON -> PG array)")
    
    print(f"  Mapped {len(output_df.columns)} columns")
    return output_df


def validate_output(df: pd.DataFrame) -> bool:
    """Validate required columns are present and data is valid."""
    print("Validating output...")
    
    required = ["wbs_number", "wbs_source"]
    missing = [col for col in required if col not in df.columns]
    
    if missing:
        print(f"  ERROR: Missing required columns: {missing}")
        return False
    
    # Check for nulls in required columns
    for col in required:
        null_count = df[col].isna().sum()
        if null_count > 0:
            print(f"  ERROR: {null_count:,} nulls in required column '{col}'")
            return False
    
    # Verify no duplicate wbs_number (since wbs_number is now the primary key)
    dup_mask = df.duplicated(subset=["wbs_number"], keep=False)
    if dup_mask.any():
        dup_count = dup_mask.sum()
        print(f"  ERROR: {dup_count:,} duplicate wbs_number values remain")
        dup_wbs = df.loc[dup_mask, "wbs_number"].unique()
        print(f"  Sample duplicates: {list(dup_wbs[:5])}")
        return False
    
    # Validate WBS number format
    valid_format = df["wbs_number"].str.match(r'^J\.\d{2}\.\d{6}$', na=False)
    invalid_count = (~valid_format).sum()
    if invalid_count > 0:
        print(f"  Warning: {invalid_count:,} rows with non-standard WBS format")
    
    print("  Validation passed")
    return True


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save import-ready DataFrame to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"  Saved to: {filepath}")
    print(f"  Final row count: {len(df):,}")
    print(f"  Columns: {len(df.columns)}")


def main():
    print("=" * 60)
    print("Stage 3: Prepare WBS Details for Import")
    print("=" * 60)
    
    # Check dependencies
    if not INPUT_FILE.exists():
        print(f"ERROR: Dependency not found: {INPUT_FILE}")
        return False
    
    print("\n[1/4] Loading data...")
    df = load_data()
    
    print("\n[2/4] Handling duplicates...")
    df = handle_duplicates(df)
    
    print("\n[3/4] Mapping columns...")
    output_df = map_columns(df)
    
    print("\n[4/4] Validating and saving...")
    if not validate_output(output_df):
        return False
    save_data(output_df, OUTPUT_FILE)
    
    # Print summary
    print("\n" + "-" * 40)
    print("Summary by Source:")
    print(output_df["wbs_source"].value_counts().to_string())
    
    print("\n" + "=" * 60)
    print("Stage 3 Complete: WBS Details ready for import")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
