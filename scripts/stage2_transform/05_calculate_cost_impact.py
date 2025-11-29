#!/usr/bin/env python3
"""
Stage 2: Calculate Cost Impact

Calculates cost impact from GR and IR postings for each PO Line Item.
Two types: Simple (GLD + K/P/S/V) uses GR only, Complex uses GR/IR logic.

Dependencies: All stage1 scripts must run first
Input: data/intermediate/po_line_items.csv, gr_postings.csv, ir_postings.csv
Output: data/intermediate/cost_impact.csv
"""

import sys
from pathlib import Path

# Add scripts directory to path for config imports
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import pandas as pd
from config.column_mappings import SIMPLE_VENDOR_CATEGORY, SIMPLE_ACCOUNT_CATEGORIES

# Paths
PROJECT_ROOT = SCRIPTS_DIR.parent
PO_LINE_ITEMS_FILE = PROJECT_ROOT / "data" / "intermediate" / "po_line_items.csv"
GR_POSTINGS_FILE = PROJECT_ROOT / "data" / "intermediate" / "gr_postings.csv"
IR_POSTINGS_FILE = PROJECT_ROOT / "data" / "intermediate" / "ir_postings.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "intermediate" / "cost_impact.csv"


def load_data():
    """Load all required data files."""
    print("Loading data files...")
    
    po_df = pd.read_csv(PO_LINE_ITEMS_FILE)
    print(f"  PO Line Items: {len(po_df):,} rows")
    
    gr_df = pd.read_csv(GR_POSTINGS_FILE)
    print(f"  GR Postings: {len(gr_df):,} rows")
    
    ir_df = pd.read_csv(IR_POSTINGS_FILE)
    print(f"  IR Postings: {len(ir_df):,} rows")
    
    return po_df, gr_df, ir_df


def classify_po_line_items(po_df: pd.DataFrame) -> tuple:
    """
    Classify PO Line Items into simple (Type 1) and complex (Type 2).
    
    Type 1 (Simple): Vendor Category = GLD AND Account Category IN (K, P, S, V)
    Type 2 (Complex): All others
    """
    is_gld = po_df["Main Vendor SLB Vendor Category"] == SIMPLE_VENDOR_CATEGORY
    is_valid_cat = po_df["PO Account Assignment Category"].isin(SIMPLE_ACCOUNT_CATEGORIES)
    
    simple_mask = is_gld & is_valid_cat
    
    simple_po_ids = set(po_df.loc[simple_mask, "PO Line ID"])
    complex_po_ids = set(po_df.loc[~simple_mask, "PO Line ID"])
    
    print(f"  Type 1 (Simple): {len(simple_po_ids):,} PO Line IDs")
    print(f"  Type 2 (Complex): {len(complex_po_ids):,} PO Line IDs")
    
    return simple_po_ids, complex_po_ids


def calculate_simple_cost_impact(gr_df: pd.DataFrame, simple_po_ids: set) -> pd.DataFrame:
    """
    Type 1: Cost impact = GR postings only (IR ignored).
    """
    simple_gr = gr_df[gr_df["PO Line ID"].isin(simple_po_ids)].copy()
    
    result = pd.DataFrame({
        "PO Line ID": simple_gr["PO Line ID"],
        "Posting Date": simple_gr["GR Posting Date"],
        "Posting Type": "GR",
        "Posting Qty": simple_gr["GR Effective Quantity"],
        "Cost Impact Qty": simple_gr["GR Effective Quantity"],
        "Cost Impact Amount": simple_gr["GR Amount"],
    })
    
    print(f"  Generated {len(result):,} simple cost impact records")
    return result


def calculate_complex_cost_impact(gr_df: pd.DataFrame, ir_df: pd.DataFrame, 
                                   complex_po_ids: set, po_df: pd.DataFrame) -> pd.DataFrame:
    """
    Type 2: Cost impact based on GR/IR chronological processing.
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
    
    # Combine and sort
    combined = pd.concat([complex_gr, complex_ir], ignore_index=True)
    combined["Posting Date"] = pd.to_datetime(combined["Posting Date"])
    combined = combined.sort_values(["PO Line ID", "Posting Date", "Posting Type"])
    
    # Get unit prices
    po_df["Unit Price"] = po_df["Purchase Value USD"] / po_df["Ordered Quantity"]
    unit_prices = po_df.set_index("PO Line ID")["Unit Price"].to_dict()
    
    # Process each PO Line ID
    results = []
    
    for po_line_id, group in combined.groupby("PO Line ID"):
        cumulative_gr = 0
        cumulative_ir = 0
        last_cumulative = 0
        unit_price = unit_prices.get(po_line_id, 0)
        
        for _, row in group.iterrows():
            posting_type = row["Posting Type"]
            posting_qty = row["Posting Qty"]
            
            if posting_type == "GR":
                cumulative_gr += posting_qty
                reference = cumulative_gr if cumulative_gr >= cumulative_ir else max(cumulative_gr, cumulative_ir)
            else:
                cumulative_ir += posting_qty
                reference = cumulative_ir if cumulative_ir >= cumulative_gr else max(cumulative_gr, cumulative_ir)
            
            cost_impact_qty = reference - last_cumulative
            cost_impact_amount = round(cost_impact_qty * unit_price, 2)
            last_cumulative += cost_impact_qty
            
            results.append({
                "PO Line ID": po_line_id,
                "Posting Date": row["Posting Date"],
                "Posting Type": posting_type,
                "Posting Qty": posting_qty,
                "Cost Impact Qty": cost_impact_qty,
                "Cost Impact Amount": cost_impact_amount,
            })
    
    result_df = pd.DataFrame(results)
    print(f"  Generated {len(result_df):,} complex cost impact records")
    return result_df


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save cost impact DataFrame to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"  Saved to: {filepath}")
    print(f"  Total records: {len(df):,}")
    print(f"  Total cost impact: ${df['Cost Impact Amount'].sum():,.2f}")


def main():
    print("=" * 60)
    print("Stage 2: Calculate Cost Impact")
    print("=" * 60)
    
    # Check dependencies
    for f in [PO_LINE_ITEMS_FILE, GR_POSTINGS_FILE, IR_POSTINGS_FILE]:
        if not f.exists():
            print(f"ERROR: Dependency not found: {f}")
            print("Run all stage1 scripts first")
            return False
    
    print("\n[1/4] Loading data...")
    po_df, gr_df, ir_df = load_data()
    
    print("\n[2/4] Classifying PO Line Items...")
    simple_po_ids, complex_po_ids = classify_po_line_items(po_df)
    
    print("\n[3/4] Calculating cost impact...")
    print("  Processing Type 1 (Simple)...")
    simple_impact = calculate_simple_cost_impact(gr_df, simple_po_ids)
    
    print("  Processing Type 2 (Complex)...")
    complex_impact = calculate_complex_cost_impact(gr_df, ir_df, complex_po_ids, po_df)
    
    print("\n[4/4] Saving results...")
    all_impact = pd.concat([simple_impact, complex_impact], ignore_index=True)
    all_impact = all_impact.sort_values(["PO Line ID", "Posting Date"])
    save_data(all_impact, OUTPUT_FILE)
    
    print("\n" + "=" * 60)
    print("Stage 2 Complete: Cost Impact calculated")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
