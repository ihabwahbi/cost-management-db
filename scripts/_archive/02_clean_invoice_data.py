"""
Step 02: Clean Invoice Data

This script:
1. Reads raw Invoice data
2. Removes rows where quantity is 0
3. Outputs cleaned Invoice data to intermediate/

Input:  data/raw/invoice table.csv
Output: data/intermediate/invoice_cleaned.csv
"""

import pandas as pd
import sys
from config import (
    RAW_INVOICE_FILE,
    INTERMEDIATE_INVOICE_CLEANED,
    ensure_directories,
)


def clean_invoice_data():
    """Clean invoice data by removing zero quantity rows."""
    
    print("=" * 60)
    print("STEP 02: CLEAN INVOICE DATA")
    print("=" * 60)
    
    # Ensure output directory exists
    ensure_directories()
    
    # Load raw data
    print(f"\nReading: {RAW_INVOICE_FILE}")
    try:
        df = pd.read_csv(RAW_INVOICE_FILE)
    except FileNotFoundError:
        print(f"ERROR: File not found - {RAW_INVOICE_FILE}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to read file - {e}")
        sys.exit(1)
    
    print(f"  Rows loaded: {len(df):,}")
    
    # Standardize column names (lowercase, underscores)
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    
    # Convert types
    print("\nConverting data types...")
    df['ir_effective_quantity'] = pd.to_numeric(df['ir_effective_quantity'], errors='coerce').fillna(0)
    df['ir_amount_usd'] = pd.to_numeric(df['ir_amount_usd'], errors='coerce').fillna(0)
    df['invoice_posting_date'] = pd.to_datetime(df['invoice_posting_date'], errors='coerce')
    
    rows_before = len(df)
    
    # Remove rows where quantity is 0
    df_cleaned = df[df['ir_effective_quantity'] != 0].copy()
    
    rows_removed = rows_before - len(df_cleaned)
    print(f"  Removed {rows_removed:,} rows with 0 quantity")
    print(f"  Final rows: {len(df_cleaned):,}")
    
    # Save output
    print(f"\nSaving to: {INTERMEDIATE_INVOICE_CLEANED}")
    df_cleaned.to_csv(INTERMEDIATE_INVOICE_CLEANED, index=False)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Input rows:         {rows_before:,}")
    print(f"  Removed (0 qty):    {rows_removed:,}")
    print(f"  Output rows:        {len(df_cleaned):,}")
    print(f"  Unique PO Lines:    {df_cleaned['po_line_id'].nunique():,}")
    print(f"  Total Invoice Amt:  ${df_cleaned['ir_amount_usd'].sum():,.2f}")
    print("=" * 60)
    
    return df_cleaned


if __name__ == '__main__':
    clean_invoice_data()
    print("\nStep 02 complete.")
