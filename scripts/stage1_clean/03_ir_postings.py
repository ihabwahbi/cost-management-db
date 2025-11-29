#!/usr/bin/env python3
"""
Stage 1: Clean IR (Invoice Receipt) Postings

Reads raw invoice table, calculates invoice amounts using unit prices
from intermediate PO line items.

Dependencies: 01_po_line_items.py must run first
Input: data/raw/invoice table.csv, data/intermediate/po_line_items.csv
Output: data/intermediate/ir_postings.csv
"""

import sys
from pathlib import Path

import pandas as pd

# Paths
SCRIPTS_DIR = Path(__file__).parent.parent
PROJECT_ROOT = SCRIPTS_DIR.parent
INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "invoice table.csv"
PO_LINE_ITEMS_FILE = PROJECT_ROOT / "data" / "intermediate" / "po_line_items.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "intermediate" / "ir_postings.csv"


def load_data(filepath: Path) -> pd.DataFrame:
    """Load the raw CSV file."""
    print(f"Loading data from: {filepath}")
    df = pd.read_csv(filepath)
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
    return df


def calculate_invoice_amount(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Invoice Amount based on unit price from PO Line Items.
    Formula: Invoice Amount = (Purchase Value USD / Ordered Quantity) * IR Effective Quantity
    """
    # Load PO line items to get unit prices
    print(f"  Loading unit prices from: {PO_LINE_ITEMS_FILE}")
    po_df = pd.read_csv(PO_LINE_ITEMS_FILE)
    
    # Calculate unit price for each PO Line ID
    po_df["Unit Price"] = po_df["Purchase Value USD"] / po_df["Ordered Quantity"]
    unit_price_lookup = po_df[["PO Line ID", "Unit Price"]].drop_duplicates()
    print(f"  Unit price lookup: {len(unit_price_lookup):,} PO Line IDs")
    
    # Merge with Invoice table (inner join to keep only matching PO Line IDs)
    initial_count = len(df)
    df = df.merge(unit_price_lookup, on="PO Line ID", how="inner")
    dropped_count = initial_count - len(df)
    print(f"  Dropped {dropped_count:,} rows with no matching PO Line ID")
    
    # Calculate Invoice Amount
    df["Invoice Amount"] = (df["Unit Price"] * df["IR Effective Quantity"]).round(2)
    
    # Keep only needed columns
    df = df[["PO Line ID", "Invoice Posting Date", "IR Effective Quantity", "Invoice Amount"]]
    
    return df


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save the cleaned DataFrame to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"  Saved to: {filepath}")
    print(f"  Final row count: {len(df):,}")


def main():
    print("=" * 60)
    print("Stage 1: Clean IR Postings")
    print("=" * 60)
    
    # Check dependency
    if not PO_LINE_ITEMS_FILE.exists():
        print(f"ERROR: Dependency not found: {PO_LINE_ITEMS_FILE}")
        print("Run 01_po_line_items.py first")
        return False
    
    print("\n[1/2] Loading data...")
    df = load_data(INPUT_FILE)
    
    print("\n[2/2] Calculating Invoice Amount...")
    df = calculate_invoice_amount(df)
    
    print("\n[Save] Writing output...")
    save_data(df, OUTPUT_FILE)
    
    print("\n" + "=" * 60)
    print("Stage 1 Complete: IR Postings cleaned")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
