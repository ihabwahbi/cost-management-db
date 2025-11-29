#!/usr/bin/env python3
"""
Stage 1: Clean GR (Goods Receipt) Postings

Reads raw GR table, filters and calculates GR amounts using unit prices
from intermediate PO line items.

Dependencies: 01_po_line_items.py must run first
Input: data/raw/gr table.csv, data/intermediate/po_line_items.csv
Output: data/intermediate/gr_postings.csv
"""

import sys
from pathlib import Path

import pandas as pd

# Paths
SCRIPTS_DIR = Path(__file__).parent.parent
PROJECT_ROOT = SCRIPTS_DIR.parent
INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "gr table.csv"
PO_LINE_ITEMS_FILE = PROJECT_ROOT / "data" / "intermediate" / "po_line_items.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "intermediate" / "gr_postings.csv"


def load_data(filepath: Path) -> pd.DataFrame:
    """Load the raw CSV file."""
    print(f"Loading data from: {filepath}")
    df = pd.read_csv(filepath)
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
    return df


def filter_zero_quantity(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with zero GR Effective Quantity."""
    initial_count = len(df)
    df_filtered = df[df["GR Effective Quantity"] != 0].copy()
    removed_count = initial_count - len(df_filtered)
    print(f"  Removed {removed_count:,} rows with zero quantity")
    return df_filtered


def calculate_gr_amount(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate GR Amount based on unit price from PO Line Items.
    Formula: GR Amount = (Purchase Value USD / Ordered Quantity) * GR Effective Quantity
    """
    # Load PO line items to get unit prices
    print(f"  Loading unit prices from: {PO_LINE_ITEMS_FILE}")
    po_df = pd.read_csv(PO_LINE_ITEMS_FILE)
    
    # Calculate unit price for each PO Line ID
    po_df["Unit Price"] = po_df["Purchase Value USD"] / po_df["Ordered Quantity"]
    unit_price_lookup = po_df[["PO Line ID", "Unit Price"]].drop_duplicates()
    print(f"  Unit price lookup: {len(unit_price_lookup):,} PO Line IDs")
    
    # Merge with GR table (inner join to keep only matching PO Line IDs)
    initial_count = len(df)
    df = df.merge(unit_price_lookup, on="PO Line ID", how="inner")
    dropped_count = initial_count - len(df)
    print(f"  Dropped {dropped_count:,} rows with no matching PO Line ID")
    
    # Calculate GR Amount
    df["GR Amount"] = (df["Unit Price"] * df["GR Effective Quantity"]).round(2)
    
    # Keep only needed columns
    df = df[["PO Line ID", "GR Posting Date", "GR Effective Quantity", "GR Amount"]]
    
    return df


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save the cleaned DataFrame to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"  Saved to: {filepath}")
    print(f"  Final row count: {len(df):,}")


def main():
    print("=" * 60)
    print("Stage 1: Clean GR Postings")
    print("=" * 60)
    
    # Check dependency
    if not PO_LINE_ITEMS_FILE.exists():
        print(f"ERROR: Dependency not found: {PO_LINE_ITEMS_FILE}")
        print("Run 01_po_line_items.py first")
        return False
    
    print("\n[1/3] Loading data...")
    df = load_data(INPUT_FILE)
    
    print("\n[2/3] Filtering zero quantity rows...")
    df = filter_zero_quantity(df)
    
    print("\n[3/3] Calculating GR Amount...")
    df = calculate_gr_amount(df)
    
    print("\n[Save] Writing output...")
    save_data(df, OUTPUT_FILE)
    
    print("\n" + "=" * 60)
    print("Stage 1 Complete: GR Postings cleaned")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
