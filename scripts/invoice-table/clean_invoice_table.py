#!/usr/bin/env python3
"""
Clean Invoice Table CSV

This script processes the raw Invoice table CSV file and applies
filtering and transformations as needed.
"""

import pandas as pd
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "invoice table.csv"
PO_LINE_ITEMS_FILE = PROJECT_ROOT / "data" / "processed" / "po_line_items_cleaned.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "invoice_table_cleaned.csv"


def load_data(filepath: Path) -> pd.DataFrame:
    """Load the raw CSV file."""
    print(f"Loading data from: {filepath}")
    df = pd.read_csv(filepath)
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
    return df


def calculate_invoice_amount(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Invoice Amount based on unit price from PO Line Items.
    Also drops rows with no matching PO Line ID.
    
    Formula: Invoice Amount = (Purchase Value USD / Ordered Quantity) * IR Effective Quantity
    """
    # Load PO line items to get unit prices
    print(f"  Loading PO line items from: {PO_LINE_ITEMS_FILE}")
    po_df = pd.read_csv(PO_LINE_ITEMS_FILE)
    
    # Calculate unit price for each PO Line ID
    po_df["Unit Price"] = po_df["Purchase Value USD"] / po_df["Ordered Quantity"]
    
    # Create lookup with just PO Line ID and Unit Price
    unit_price_lookup = po_df[["PO Line ID", "Unit Price"]].drop_duplicates()
    print(f"  Created unit price lookup with {len(unit_price_lookup):,} PO Line IDs")
    
    # Merge with Invoice table (inner join to keep only matching PO Line IDs)
    initial_count = len(df)
    df = df.merge(unit_price_lookup, on="PO Line ID", how="inner")
    
    dropped_count = initial_count - len(df)
    print(f"  Dropped {dropped_count:,} rows with no matching PO Line ID")
    print(f"  Remaining: {len(df):,} rows")
    
    # Calculate Invoice Amount
    df["Invoice Amount"] = df["Unit Price"] * df["IR Effective Quantity"]
    
    # Drop the Unit Price column (intermediate)
    df = df.drop(columns=["Unit Price"])
    
    # Round Invoice Amount to 2 decimal places
    df["Invoice Amount"] = df["Invoice Amount"].round(2)
    
    print(f"  Added 'Invoice Amount' column")
    
    return df


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save the cleaned DataFrame to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"  Saved to: {filepath}")


def main():
    print("=" * 60)
    print("Invoice Table Cleaning Script")
    print("=" * 60)
    
    # Load
    print("\n[1/3] Loading data...")
    df = load_data(INPUT_FILE)
    
    # Calculate: Invoice Amount (also filters unmatched PO Line IDs)
    print("\n[2/3] Calculating Invoice Amount...")
    df = calculate_invoice_amount(df)
    
    # Save
    print("\n[3/3] Saving cleaned data...")
    save_data(df, OUTPUT_FILE)
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
