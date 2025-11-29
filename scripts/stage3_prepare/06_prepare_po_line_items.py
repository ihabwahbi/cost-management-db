#!/usr/bin/env python3
"""
Stage 3: Prepare PO Line Items for Import

Maps intermediate columns to database schema columns and calculates
derived fields (open_po_qty, open_po_value).

Dependencies: All stage1 and stage2 scripts must run first
Input: data/intermediate/po_line_items.csv, data/intermediate/cost_impact.csv
Output: data/import-ready/po_line_items.csv
"""

import sys
from pathlib import Path

# Add scripts directory to path for config imports
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import pandas as pd
from config.column_mappings import PO_LINE_ITEMS_MAPPING

# Paths
PROJECT_ROOT = SCRIPTS_DIR.parent
PO_LINE_ITEMS_FILE = PROJECT_ROOT / "data" / "intermediate" / "po_line_items.csv"
COST_IMPACT_FILE = PROJECT_ROOT / "data" / "intermediate" / "cost_impact.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "import-ready" / "po_line_items.csv"


def load_data():
    """Load intermediate data files."""
    print("Loading intermediate data...")
    
    po_df = pd.read_csv(PO_LINE_ITEMS_FILE)
    print(f"  PO Line Items: {len(po_df):,} rows")
    
    cost_df = pd.read_csv(COST_IMPACT_FILE)
    print(f"  Cost Impact: {len(cost_df):,} rows")
    
    return po_df, cost_df


def calculate_open_values(po_df: pd.DataFrame, cost_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate open_po_qty and open_po_value.
    
    open_po_qty = ordered_qty - SUM(cost_impact_qty)
    open_po_value = po_value_usd - SUM(cost_impact_amount)
    
    For closed POs (PO Receipt Status = 'Closed'), force to 0.
    """
    print("Calculating open PO values...")
    
    # Aggregate cost impact by PO Line ID
    cost_agg = cost_df.groupby("PO Line ID").agg({
        "Cost Impact Qty": "sum",
        "Cost Impact Amount": "sum"
    }).reset_index()
    cost_agg.columns = ["PO Line ID", "Total Cost Impact Qty", "Total Cost Impact Amount"]
    
    # Merge with PO line items
    po_df = po_df.merge(cost_agg, on="PO Line ID", how="left")
    
    # Fill NaN with 0 for POs with no cost impact yet
    po_df["Total Cost Impact Qty"] = po_df["Total Cost Impact Qty"].fillna(0)
    po_df["Total Cost Impact Amount"] = po_df["Total Cost Impact Amount"].fillna(0)
    
    # Calculate open values
    po_df["open_po_qty"] = po_df["Ordered Quantity"] - po_df["Total Cost Impact Qty"]
    po_df["open_po_value"] = po_df["Purchase Value USD"] - po_df["Total Cost Impact Amount"]
    
    # Force to 0 for closed POs
    closed_mask = po_df["PO Receipt Status"] == "Closed"
    po_df.loc[closed_mask, "open_po_qty"] = 0
    po_df.loc[closed_mask, "open_po_value"] = 0
    
    print(f"  POs with open value > 0: {(po_df['open_po_value'] > 0).sum():,}")
    print(f"  Closed POs (forced to 0): {closed_mask.sum():,}")
    
    # Drop intermediate columns
    po_df = po_df.drop(columns=["Total Cost Impact Qty", "Total Cost Impact Amount"])
    
    return po_df


def map_columns(po_df: pd.DataFrame) -> pd.DataFrame:
    """Map CSV columns to database column names."""
    print("Mapping columns to database schema...")
    
    # Build the output dataframe with mapped columns
    output_df = pd.DataFrame()
    
    for csv_col, db_col in PO_LINE_ITEMS_MAPPING.items():
        if csv_col in po_df.columns:
            output_df[db_col] = po_df[csv_col]
        else:
            print(f"  Warning: Column '{csv_col}' not found in source data")
    
    # Add calculated columns (already have db names)
    if "open_po_qty" in po_df.columns:
        output_df["open_po_qty"] = po_df["open_po_qty"].round(4)
    if "open_po_value" in po_df.columns:
        output_df["open_po_value"] = po_df["open_po_value"].round(2)
    
    # Add default for fmt_po (boolean)
    output_df["fmt_po"] = False
    
    print(f"  Mapped {len(output_df.columns)} columns")
    return output_df


def validate_output(df: pd.DataFrame) -> bool:
    """Validate required columns are present."""
    required = ["po_line_id", "po_number", "line_item_number", "ordered_qty", "po_value_usd"]
    missing = [col for col in required if col not in df.columns]
    
    if missing:
        print(f"  ERROR: Missing required columns: {missing}")
        return False
    
    # Check for nulls in required columns
    for col in required:
        null_count = df[col].isna().sum()
        if null_count > 0:
            print(f"  Warning: {null_count:,} nulls in required column '{col}'")
    
    print("  Validation passed")
    return True


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save import-ready DataFrame to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"  Saved to: {filepath}")
    print(f"  Final row count: {len(df):,}")
    print(f"  Columns: {len(df.columns)}")


def main():
    print("=" * 60)
    print("Stage 3: Prepare PO Line Items for Import")
    print("=" * 60)
    
    # Check dependencies
    if not PO_LINE_ITEMS_FILE.exists():
        print(f"ERROR: Dependency not found: {PO_LINE_ITEMS_FILE}")
        return False
    if not COST_IMPACT_FILE.exists():
        print(f"ERROR: Dependency not found: {COST_IMPACT_FILE}")
        return False
    
    print("\n[1/4] Loading data...")
    po_df, cost_df = load_data()
    
    print("\n[2/4] Calculating open values...")
    po_df = calculate_open_values(po_df, cost_df)
    
    print("\n[3/4] Mapping columns...")
    output_df = map_columns(po_df)
    
    print("\n[4/4] Validating and saving...")
    if not validate_output(output_df):
        return False
    save_data(output_df, OUTPUT_FILE)
    
    print("\n" + "=" * 60)
    print("Stage 3 Complete: PO Line Items ready for import")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
