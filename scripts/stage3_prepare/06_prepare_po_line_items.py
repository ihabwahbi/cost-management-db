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

import pandas as pd  # noqa: E402
from config.column_mappings import PO_LINE_ITEMS_MAPPING  # noqa: E402

# Import Pandera contract for runtime validation (optional dependency)
try:
    from contracts.po_line_items_schema import (  # type: ignore[import-not-found]  # noqa: E402
        PANDERA_AVAILABLE,
        POLineItemsSchema,
    )
except ImportError:
    PANDERA_AVAILABLE = False
    POLineItemsSchema = None  # type: ignore[misc, assignment]

# Paths
PROJECT_ROOT = SCRIPTS_DIR.parent
PO_LINE_ITEMS_FILE = PROJECT_ROOT / "data" / "intermediate" / "po_line_items.csv"
COST_IMPACT_FILE = PROJECT_ROOT / "data" / "intermediate" / "cost_impact.csv"
WBS_DETAILS_FILE = PROJECT_ROOT / "data" / "import-ready" / "wbs_details.csv"
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
    Calculate open_po_qty and open_po_value based on cost impact.

    Logic:
    - If raw status is CLOSED PO: trust it, set open_po_qty and open_po_value to 0
    - Otherwise: calculate open values from ordered - cost impact
    """
    print("Calculating open PO values...")

    # Aggregate cost impact by PO Line ID
    cost_agg = (
        cost_df.groupby("PO Line ID")
        .agg({"Cost Impact Qty": "sum", "Cost Impact Amount": "sum"})
        .reset_index()
    )
    cost_agg.columns = [  # type: ignore[assignment]
        "PO Line ID",
        "Total Cost Impact Qty",
        "Total Cost Impact Amount",
    ]

    # Merge with PO line items
    po_df = po_df.merge(cost_agg, on="PO Line ID", how="left")

    # Fill NaN with 0 for POs with no cost impact yet
    po_df["Total Cost Impact Qty"] = po_df["Total Cost Impact Qty"].fillna(0)
    po_df["Total Cost Impact Amount"] = po_df["Total Cost Impact Amount"].fillna(0)

    # Identify POs already closed in raw data - trust this, don't recalculate
    already_closed = po_df["PO Receipt Status"] == "CLOSED PO"
    not_closed = ~already_closed

    # For already closed POs: set open values to 0
    po_df.loc[already_closed, "open_po_qty"] = 0
    po_df.loc[already_closed, "open_po_value"] = 0

    # For non-closed POs: calculate open values
    po_df.loc[not_closed, "open_po_qty"] = (
        po_df.loc[not_closed, "Ordered Quantity"]
        - po_df.loc[not_closed, "Total Cost Impact Qty"]
    )
    po_df.loc[not_closed, "open_po_value"] = (
        po_df.loc[not_closed, "Purchase Value USD"]
        - po_df.loc[not_closed, "Total Cost Impact Amount"]
    )

    print(f"  Closed POs (from raw status): {already_closed.sum():,}")
    print(f"  Open POs: {not_closed.sum():,}")

    # Drop intermediate columns
    po_df = po_df.drop(columns=["Total Cost Impact Qty", "Total Cost Impact Amount"])

    return po_df


def clean_numeric_string(series: pd.Series) -> pd.Series:
    """
    Clean numeric values that should be strings.
    Removes .0 suffix from floats (e.g., '4002084960.0' -> '4002084960').
    """
    return series.apply(
        lambda x: str(int(x)) if pd.notna(x) and isinstance(x, float) else x
    )


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

    # Clean numeric columns that should be strings (remove .0 suffix)
    string_columns = ["po_number", "plant_code", "pr_number", "pr_line"]
    for col in string_columns:
        if col in output_df.columns:
            output_df[col] = clean_numeric_string(output_df[col])

    # Add calculated columns (already have db names)
    if "open_po_qty" in po_df.columns:
        output_df["open_po_qty"] = po_df["open_po_qty"].round(4)
    if "open_po_value" in po_df.columns:
        output_df["open_po_value"] = po_df["open_po_value"].round(2)

    # Set fmt_po = True when vendor category is OPS
    vendor_category_col = "Main Vendor SLB Vendor Category"
    if vendor_category_col in po_df.columns:
        is_ops_vendor = po_df[vendor_category_col] == "OPS"
        output_df["fmt_po"] = is_ops_vendor
    else:
        output_df["fmt_po"] = False

    print(f"  Mapped {len(output_df.columns)} columns")
    return output_df


def calculate_wbs_validated(df: pd.DataFrame) -> pd.DataFrame:
    """
    Set wbs_validated = True if wbs_number exists in wbs_details.

    This enables data quality reporting for POs with invalid/unknown WBS references
    (e.g., typos, capex WBS tracked in separate systems).
    """
    print("Calculating WBS validation status...")

    if not WBS_DETAILS_FILE.exists():
        print(f"  Warning: WBS details file not found: {WBS_DETAILS_FILE}")
        print("  Setting all wbs_validated = False")
        df["wbs_validated"] = False
        return df

    # Load valid WBS numbers from wbs_details
    wbs_df = pd.read_csv(WBS_DETAILS_FILE, usecols=["wbs_number"])
    valid_wbs = set(wbs_df["wbs_number"].dropna().unique())
    print(f"  Loaded {len(valid_wbs):,} valid WBS numbers from wbs_details")

    # Calculate validation status
    # wbs_validated = True if wbs_number is not null AND exists in wbs_details
    has_wbs = df["wbs_number"].notna()
    wbs_exists = df["wbs_number"].isin(valid_wbs)
    df["wbs_validated"] = has_wbs & wbs_exists

    # Report stats
    total_with_wbs = has_wbs.sum()
    validated_count = df["wbs_validated"].sum()
    unvalidated_count = total_with_wbs - validated_count

    print(f"  POs with WBS: {total_with_wbs:,}")
    print(f"  WBS validated: {validated_count:,}")
    print(f"  WBS unvalidated (orphan): {unvalidated_count:,}")

    return df


def calculate_is_capex(df: pd.DataFrame) -> pd.DataFrame:
    """
    Set is_capex = True if WBS indicates a capitalized PO.

    CapEx POs (C.* WBS prefix) don't hit P&L - they're capitalized assets.
    Examples: C.FT*, C.NF*, C.LF*, etc.
    This flag enables reports to filter out CapEx when analyzing OpEx cost impact.
    """
    print("Calculating CapEx flag...")

    # CapEx WBS pattern: starts with 'C.' (e.g., C.FT000928, C.NF001234)
    df["is_capex"] = df["wbs_number"].str.startswith("C.", na=False)

    capex_count = df["is_capex"].sum()
    capex_value = df.loc[df["is_capex"], "po_value_usd"].sum()

    print(f"  CapEx POs (C.* WBS): {capex_count:,} rows, ${capex_value:,.0f} value")
    print(f"  OpEx POs: {len(df) - capex_count:,} rows")

    return df


def validate_output(df: pd.DataFrame) -> bool:
    """Validate output using Pandera contract (with fallback to basic checks)."""
    # Basic column checks first (fast fail)
    required = [
        "po_line_id",
        "po_number",
        "line_item_number",
        "ordered_qty",
        "po_value_usd",
    ]
    missing = [col for col in required if col not in df.columns]

    if missing:
        print(f"  ERROR: Missing required columns: {missing}")
        return False

    # Pandera contract validation (if available)
    if PANDERA_AVAILABLE and POLineItemsSchema is not None:
        try:
            POLineItemsSchema.validate(df, lazy=True)
            print("  Pandera contract validation passed")
        except Exception as e:
            print("  ERROR: Pandera contract validation failed:")
            print(f"    {e}")
            return False
    else:
        print("  Warning: Pandera not available, using basic validation only")
        # Fallback: check for nulls in required columns
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

    print("\n[1/6] Loading data...")
    po_df, cost_df = load_data()

    print("\n[2/6] Calculating open values...")
    po_df = calculate_open_values(po_df, cost_df)

    print("\n[3/6] Mapping columns...")
    output_df = map_columns(po_df)

    print("\n[4/6] Calculating WBS validation...")
    output_df = calculate_wbs_validated(output_df)

    print("\n[5/6] Calculating CapEx flag...")
    output_df = calculate_is_capex(output_df)

    print("\n[6/6] Validating and saving...")
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
