#!/usr/bin/env python3
"""
Stage 2: Calculate GRIR Exposures

Calculates GRIR (Goods Receipt/Invoice Receipt variance) for Simple POs
(GLD vendor + K/P/S/V account assignment). GRIR = IR - GR when IR > GR.

This tracks balance sheet exposure from invoices received but not yet
goods-receipted, which will eventually hit the Net Income Statement.

Dependencies: All stage1 scripts + 05_calculate_cost_impact.py must run first
Input: data/intermediate/po_line_items.csv, gr_postings.csv, ir_postings.csv
Output: data/intermediate/grir_exposures.csv
"""

import sys
from pathlib import Path
from datetime import date

# Add scripts directory to path for config imports
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import pandas as pd
from config.column_mappings import (
    SIMPLE_VENDOR_CATEGORY, 
    SIMPLE_ACCOUNT_CATEGORIES,
    GRIR_TIME_BUCKETS,
    GRIR_TIME_BUCKET_MAX,
)

# Paths
PROJECT_ROOT = SCRIPTS_DIR.parent
PO_LINE_ITEMS_FILE = PROJECT_ROOT / "data" / "intermediate" / "po_line_items.csv"
GR_POSTINGS_FILE = PROJECT_ROOT / "data" / "intermediate" / "gr_postings.csv"
IR_POSTINGS_FILE = PROJECT_ROOT / "data" / "intermediate" / "ir_postings.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "intermediate" / "grir_exposures.csv"


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


def get_simple_po_ids(po_df: pd.DataFrame) -> set:
    """
    Get PO Line IDs for Simple POs (GLD + K/P/S/V) that are NOT closed.
    These are the POs where we track GRIR exposure.
    
    Closed POs are excluded - no exposure if PO is already closed.
    """
    is_gld = po_df["Main Vendor SLB Vendor Category"] == SIMPLE_VENDOR_CATEGORY
    is_valid_cat = po_df["PO Account Assignment Category"].isin(SIMPLE_ACCOUNT_CATEGORIES)
    is_not_closed = po_df["PO Receipt Status"] != "CLOSED PO"
    
    simple_mask = is_gld & is_valid_cat & is_not_closed
    simple_po_ids = set(po_df.loc[simple_mask, "PO Line ID"])
    
    # Count how many were excluded due to closed status
    closed_simple = (is_gld & is_valid_cat & ~is_not_closed).sum()
    
    print(f"  Simple POs (GLD + K/P/S/V): {len(simple_po_ids):,} open PO Line IDs")
    print(f"  Excluded (CLOSED PO): {closed_simple:,} PO Line IDs")
    return simple_po_ids


def get_unit_prices(po_df: pd.DataFrame) -> dict:
    """Calculate unit price for each PO Line ID."""
    po_df = po_df.copy()
    po_df["Unit Price"] = po_df["Purchase Value USD"] / po_df["Ordered Quantity"]
    return po_df.set_index("PO Line ID")["Unit Price"].to_dict()


def categorize_time_bucket(days: int) -> str:
    """Categorize days into time bucket."""
    for threshold, bucket in sorted(GRIR_TIME_BUCKETS.items()):
        if days <= threshold:
            return bucket
    return GRIR_TIME_BUCKET_MAX


def calculate_grir_exposures(
    gr_df: pd.DataFrame, 
    ir_df: pd.DataFrame, 
    simple_po_ids: set,
    unit_prices: dict,
    snapshot_date: date
) -> pd.DataFrame:
    """
    Calculate GRIR exposure for each Simple PO Line ID.
    
    GRIR = IR - GR (when IR > GR)
    
    Logic:
    1. For each PO Line ID, combine GR and IR postings chronologically
    2. Track cumulative GR and IR
    3. Find first date when IR exceeded GR (first_exposure_date)
    4. Calculate current GRIR qty/value
    5. Calculate duration and time bucket
    """
    # Filter for simple PO Line IDs
    simple_gr = gr_df[gr_df["PO Line ID"].isin(simple_po_ids)].copy()
    simple_ir = ir_df[ir_df["PO Line ID"].isin(simple_po_ids)].copy()
    
    print(f"  Simple GR postings: {len(simple_gr):,} rows")
    print(f"  Simple IR postings: {len(simple_ir):,} rows")
    
    # Prepare GR postings
    simple_gr = simple_gr.rename(columns={
        "GR Posting Date": "Posting Date",
        "GR Effective Quantity": "Posting Qty",
    })
    simple_gr["Posting Type"] = "GR"
    simple_gr = simple_gr[["PO Line ID", "Posting Date", "Posting Type", "Posting Qty"]]
    
    # Prepare IR postings
    simple_ir = simple_ir.rename(columns={
        "Invoice Posting Date": "Posting Date",
        "IR Effective Quantity": "Posting Qty",
    })
    simple_ir["Posting Type"] = "IR"
    simple_ir = simple_ir[["PO Line ID", "Posting Date", "Posting Type", "Posting Qty"]]
    
    # Combine and sort chronologically
    combined = pd.concat([simple_gr, simple_ir], ignore_index=True)
    combined["Posting Date"] = pd.to_datetime(combined["Posting Date"])
    combined = combined.sort_values(["PO Line ID", "Posting Date", "Posting Type"])
    
    # Process each PO Line ID
    results = []
    
    for po_line_id, group in combined.groupby("PO Line ID"):
        cumulative_gr = 0.0
        cumulative_ir = 0.0
        first_exposure_date = None
        
        # Walk through postings chronologically to find first exposure
        for _, row in group.iterrows():
            posting_type = row["Posting Type"]
            posting_qty = float(row["Posting Qty"])
            posting_date = row["Posting Date"]
            
            if posting_type == "GR":
                cumulative_gr += posting_qty
            else:  # IR
                cumulative_ir += posting_qty
            
            # Track first date when IR > GR
            if cumulative_ir > cumulative_gr and first_exposure_date is None:
                first_exposure_date = posting_date
            
            # Reset first_exposure_date if GR catches up
            if cumulative_gr >= cumulative_ir:
                first_exposure_date = None
        
        # Calculate final GRIR
        grir_qty = cumulative_ir - cumulative_gr
        
        # Only record if there's a positive GRIR (exposure)
        if grir_qty > 0:
            unit_price = unit_prices.get(po_line_id, 0)
            grir_value = round(grir_qty * unit_price, 2)
            
            # Calculate duration
            if first_exposure_date is not None:
                days_open = (pd.Timestamp(snapshot_date) - first_exposure_date).days
            else:
                days_open = 0
            
            time_bucket = categorize_time_bucket(days_open)
            
            results.append({
                "PO Line ID": po_line_id,
                "GRIR Qty": round(grir_qty, 4),
                "GRIR Value": grir_value,
                "First Exposure Date": first_exposure_date.strftime("%Y-%m-%d") if first_exposure_date else None,
                "Days Open": days_open,
                "Time Bucket": time_bucket,
                "Snapshot Date": snapshot_date.strftime("%Y-%m-%d"),
            })
    
    result_df = pd.DataFrame(results)
    print(f"  Generated {len(result_df):,} GRIR exposure records")
    
    return result_df


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save GRIR exposures DataFrame to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"  Saved to: {filepath}")
    print(f"  Total records: {len(df):,}")
    if len(df) > 0:
        print(f"  Total GRIR value: ${df['GRIR Value'].sum():,.2f}")
        print(f"\n  Time bucket breakdown:")
        for bucket, count in df["Time Bucket"].value_counts().items():
            bucket_value = df[df["Time Bucket"] == bucket]["GRIR Value"].sum()
            print(f"    {bucket}: {count:,} POs (${bucket_value:,.2f})")


def main():
    print("=" * 60)
    print("Stage 2: Calculate GRIR Exposures")
    print("=" * 60)
    
    # Check dependencies
    for f in [PO_LINE_ITEMS_FILE, GR_POSTINGS_FILE, IR_POSTINGS_FILE]:
        if not f.exists():
            print(f"ERROR: Dependency not found: {f}")
            print("Run all stage1 scripts first")
            return False
    
    print("\n[1/4] Loading data...")
    po_df, gr_df, ir_df = load_data()
    
    print("\n[2/4] Identifying Simple POs...")
    simple_po_ids = get_simple_po_ids(po_df)
    unit_prices = get_unit_prices(po_df)
    
    print("\n[3/4] Calculating GRIR exposures...")
    snapshot_date = date.today()
    grir_df = calculate_grir_exposures(
        gr_df, ir_df, simple_po_ids, unit_prices, snapshot_date
    )
    
    print("\n[4/4] Saving results...")
    save_data(grir_df, OUTPUT_FILE)
    
    print("\n" + "=" * 60)
    print("Stage 2 Complete: GRIR Exposures calculated")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
