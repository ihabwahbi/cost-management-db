#!/usr/bin/env python3
"""
Clean GR (Goods Receipt) Table CSV

This script processes the raw GR table CSV file and applies
filtering and transformations as needed.
"""

import pandas as pd
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "gr table.csv"
PO_LINE_ITEMS_FILE = PROJECT_ROOT / "data" / "processed" / "po_line_items_cleaned.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "gr_table_cleaned.csv"


def load_data(filepath: Path) -> pd.DataFrame:
    """Load the raw CSV file."""
    print(f"Loading data from: {filepath}")
    df = pd.read_csv(filepath)
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
    return df


def filter_zero_quantity(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with zero GR Effective Quantity."""
    initial_count = len(df)
    
    # Keep rows where quantity is not zero
    df_filtered = df[df["GR Effective Quantity"] != 0].copy()
    
    removed_count = initial_count - len(df_filtered)
    print(f"  Removed {removed_count:,} rows with zero quantity")
    print(f"  Remaining: {len(df_filtered):,} rows")
    
    return df_filtered


def calculate_gr_amount(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate GR Amount based on unit price from PO Line Items.
    
    Formula: GR Amount = (Purchase Value USD / Ordered Quantity) * GR Effective Quantity
    """
    # Load PO line items to get unit prices
    print(f"  Loading PO line items from: {PO_LINE_ITEMS_FILE}")
    po_df = pd.read_csv(PO_LINE_ITEMS_FILE)
    
    # Calculate unit price for each PO Line ID
    po_df["Unit Price"] = po_df["Purchase Value USD"] / po_df["Ordered Quantity"]
    
    # Create lookup with just PO Line ID and Unit Price
    unit_price_lookup = po_df[["PO Line ID", "Unit Price"]].drop_duplicates()
    print(f"  Created unit price lookup with {len(unit_price_lookup):,} PO Line IDs")
    
    # Merge with GR table (inner join to keep only matching PO Line IDs)
    initial_count = len(df)
    df = df.merge(unit_price_lookup, on="PO Line ID", how="inner")
    
    dropped_count = initial_count - len(df)
    print(f"  Dropped {dropped_count:,} rows with no matching PO Line ID")
    print(f"  Remaining: {len(df):,} rows")
    
    # Calculate GR Amount
    df["GR Amount"] = df["Unit Price"] * df["GR Effective Quantity"]
    
    # Drop the Unit Price column (intermediate)
    df = df.drop(columns=["Unit Price"])
    
    # Round GR Amount to 2 decimal places
    df["GR Amount"] = df["GR Amount"].round(2)
    
    print(f"  Added 'GR Amount' column")
    
    return df


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save the cleaned DataFrame to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"  Saved to: {filepath}")


def main():
    print("=" * 60)
    print("GR Table Cleaning Script")
    print("=" * 60)
    
    # Load
    print("\n[1/4] Loading data...")
    df = load_data(INPUT_FILE)
    
    # Filter: Zero quantity
    print("\n[2/4] Filtering zero quantity rows...")
    df = filter_zero_quantity(df)
    
    # Calculate: GR Amount
    print("\n[3/4] Calculating GR Amount...")
    df = calculate_gr_amount(df)
    
    # Save
    print("\n[4/4] Saving cleaned data...")
    save_data(df, OUTPUT_FILE)
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
