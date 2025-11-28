#!/usr/bin/env python3
"""
Calculate Cost Impact from GR and Invoice postings.

This script calculates the actual cost impact on the net income statement
based on GR and IR postings for each PO Line Item.

Two types of cost impact calculation:
1. Simple (GLD + K/P/S/V): Cost impact = GR postings only
2. Complex (all others): Cost impact based on chronological GR/IR postings
"""

import pandas as pd
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
PO_LINE_ITEMS_FILE = PROJECT_ROOT / "data" / "processed" / "po_line_items_cleaned.csv"
GR_TABLE_FILE = PROJECT_ROOT / "data" / "processed" / "gr_table_cleaned.csv"
INVOICE_TABLE_FILE = PROJECT_ROOT / "data" / "processed" / "invoice_table_cleaned.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "cost_impact.csv"

# Classification criteria for simple cost impact (Type 1)
SIMPLE_VENDOR_CATEGORY = "GLD"
SIMPLE_ACCOUNT_CATEGORIES = ["K", "P", "S", "V"]


def load_data():
    """Load all required data files."""
    print("Loading PO Line Items...")
    po_df = pd.read_csv(PO_LINE_ITEMS_FILE)
    print(f"  Loaded {len(po_df):,} PO Line Items")
    
    print("Loading GR Table...")
    gr_df = pd.read_csv(GR_TABLE_FILE)
    print(f"  Loaded {len(gr_df):,} GR postings")
    
    print("Loading Invoice Table...")
    ir_df = pd.read_csv(INVOICE_TABLE_FILE)
    print(f"  Loaded {len(ir_df):,} IR postings")
    
    return po_df, gr_df, ir_df


def classify_po_line_items(po_df: pd.DataFrame) -> tuple:
    """
    Classify PO Line Items into simple (Type 1) and complex (Type 2).
    
    Type 1 (Simple): Main Vendor SLB Vendor Category = "GLD" 
                     AND PO Account Assignment Category IN (K, P, S, V)
    Type 2 (Complex): All others
    """
    # Create classification mask
    is_gld = po_df["Main Vendor SLB Vendor Category"] == SIMPLE_VENDOR_CATEGORY
    is_valid_category = po_df["PO Account Assignment Category"].isin(SIMPLE_ACCOUNT_CATEGORIES)
    
    simple_mask = is_gld & is_valid_category
    
    simple_po_ids = set(po_df.loc[simple_mask, "PO Line ID"])
    complex_po_ids = set(po_df.loc[~simple_mask, "PO Line ID"])
    
    print(f"  Type 1 (Simple - GLD + K/P/S/V): {len(simple_po_ids):,} PO Line IDs")
    print(f"  Type 2 (Complex): {len(complex_po_ids):,} PO Line IDs")
    
    return simple_po_ids, complex_po_ids


def calculate_simple_cost_impact(gr_df: pd.DataFrame, simple_po_ids: set) -> pd.DataFrame:
    """
    Calculate cost impact for Type 1 (Simple) PO Line Items.
    Cost impact = GR postings only (IR is ignored).
    """
    # Filter GR postings for simple PO Line IDs
    simple_gr = gr_df[gr_df["PO Line ID"].isin(simple_po_ids)].copy()
    
    # Create cost impact DataFrame
    result = pd.DataFrame({
        "PO Line ID": simple_gr["PO Line ID"],
        "Posting Date": simple_gr["GR Posting Date"],
        "Posting Type": "GR",
        "Posting Qty": simple_gr["GR Effective Quantity"],
        "Cost Impact Qty": simple_gr["GR Effective Quantity"],
        "Cost Impact Amount": simple_gr["GR Amount"],
    })
    
    print(f"  Generated {len(result):,} cost impact records from GR postings")
    
    return result


def calculate_complex_cost_impact(gr_df: pd.DataFrame, ir_df: pd.DataFrame, 
                                   complex_po_ids: set, po_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate cost impact for Type 2 (Complex) PO Line Items.
    
    For each PO Line ID, process GR and IR postings chronologically:
    - Track cumulative GR and cumulative IR separately
    - For GR: If Cum GR >= Cum IR, use Cum GR; else use Max(Cum GR, Cum IR)
    - For IR: If Cum IR >= Cum GR, use Cum IR; else use Max(Cum GR, Cum IR)
    - Cost Impact = Selected Cumulative - Last Cumulative Cost Impact
    - Negative values are allowed (reversals)
    """
    # Filter for complex PO Line IDs
    complex_gr = gr_df[gr_df["PO Line ID"].isin(complex_po_ids)].copy()
    complex_ir = ir_df[ir_df["PO Line ID"].isin(complex_po_ids)].copy()
    
    # Prepare GR postings
    complex_gr = complex_gr.rename(columns={
        "GR Posting Date": "Posting Date",
        "GR Effective Quantity": "Posting Qty",
        "GR Amount": "Posting Amount"
    })
    complex_gr["Posting Type"] = "GR"
    
    # Prepare IR postings
    complex_ir = complex_ir.rename(columns={
        "Invoice Posting Date": "Posting Date",
        "IR Effective Quantity": "Posting Qty",
        "Invoice Amount": "Posting Amount"
    })
    complex_ir["Posting Type"] = "IR"
    
    # Combine and sort by PO Line ID and Posting Date
    combined = pd.concat([complex_gr, complex_ir], ignore_index=True)
    combined["Posting Date"] = pd.to_datetime(combined["Posting Date"])
    combined = combined.sort_values(["PO Line ID", "Posting Date", "Posting Type"])
    
    # Get unit prices from PO Line Items for amount calculation
    po_df["Unit Price"] = po_df["Purchase Value USD"] / po_df["Ordered Quantity"]
    unit_prices = po_df.set_index("PO Line ID")["Unit Price"].to_dict()
    
    # Process each PO Line ID
    results = []
    
    for po_line_id, group in combined.groupby("PO Line ID"):
        cumulative_gr = 0
        cumulative_ir = 0
        last_cumulative_cost_impact = 0
        unit_price = unit_prices.get(po_line_id, 0)
        
        for _, row in group.iterrows():
            posting_type = row["Posting Type"]
            posting_qty = row["Posting Qty"]
            
            # Update cumulative based on posting type
            if posting_type == "GR":
                cumulative_gr += posting_qty
                # For GR: If Cum GR >= Cum IR, use Cum GR; else use Max(Cum GR, Cum IR)
                if cumulative_gr >= cumulative_ir:
                    reference_cumulative = cumulative_gr
                else:
                    reference_cumulative = max(cumulative_gr, cumulative_ir)
            else:  # IR
                cumulative_ir += posting_qty
                # For IR: If Cum IR >= Cum GR, use Cum IR; else use Max(Cum GR, Cum IR)
                if cumulative_ir >= cumulative_gr:
                    reference_cumulative = cumulative_ir
                else:
                    reference_cumulative = max(cumulative_gr, cumulative_ir)
            
            # Calculate cost impact qty (negative values allowed)
            cost_impact_qty = reference_cumulative - last_cumulative_cost_impact
            cost_impact_amount = round(cost_impact_qty * unit_price, 2)
            
            # Update last cumulative cost impact
            last_cumulative_cost_impact += cost_impact_qty
            
            results.append({
                "PO Line ID": po_line_id,
                "Posting Date": row["Posting Date"],
                "Posting Type": posting_type,
                "Posting Qty": posting_qty,
                "Cost Impact Qty": cost_impact_qty,
                "Cost Impact Amount": cost_impact_amount,
            })
    
    result_df = pd.DataFrame(results)
    print(f"  Generated {len(result_df):,} cost impact records from GR/IR postings")
    
    return result_df


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save the cost impact DataFrame to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"  Saved to: {filepath}")


def main():
    print("=" * 60)
    print("Cost Impact Calculation Script")
    print("=" * 60)
    
    # Load data
    print("\n[1/5] Loading data...")
    po_df, gr_df, ir_df = load_data()
    
    # Classify PO Line Items
    print("\n[2/5] Classifying PO Line Items...")
    simple_po_ids, complex_po_ids = classify_po_line_items(po_df)
    
    # Calculate simple cost impact (Type 1)
    print("\n[3/5] Calculating Type 1 (Simple) cost impact...")
    simple_cost_impact = calculate_simple_cost_impact(gr_df, simple_po_ids)
    
    # Calculate complex cost impact (Type 2)
    print("\n[4/5] Calculating Type 2 (Complex) cost impact...")
    complex_cost_impact = calculate_complex_cost_impact(gr_df, ir_df, complex_po_ids, po_df)
    
    # Combine results
    print("\n[5/5] Saving combined cost impact data...")
    all_cost_impact = pd.concat([simple_cost_impact, complex_cost_impact], ignore_index=True)
    all_cost_impact = all_cost_impact.sort_values(["PO Line ID", "Posting Date"])
    
    # Summary stats
    total_records = len(all_cost_impact)
    total_cost_impact = all_cost_impact["Cost Impact Amount"].sum()
    print(f"  Total records: {total_records:,}")
    print(f"  Total cost impact: ${total_cost_impact:,.2f}")
    
    save_data(all_cost_impact, OUTPUT_FILE)
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
