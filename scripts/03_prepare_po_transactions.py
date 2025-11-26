"""
Step 03: Prepare PO Transactions for Database Import

This script:
1. Loads cleaned GR data (from step 01)
2. Loads raw Invoice data
3. Loads cost recognition lookup (from step 02)
4. Combines into unified transaction format
5. Applies is_cost_recognized logic
6. Outputs import-ready file matching po_transactions schema

Input:  
  - data/intermediate/gr_cleaned.csv
  - data/raw/invoice table.csv
  - data/intermediate/po_cost_recognition_lookup.csv

Output: 
  - data/import_ready/po_transactions.csv
"""

import pandas as pd
import sys
from config import (
    RAW_INVOICE_FILE,
    INTERMEDIATE_GR_CLEANED,
    INTERMEDIATE_PO_LOOKUP,
    IMPORT_READY_PO_TRANSACTIONS,
    ensure_directories,
)


def load_gr_data():
    """Load cleaned GR data."""
    print(f"  Loading GR data: {INTERMEDIATE_GR_CLEANED}")
    try:
        df = pd.read_csv(INTERMEDIATE_GR_CLEANED)
        print(f"    Rows: {len(df):,}")
        return df
    except FileNotFoundError:
        print(f"  ERROR: File not found. Run 01_clean_gr_data.py first.")
        sys.exit(1)


def load_invoice_data():
    """Load raw invoice data."""
    print(f"  Loading Invoice data: {RAW_INVOICE_FILE}")
    try:
        df = pd.read_csv(RAW_INVOICE_FILE)
        # Standardize column names
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        print(f"    Rows: {len(df):,}")
        return df
    except FileNotFoundError:
        print(f"  ERROR: File not found - {RAW_INVOICE_FILE}")
        sys.exit(1)


def load_cost_lookup():
    """Load cost recognition lookup."""
    print(f"  Loading cost lookup: {INTERMEDIATE_PO_LOOKUP}")
    try:
        df = pd.read_csv(INTERMEDIATE_PO_LOOKUP)
        print(f"    Rows: {len(df):,}")
        return df
    except FileNotFoundError:
        print(f"  ERROR: File not found. Run 02_build_po_lookup.py first.")
        sys.exit(1)


def transform_gr_data(df):
    """Transform GR data to transaction format."""
    transformed = pd.DataFrame()
    transformed['po_line_id'] = df['po_line_id']
    transformed['transaction_type'] = 'GR'
    transformed['posting_date'] = pd.to_datetime(df['gr_posting_date']).dt.strftime('%Y-%m-%d')
    transformed['quantity'] = df['gr_effective_quantity']
    transformed['amount'] = df['gr_amount_usd']
    transformed['reference_number'] = None
    return transformed


def transform_invoice_data(df):
    """Transform Invoice data to transaction format."""
    transformed = pd.DataFrame()
    transformed['po_line_id'] = df['po_line_id']
    transformed['transaction_type'] = 'Invoice'
    transformed['posting_date'] = pd.to_datetime(df['invoice_posting_date']).dt.strftime('%Y-%m-%d')
    transformed['quantity'] = df['ir_effective_quantity']
    transformed['amount'] = df['ir_amount_usd']
    transformed['reference_number'] = None
    return transformed


def prepare_po_transactions():
    """Prepare final PO transactions file for database import."""
    
    print("=" * 60)
    print("STEP 03: PREPARE PO TRANSACTIONS")
    print("=" * 60)
    
    # Ensure output directory exists
    ensure_directories()
    
    # Load all required data
    print("\nLoading data...")
    gr_df = load_gr_data()
    invoice_df = load_invoice_data()
    lookup_df = load_cost_lookup()
    
    # Transform to common format
    print("\nTransforming to transaction format...")
    gr_transactions = transform_gr_data(gr_df)
    invoice_transactions = transform_invoice_data(invoice_df)
    
    print(f"  GR transactions:      {len(gr_transactions):,}")
    print(f"  Invoice transactions: {len(invoice_transactions):,}")
    
    # Combine all transactions
    print("\nCombining transactions...")
    all_transactions = pd.concat([gr_transactions, invoice_transactions], ignore_index=True)
    print(f"  Total transactions:   {len(all_transactions):,}")
    
    # Join with cost recognition lookup
    print("\nApplying cost recognition logic...")
    all_transactions = all_transactions.merge(
        lookup_df[['po_line_id', 'cost_recognized_at_gr']],
        on='po_line_id',
        how='left'
    )
    
    # Handle PO lines not found in lookup (default to cost at Invoice)
    missing_lookup = all_transactions['cost_recognized_at_gr'].isna().sum()
    if missing_lookup > 0:
        print(f"  WARNING: {missing_lookup:,} transactions have no lookup entry (defaulting to cost at Invoice)")
        all_transactions['cost_recognized_at_gr'] = all_transactions['cost_recognized_at_gr'].fillna(False)
    
    # Calculate is_cost_recognized
    # True if: (cost_at_gr AND type=GR) OR (NOT cost_at_gr AND type=Invoice)
    all_transactions['is_cost_recognized'] = (
        ((all_transactions['cost_recognized_at_gr'] == True) & (all_transactions['transaction_type'] == 'GR')) |
        ((all_transactions['cost_recognized_at_gr'] == False) & (all_transactions['transaction_type'] == 'Invoice'))
    )
    
    # Drop the helper column
    all_transactions = all_transactions.drop(columns=['cost_recognized_at_gr'])
    
    # Sort by po_line_id and posting_date for readability
    all_transactions = all_transactions.sort_values(['po_line_id', 'posting_date'])
    
    # Reorder columns to match schema
    final_columns = [
        'po_line_id',
        'transaction_type',
        'posting_date',
        'quantity',
        'amount',
        'is_cost_recognized',
        'reference_number'
    ]
    all_transactions = all_transactions[final_columns]
    
    # Save output
    print(f"\nSaving to: {IMPORT_READY_PO_TRANSACTIONS}")
    all_transactions.to_csv(IMPORT_READY_PO_TRANSACTIONS, index=False)
    
    # Summary statistics
    cost_recognized_count = all_transactions['is_cost_recognized'].sum()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total transactions:     {len(all_transactions):,}")
    print(f"  GR transactions:        {len(gr_transactions):,}")
    print(f"  Invoice transactions:   {len(invoice_transactions):,}")
    print(f"  Cost recognized (True): {cost_recognized_count:,}")
    print(f"  Cost recognized (False):{len(all_transactions) - cost_recognized_count:,}")
    print(f"  Unique PO Lines:        {all_transactions['po_line_id'].nunique():,}")
    print("=" * 60)
    
    # Show sample output
    print("\nSample output (first 10 rows):")
    print(all_transactions.head(10).to_string(index=False))
    
    return all_transactions


if __name__ == '__main__':
    prepare_po_transactions()
    print("\nStep 03 complete.")
