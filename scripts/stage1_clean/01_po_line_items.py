#!/usr/bin/env python3
"""
Stage 1: Clean PO Line Items

Reads raw PO line items CSV, applies filtering and transformations,
outputs to intermediate folder.

Dependencies: None (first script in pipeline)
Input: data/raw/po line items.csv
Output: data/intermediate/po_line_items.csv
"""

import sys
from pathlib import Path

# Add scripts directory to path for config imports
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import pandas as pd
from config.column_mappings import (
    EXCLUDED_VALUATION_CLASSES,
    EXCLUDED_NIS_LEVELS,
    VENDOR_NAME_MAPPING,
    PLANT_CODE_TO_LOCATION,
)

# Paths
PROJECT_ROOT = SCRIPTS_DIR.parent
INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "po line items.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "intermediate" / "po_line_items.csv"


def load_data(filepath: Path) -> pd.DataFrame:
    """Load the raw CSV file."""
    print(f"Loading data from: {filepath}")
    df = pd.read_csv(filepath)
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
    return df


def filter_valuation_classes(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with excluded PO Valuation Classes."""
    initial_count = len(df)
    valuation_class = pd.to_numeric(df["PO Valuation Class"], errors="coerce")
    mask = ~valuation_class.isin(EXCLUDED_VALUATION_CLASSES)
    df_filtered = df[mask].copy()
    removed_count = initial_count - len(df_filtered)
    print(f"  Removed {removed_count:,} rows with Valuation Classes {EXCLUDED_VALUATION_CLASSES}")
    return df_filtered


def filter_nis_levels(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with excluded NIS Level 0 Desc values."""
    initial_count = len(df)
    mask = ~df["NIS Level 0 Desc"].isin(EXCLUDED_NIS_LEVELS)
    df_filtered = df[mask].copy()
    removed_count = initial_count - len(df_filtered)
    print(f"  Removed {removed_count:,} rows with excluded NIS Levels")
    return df_filtered


def fill_nis_level_for_3021(df: pd.DataFrame) -> pd.DataFrame:
    """Set NIS Level 0 Desc to 'Materials and Supplies' for Valuation Class 3021 where null."""
    valuation_class = pd.to_numeric(df["PO Valuation Class"], errors="coerce")
    mask = (valuation_class == 3021) & (df["NIS Level 0 Desc"].isna() | (df["NIS Level 0 Desc"] == ""))
    updated_count = mask.sum()
    df.loc[mask, "NIS Level 0 Desc"] = "Materials and Supplies"
    print(f"  Set NIS Level for {updated_count:,} rows (Valuation Class 3021)")
    return df


def transform_nis_column(df: pd.DataFrame) -> pd.DataFrame:
    """Rename NIS Level 0 Desc to NIS Line and clean up values."""
    # Replace "Lease and Rent Total" with "Lease and Rent"
    mask = df["NIS Level 0 Desc"] == "Lease and Rent Total"
    df.loc[mask, "NIS Level 0 Desc"] = "Lease and Rent"
    print(f"  Normalized 'Lease and Rent Total' → 'Lease and Rent': {mask.sum():,} rows")
    
    # Rename column
    df = df.rename(columns={"NIS Level 0 Desc": "NIS Line"})
    return df


def map_vendor_names(df: pd.DataFrame) -> pd.DataFrame:
    """Map Main Vendor Name and Ultimate Vendor Name based on vendor IDs."""
    # Map Main Vendor Name
    main_mask = df["Main Vendor ID"].isin(VENDOR_NAME_MAPPING.keys())
    df.loc[main_mask, "Main Vendor Name"] = df.loc[main_mask, "Main Vendor ID"].map(VENDOR_NAME_MAPPING)
    print(f"  Mapped {main_mask.sum():,} Main Vendor Names")
    
    # Map Ultimate Vendor Name
    ultimate_mask = df["Ultimate Vendor Number"].isin(VENDOR_NAME_MAPPING.keys())
    df.loc[ultimate_mask, "Ultimate Vendor Name"] = df.loc[ultimate_mask, "Ultimate Vendor Number"].map(VENDOR_NAME_MAPPING)
    print(f"  Mapped {ultimate_mask.sum():,} Ultimate Vendor Names")
    
    return df


def map_location(df: pd.DataFrame) -> pd.DataFrame:
    """Map Plant Code to Location."""
    plant_code_str = df["Plant Code"].astype(str)
    df["Location"] = plant_code_str.map(PLANT_CODE_TO_LOCATION)
    mapped_count = df["Location"].notna().sum()
    print(f"  Created Location column: {mapped_count:,} mapped")
    return df


def consolidate_delivery_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Consolidate delivery date columns into 'Expected Delivery Date'."""
    requested_col = "PO Current Supplier Requested Delivery Date"
    promised_col = "PO Current Supplier Promised Date"
    
    df["Expected Delivery Date"] = df[promised_col].where(
        df[promised_col].notna() & (df[promised_col] != ""), 
        df[requested_col]
    )
    
    # Remove original columns
    df = df.drop(columns=[requested_col, promised_col])
    print(f"  Created 'Expected Delivery Date' column")
    return df


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save the cleaned DataFrame to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"  Saved to: {filepath}")
    print(f"  Final row count: {len(df):,}")


def main():
    print("=" * 60)
    print("Stage 1: Clean PO Line Items")
    print("=" * 60)
    
    print("\n[1/8] Loading data...")
    df = load_data(INPUT_FILE)
    
    print("\n[2/8] Filtering valuation classes...")
    df = filter_valuation_classes(df)
    
    print("\n[3/8] Filtering NIS levels...")
    df = filter_nis_levels(df)
    
    print("\n[4/8] Filling NIS for Valuation Class 3021...")
    df = fill_nis_level_for_3021(df)
    
    print("\n[5/8] Transforming NIS column...")
    df = transform_nis_column(df)
    
    print("\n[6/8] Mapping vendor names...")
    df = map_vendor_names(df)
    
    print("\n[7/8] Mapping locations...")
    df = map_location(df)
    
    print("\n[8/8] Consolidating delivery dates...")
    df = consolidate_delivery_dates(df)
    
    print("\n[Save] Writing output...")
    save_data(df, OUTPUT_FILE)
    
    print("\n" + "=" * 60)
    print("Stage 1 Complete: PO Line Items cleaned")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
