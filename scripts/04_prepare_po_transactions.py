"""
Step 04: Prepare PO Transactions for Database Import

This script:
1. Loads cleaned GR data (from step 01)
2. Loads cleaned Invoice data (from step 02)
3. Loads cost recognition lookup (from step 03)
4. Combines into unified transaction format
5. Applies is_cost_recognized logic
6. Outputs import-ready file matching po_transactions schema

Input:  
  - data/intermediate/gr_cleaned.csv
  - data/intermediate/invoice_cleaned.csv
  - data/intermediate/po_cost_recognition_lookup.csv

Output: 
  - data/import_ready/po_transactions.csv
"""

import pandas as pd
import sys
from config import (
    INTERMEDIATE_GR_CLEANED,
    INTERMEDIATE_INVOICE_CLEANED,
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
    """Load cleaned invoice data."""
    print(f"  Loading Invoice data: {INTERMEDIATE_INVOICE_CLEANED}")
    try:
        df = pd.read_csv(INTERMEDIATE_INVOICE_CLEANED)
        print(f"    Rows: {len(df):,}")
        return df
    except FileNotFoundError:
        print(f"  ERROR: File not found. Run 02_clean_invoice_data.py first.")
        sys.exit(1)


def load_cost_lookup():
    """Load cost recognition lookup."""
    print(f"  Loading cost lookup: {INTERMEDIATE_PO_LOOKUP}")
    try:
        df = pd.read_csv(INTERMEDIATE_PO_LOOKUP)
        print(f"    Rows: {len(df):,}")
        return df
    except FileNotFoundError:
        print(f"  ERROR: File not found. Run 03_build_po_lookup.py first.")
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
    print("STEP 04: PREPARE PO TRANSACTIONS")
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
    
    # Handle PO lines not found in lookup (default to cost at Invoice rules)
    missing_lookup = all_transactions['cost_recognized_at_gr'].isna().sum()
    if missing_lookup > 0:
        print(f"  WARNING: {missing_lookup:,} transactions have no lookup entry (defaulting to Invoice rules)")
        all_transactions['cost_recognized_at_gr'] = all_transactions['cost_recognized_at_gr'].fillna(False)
    
    # Convert posting_date to datetime for comparison
    all_transactions['posting_date_dt'] = pd.to_datetime(all_transactions['posting_date'])
    
    # For PO lines where cost is normally at Invoice (cost_recognized_at_gr = False),
    # we need to check if GR came before Invoice. If so, GR gets cost recognition.
    
    # Step 1: Find earliest GR date per PO line
    gr_dates = all_transactions[all_transactions['transaction_type'] == 'GR'].groupby('po_line_id')['posting_date_dt'].min()
    gr_dates = gr_dates.rename('earliest_gr_date')
    
    # Step 2: Find earliest Invoice date per PO line
    inv_dates = all_transactions[all_transactions['transaction_type'] == 'Invoice'].groupby('po_line_id')['posting_date_dt'].min()
    inv_dates = inv_dates.rename('earliest_inv_date')
    
    # Step 3: Join these back to determine which type gets cost recognition
    all_transactions = all_transactions.merge(gr_dates, on='po_line_id', how='left')
    all_transactions = all_transactions.merge(inv_dates, on='po_line_id', how='left')
    
    # Step 4: Determine effective cost recognition type per PO line
    # For cost_at_gr lines: always GR
    # For cost_at_invoice lines: GR if earliest_gr < earliest_inv (or no invoice), else Invoice
    def determine_cost_type(row):
        if row['cost_recognized_at_gr']:
            return 'GR'
        else:
            # Cost normally at Invoice, but check timing
            if pd.isna(row['earliest_inv_date']):
                # No invoice exists, GR gets cost recognition
                return 'GR'
            elif pd.isna(row['earliest_gr_date']):
                # No GR exists, Invoice gets cost recognition
                return 'Invoice'
            elif row['earliest_gr_date'] < row['earliest_inv_date']:
                # GR came first, GR gets cost recognition
                return 'GR'
            else:
                # Invoice came first or same date, Invoice gets cost recognition
                return 'Invoice'
    
    all_transactions['cost_recognition_type'] = all_transactions.apply(determine_cost_type, axis=1)
    
    # Step 5: Set is_cost_recognized based on whether this transaction matches the cost recognition type
    all_transactions['is_cost_recognized'] = (
        all_transactions['transaction_type'] == all_transactions['cost_recognition_type']
    )
    
    # Drop helper columns
    all_transactions = all_transactions.drop(columns=[
        'cost_recognized_at_gr', 'posting_date_dt', 
        'earliest_gr_date', 'earliest_inv_date', 'cost_recognition_type'
    ])
    
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
    print("\nStep 04 complete.")
