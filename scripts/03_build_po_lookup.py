"""
Step 03: Build PO Cost Recognition Lookup

This script:
1. Reads raw PO line items data
2. Determines cost recognition point for each PO line
3. Outputs a lookup table to intermediate/

Business Rules - Cost is recognized at GR if:
  1. Main Vendor SLB Vendor Category = "3rd Party"
  OR
  2. PO Account Assignment Category IN ("P", "K") AND Main Vendor SLB Vendor Category = "GLD"

Otherwise, cost is recognized at Invoice (IR).

Input:  data/raw/po line items.csv
Output: data/intermediate/po_cost_recognition_lookup.csv
"""

import pandas as pd
import sys
from config import (
    RAW_PO_LINE_ITEMS_FILE,
    INTERMEDIATE_PO_LOOKUP,
    PO_LINE_ITEMS_COLUMNS,
    VENDOR_CATEGORY_3RD_PARTY,
    VENDOR_CATEGORY_GLD,
    ACCOUNT_ASSIGNMENTS_FOR_GLD,
    ensure_directories,
)


def determine_cost_at_gr(row):
    """
    Determine if cost is recognized at GR for a given PO line.
    
    Returns True if cost is recognized at GR, False if at Invoice.
    """
    vendor_category = str(row['vendor_category']).strip()
    account_assignment = str(row['account_assignment']).strip()
    
    # Rule 1: 3rd Party vendors -> cost at GR
    if vendor_category == VENDOR_CATEGORY_3RD_PARTY:
        return True
    
    # Rule 2: GLD vendors with P or K account assignment -> cost at GR
    if vendor_category == VENDOR_CATEGORY_GLD and account_assignment in ACCOUNT_ASSIGNMENTS_FOR_GLD:
        return True
    
    # Everything else -> cost at Invoice
    return False


def build_po_lookup():
    """Build cost recognition lookup table from PO line items."""
    
    print("=" * 60)
    print("STEP 03: BUILD PO COST RECOGNITION LOOKUP")
    print("=" * 60)
    
    # Ensure output directory exists
    ensure_directories()
    
    # Load raw data
    print(f"\nReading: {RAW_PO_LINE_ITEMS_FILE}")
    try:
        df = pd.read_csv(RAW_PO_LINE_ITEMS_FILE)
    except FileNotFoundError:
        print(f"ERROR: File not found - {RAW_PO_LINE_ITEMS_FILE}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to read file - {e}")
        sys.exit(1)
    
    print(f"  Rows loaded: {len(df):,}")
    
    # Select and rename columns we need
    print("\nExtracting relevant columns...")
    lookup_df = pd.DataFrame()
    lookup_df['po_line_id'] = df[PO_LINE_ITEMS_COLUMNS['po_line_id']]
    lookup_df['vendor_category'] = df[PO_LINE_ITEMS_COLUMNS['vendor_category']].fillna('')
    lookup_df['account_assignment'] = df[PO_LINE_ITEMS_COLUMNS['account_assignment']].fillna('')
    
    # Apply cost recognition logic
    print("\nApplying cost recognition rules...")
    lookup_df['cost_recognized_at_gr'] = lookup_df.apply(determine_cost_at_gr, axis=1)
    
    # Keep only the columns we need for lookup
    output_df = lookup_df[['po_line_id', 'cost_recognized_at_gr']].copy()
    
    # Remove duplicates (shouldn't be any, but just in case)
    output_df = output_df.drop_duplicates(subset=['po_line_id'])
    
    # Save output
    print(f"\nSaving to: {INTERMEDIATE_PO_LOOKUP}")
    output_df.to_csv(INTERMEDIATE_PO_LOOKUP, index=False)
    
    # Summary statistics
    cost_at_gr = output_df['cost_recognized_at_gr'].sum()
    cost_at_ir = len(output_df) - cost_at_gr
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total PO Lines:       {len(output_df):,}")
    print(f"  Cost at GR:           {cost_at_gr:,} ({100*cost_at_gr/len(output_df):.1f}%)")
    print(f"  Cost at Invoice:      {cost_at_ir:,} ({100*cost_at_ir/len(output_df):.1f}%)")
    print("=" * 60)
    
    # Show breakdown by vendor category for verification
    print("\nBreakdown by Vendor Category:")
    breakdown = lookup_df.groupby('vendor_category')['cost_recognized_at_gr'].agg(['count', 'sum'])
    breakdown.columns = ['Total', 'Cost at GR']
    breakdown['Cost at IR'] = breakdown['Total'] - breakdown['Cost at GR']
    print(breakdown.to_string())
    
    return output_df


if __name__ == '__main__':
    build_po_lookup()
    print("\nStep 03 complete.")
