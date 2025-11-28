#!/usr/bin/env python3
"""
Clean PO Line Items CSV

This script processes the raw PO line items CSV file and applies
filtering, transformations, and additions as needed.
"""

import pandas as pd
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "po line items.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "po_line_items_cleaned.csv"

# Valuation classes to exclude
EXCLUDED_VALUATION_CLASSES = [7800, 7900, 5008]

# NIS Level 0 Desc values to exclude
EXCLUDED_NIS_LEVELS = [
    "Compensation Business Delivery",
    "Compensation Business Enablement",
]

# Ultimate Vendor Number -> Main Vendor Name mapping
VENDOR_NAME_MAPPING = {
    "P9516": "Dubai Hub",
    "P9109": "Houston Hub",
    "P9517": "Shanghai Hub",
    "P9518": "Singapore Hub",
    "P9514": "Canada Hub",
    "P9519": "Japan Hub",
    "P9097": "Rotterdam Hub",
    "P9107": "NAM RDC",
    "P9071": "PPCU",
    "P9052": "SRC",
    "P9057": "SKK",
    "P9060": "SRPC",
    "P9036": "HFE",
    "P9035": "HCS",
    "P9086": "ONESUBSEA",
    "P9064": "PPCS",
    "P9066": "SWTC",
    "P9562": "QRTC",
}


def load_data(filepath: Path) -> pd.DataFrame:
    """Load the raw CSV file."""
    print(f"Loading data from: {filepath}")
    df = pd.read_csv(filepath)
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
    return df


def filter_valuation_classes(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with excluded PO Valuation Classes."""
    initial_count = len(df)
    
    # Convert to numeric for comparison (handles empty strings)
    valuation_class = pd.to_numeric(df["PO Valuation Class"], errors="coerce")
    
    # Keep rows NOT in excluded list
    mask = ~valuation_class.isin(EXCLUDED_VALUATION_CLASSES)
    df_filtered = df[mask].copy()
    
    removed_count = initial_count - len(df_filtered)
    print(f"  Removed {removed_count:,} rows with Valuation Classes {EXCLUDED_VALUATION_CLASSES}")
    print(f"  Remaining: {len(df_filtered):,} rows")
    
    return df_filtered


def filter_nis_levels(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with excluded NIS Level 0 Desc values."""
    initial_count = len(df)
    
    # Keep rows NOT in excluded list
    mask = ~df["NIS Level 0 Desc"].isin(EXCLUDED_NIS_LEVELS)
    df_filtered = df[mask].copy()
    
    removed_count = initial_count - len(df_filtered)
    print(f"  Removed {removed_count:,} rows with NIS Levels: {EXCLUDED_NIS_LEVELS}")
    print(f"  Remaining: {len(df_filtered):,} rows")
    
    return df_filtered


def fill_nis_level_for_3021(df: pd.DataFrame) -> pd.DataFrame:
    """Set NIS Level 0 Desc to 'Materials and Supplies' for Valuation Class 3021 where null."""
    valuation_class = pd.to_numeric(df["PO Valuation Class"], errors="coerce")
    
    # Find rows: Valuation Class 3021 AND NIS Level 0 Desc is null/empty
    mask = (valuation_class == 3021) & (df["NIS Level 0 Desc"].isna() | (df["NIS Level 0 Desc"] == ""))
    
    updated_count = mask.sum()
    df.loc[mask, "NIS Level 0 Desc"] = "Materials and Supplies"
    
    print(f"  Updated {updated_count:,} rows (Valuation Class 3021 with null NIS Level)")
    
    return df


def map_vendor_names(df: pd.DataFrame) -> pd.DataFrame:
    """Map Main Vendor Name based on Ultimate Vendor Number."""
    # Find rows where Ultimate Vendor Number matches our mapping
    mask = df["Ultimate Vendor Number"].isin(VENDOR_NAME_MAPPING.keys())
    
    updated_count = mask.sum()
    
    # Apply the mapping
    df.loc[mask, "Main Vendor Name"] = df.loc[mask, "Ultimate Vendor Number"].map(VENDOR_NAME_MAPPING)
    
    print(f"  Updated {updated_count:,} rows with mapped vendor names")
    
    return df


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save the cleaned DataFrame to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"  Saved to: {filepath}")


def main():
    print("=" * 60)
    print("PO Line Items Cleaning Script")
    print("=" * 60)
    
    # Load
    print("\n[1/6] Loading data...")
    df = load_data(INPUT_FILE)
    
    # Filter: Valuation classes
    print("\n[2/6] Filtering valuation classes...")
    df = filter_valuation_classes(df)
    
    # Filter: NIS Levels
    print("\n[3/6] Filtering NIS Level 0 Desc...")
    df = filter_nis_levels(df)
    
    # Transform: Fill NIS Level for 3021
    print("\n[4/6] Filling NIS Level 0 Desc for Valuation Class 3021...")
    df = fill_nis_level_for_3021(df)
    
    # Transform: Map vendor names
    print("\n[5/6] Mapping Main Vendor Name from Ultimate Vendor Number...")
    df = map_vendor_names(df)
    
    # Save
    print("\n[6/6] Saving cleaned data...")
    save_data(df, OUTPUT_FILE)
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
