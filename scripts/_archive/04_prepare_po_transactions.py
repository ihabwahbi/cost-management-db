"""
Step 04: Prepare PO Transactions for Database Import

This script:
1. Loads cleaned GR data (from step 01)
2. Loads cleaned Invoice data (from step 02)
3. Loads cost recognition lookup (from step 03)
4. Combines into unified transaction format
5. Applies cost recognition logic with partial quantity support
6. Outputs import-ready file matching po_transactions schema

Cost Recognition Rules:
- GLD + P/K PO lines: Only GR triggers cost recognition (full qty)
- All other PO lines: High water mark logic - whichever event (GR or Invoice)
  pushes max(cum_gr, cum_inv) forward gets cost recognition for that qty

Input:  
  - data/intermediate/gr_cleaned.csv
  - data/intermediate/invoice_cleaned.csv
  - data/intermediate/po_cost_recognition_lookup.csv

Output: 
  - data/import_ready/po_transactions.csv
"""

import pandas as pd
import numpy as np
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


def calculate_cost_recognition_for_gr_only(group):
    """
    For GLD + P/K PO lines: Only GR triggers cost recognition.
    GR gets full quantity, Invoice gets 0.
    """
    result = group.copy()
    result['cost_recognized_qty'] = np.where(
        result['transaction_type'] == 'GR',
        result['quantity'],
        0
    )
    return result


def calculate_cost_recognition_high_water_mark(group):
    """
    For non-GLD+P/K PO lines: Apply high water mark logic.
    
    Sort by posting_date ASC, then quantity DESC (higher qty first for same date).
    Cost recognized qty = increase in max(cumulative_gr, cumulative_invoice).
    """
    # Sort: date ascending, quantity descending (higher qty first on same date)
    group = group.sort_values(
        ['posting_date', 'quantity'], 
        ascending=[True, False]
    ).copy()
    
    # Initialize tracking variables
    cum_gr = 0
    cum_inv = 0
    prev_high_water = 0
    cost_recognized_qtys = []
    
    for idx, row in group.iterrows():
        qty = row['quantity']
        
        if row['transaction_type'] == 'GR':
            cum_gr += qty
        else:  # Invoice
            cum_inv += qty
        
        # High water mark is the max of cumulative GR and Invoice
        high_water = max(cum_gr, cum_inv)
        
        # Cost recognized for this transaction is the increase in high water mark
        cost_recognized_qty = high_water - prev_high_water
        cost_recognized_qtys.append(cost_recognized_qty)
        
        prev_high_water = high_water
    
    group['cost_recognized_qty'] = cost_recognized_qtys
    return group


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
    
    # Handle PO lines not found in lookup (default to high water mark rules)
    missing_lookup = all_transactions['cost_recognized_at_gr'].isna().sum()
    if missing_lookup > 0:
        print(f"  WARNING: {missing_lookup:,} transactions have no lookup entry (using high water mark rules)")
        all_transactions['cost_recognized_at_gr'] = all_transactions['cost_recognized_at_gr'].fillna(False)
    
    # Split into two groups based on cost recognition type
    gr_only_mask = all_transactions['cost_recognized_at_gr'] == True
    gr_only_lines = all_transactions[gr_only_mask]['po_line_id'].unique()
    high_water_lines = all_transactions[~gr_only_mask]['po_line_id'].unique()
    
    print(f"  GLD+P/K PO lines (GR only):     {len(gr_only_lines):,}")
    print(f"  Other PO lines (high water):    {len(high_water_lines):,}")
    
    # Process GR-only PO lines
    print("\n  Processing GR-only cost recognition...")
    gr_only_transactions = all_transactions[all_transactions['po_line_id'].isin(gr_only_lines)]
    if len(gr_only_transactions) > 0:
        gr_only_result = gr_only_transactions.groupby('po_line_id', group_keys=False).apply(
            calculate_cost_recognition_for_gr_only
        )
    else:
        gr_only_result = pd.DataFrame()
    
    # Process high water mark PO lines
    print("  Processing high water mark cost recognition...")
    high_water_transactions = all_transactions[all_transactions['po_line_id'].isin(high_water_lines)]
    if len(high_water_transactions) > 0:
        high_water_result = high_water_transactions.groupby('po_line_id', group_keys=False).apply(
            calculate_cost_recognition_high_water_mark
        )
    else:
        high_water_result = pd.DataFrame()
    
    # Combine results
    all_transactions = pd.concat([gr_only_result, high_water_result], ignore_index=True)
    
    # Set is_cost_recognized based on cost_recognized_qty > 0
    all_transactions['is_cost_recognized'] = all_transactions['cost_recognized_qty'] > 0
    
    # Drop helper column
    all_transactions = all_transactions.drop(columns=['cost_recognized_at_gr'])
    
    # Sort by po_line_id and posting_date for readability
    all_transactions = all_transactions.sort_values(['po_line_id', 'posting_date', 'quantity'], 
                                                     ascending=[True, True, False])
    
    # Reorder columns to match schema
    final_columns = [
        'po_line_id',
        'transaction_type',
        'posting_date',
        'quantity',
        'amount',
        'cost_recognized_qty',
        'is_cost_recognized',
        'reference_number'
    ]
    all_transactions = all_transactions[final_columns]
    
    # Save output
    print(f"\nSaving to: {IMPORT_READY_PO_TRANSACTIONS}")
    all_transactions.to_csv(IMPORT_READY_PO_TRANSACTIONS, index=False)
    
    # Summary statistics
    total_qty = all_transactions['quantity'].sum()
    total_cost_recognized_qty = all_transactions['cost_recognized_qty'].sum()
    cost_recognized_count = all_transactions['is_cost_recognized'].sum()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total transactions:       {len(all_transactions):,}")
    print(f"  GR transactions:          {len(gr_transactions):,}")
    print(f"  Invoice transactions:     {len(invoice_transactions):,}")
    print(f"  Total quantity:           {total_qty:,.2f}")
    print(f"  Cost recognized qty:      {total_cost_recognized_qty:,.2f}")
    print(f"  Transactions with cost:   {cost_recognized_count:,}")
    print(f"  Transactions without:     {len(all_transactions) - cost_recognized_count:,}")
    print(f"  Unique PO Lines:          {all_transactions['po_line_id'].nunique():,}")
    print("=" * 60)
    
    # Show sample output
    print("\nSample output (first 15 rows):")
    print(all_transactions.head(15).to_string(index=False))
    
    return all_transactions


if __name__ == '__main__':
    prepare_po_transactions()
    print("\nStep 04 complete.")
