"""
Step 01: Clean GR (Goods Receipt) Data

This script:
1. Reads raw GR data
2. Aggregates by PO Line ID and posting date (sums both quantity and amount)
3. Removes rows where BOTH quantity and amount are 0
4. Outputs cleaned GR data to intermediate/

Note: Raw GR data often has separate rows for quantity and amount postings.
We aggregate both to get the complete picture per PO line per day.

Input:  data/raw/gr table.csv
Output: data/intermediate/gr_cleaned.csv
"""

import pandas as pd
import sys
from config import (
    RAW_GR_FILE,
    INTERMEDIATE_GR_CLEANED,
    ensure_directories,
)


def clean_gr_data():
    """Clean and aggregate GR data."""
    
    print("=" * 60)
    print("STEP 01: CLEAN GR DATA")
    print("=" * 60)
    
    # Ensure output directory exists
    ensure_directories()
    
    # Load raw data
    print(f"\nReading: {RAW_GR_FILE}")
    try:
        df = pd.read_csv(RAW_GR_FILE)
    except FileNotFoundError:
        print(f"ERROR: File not found - {RAW_GR_FILE}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to read file - {e}")
        sys.exit(1)
    
    print(f"  Rows loaded: {len(df):,}")
    
    # Standardize column names (lowercase, underscores)
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    
    # Convert types
    print("\nConverting data types...")
    df['gr_effective_quantity'] = pd.to_numeric(df['gr_effective_quantity'], errors='coerce').fillna(0)
    df['gr_amount_usd'] = pd.to_numeric(df['gr_amount_usd'], errors='coerce').fillna(0)
    df['gr_posting_date'] = pd.to_datetime(df['gr_posting_date'], errors='coerce')
    
    rows_before = len(df)
    
    # Aggregate: Group by PO Line ID and Posting Date, sum both quantity and amount
    # This consolidates separate quantity/amount postings on the same day
    print("\nAggregating by PO Line ID and posting date...")
    df_cleaned = df.groupby(
        ['po_line_id', 'gr_posting_date'], 
        as_index=False
    ).agg({
        'gr_effective_quantity': 'sum',
        'gr_amount_usd': 'sum'
    })
    
    rows_after_agg = len(df_cleaned)
    print(f"  Rows after aggregation: {rows_after_agg:,}")
    
    # Remove rows where BOTH quantity and amount are 0 (no meaningful data)
    df_cleaned = df_cleaned[
        (df_cleaned['gr_effective_quantity'] != 0) | (df_cleaned['gr_amount_usd'] != 0)
    ].copy()
    
    rows_removed = rows_after_agg - len(df_cleaned)
    if rows_removed > 0:
        print(f"  Removed {rows_removed:,} rows with 0 quantity AND 0 amount")
    
    print(f"  Final rows: {len(df_cleaned):,}")
    
    # Save output
    print(f"\nSaving to: {INTERMEDIATE_GR_CLEANED}")
    df_cleaned.to_csv(INTERMEDIATE_GR_CLEANED, index=False)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Input rows:        {rows_before:,}")
    print(f"  After aggregation: {rows_after_agg:,}")
    print(f"  Output rows:       {len(df_cleaned):,}")
    print(f"  Unique PO Lines:   {df_cleaned['po_line_id'].nunique():,}")
    print(f"  Total GR Amount:   ${df_cleaned['gr_amount_usd'].sum():,.2f}")
    print("=" * 60)
    
    return df_cleaned


if __name__ == '__main__':
    clean_gr_data()
    print("\nStep 01 complete.")
