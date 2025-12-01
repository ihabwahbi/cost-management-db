#!/usr/bin/env python3
"""
Stage 1: Clean Reservations

Reads raw reservations Excel file and performs:
1. Removes rows where both business line columns (Profit Center and Cost Center)
   have matching values of WCM, WCF, or WCD (internal transfers/overhead).
2. Splits "Reservation -Line" column into components:
   - reservation_line_id: Original combined key (e.g., "6086214878-1")
   - reservation_number: The reservation part (e.g., "6086214878")
   - reservation_line_number: The line number as integer (e.g., 1)
3. Normalizes PO Line IDs to match po_line_items format:
   - Strips leading zeros from line numbers (e.g., "4584632148-00001" -> "4584632148-1")
   - Cleans PO numbers (removes .0 suffix from float conversion)

Dependencies: None (independent stage 1 script)
Input: data/raw/reservations/Data Table - Open Reservation - *.xlsx
Output: data/intermediate/reservations.csv
"""

import sys
from pathlib import Path

# Add scripts directory to path for config imports
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import pandas as pd  # noqa: E402

# Paths
PROJECT_ROOT = SCRIPTS_DIR.parent
INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "reservations"
    / "Data Table - Open Reservation - Supply Element Availability Status (1).xlsx"
)
OUTPUT_FILE = PROJECT_ROOT / "data" / "intermediate" / "reservations.csv"

# Business lines to exclude when both columns match
EXCLUDED_MATCHING_BUSINESS_LINES = {"WCM", "WCF", "WCD"}


def load_data(filepath: Path) -> pd.DataFrame:
    """Load the raw Excel file."""
    print(f"Loading data from: {filepath.name}")
    df = pd.read_excel(filepath)
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
    return df


def split_reservation_line_id(df: pd.DataFrame) -> pd.DataFrame:
    """
    Split 'Reservation -Line' column into components.

    Input format: "6086214878-1" (reservation_number-line_number)

    Creates:
    - reservation_line_id: Original combined value (for lookups/traceability)
    - reservation_number: The reservation part (for grouping)
    - reservation_line_number: The line number as integer (for sorting)
    """
    source_col = "Reservation -Line"

    # Keep original as reservation_line_id
    df["reservation_line_id"] = df[source_col].astype(str)

    # Split from right on last hyphen (safer if reservation number contains hyphens)
    def extract_parts(val):
        if pd.isna(val) or val == "nan":
            return pd.NA, pd.NA
        val_str = str(val)
        if "-" in val_str:
            idx = val_str.rfind("-")
            return val_str[:idx], val_str[idx + 1 :]
        return val_str, pd.NA

    parts = df[source_col].apply(extract_parts)
    df["reservation_number"] = parts.apply(lambda x: x[0]).astype(
        "string"
    )  # Keep as string
    df["reservation_line_number"] = pd.to_numeric(
        parts.apply(lambda x: x[1]), errors="coerce"
    ).astype("Int64")  # Nullable integer type

    # Log results
    valid_splits = df["reservation_line_number"].notna().sum()
    print(f"  Split {valid_splits:,} reservation IDs into components")

    # Handle nulls
    null_count = df["reservation_line_number"].isna().sum()
    if null_count > 0:
        print(f"  Warning: {null_count:,} rows could not be split (null source)")

    return df


def normalize_po_line_ids(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize PO Line IDs to match po_line_items format.

    Reservations format: "4584632148-00001" (5-digit zero-padded line number)
    PO Line Items format: "4581850069-1" (no padding)

    This ensures proper joins between sap_reservations and po_line_items tables.
    """
    po_line_col = "Main - PO Line to Peg to Reservation"
    po_num_col = "Main - PO to Peg to Reservation"

    def normalize_po_line_id(val):
        """Strip leading zeros from line number part of PO Line ID."""
        if pd.isna(val) or str(val) == "nan":
            return pd.NA
        val_str = str(val)
        if "-" not in val_str:
            return val_str
        # Split from right on last hyphen
        idx = val_str.rfind("-")
        po_num = val_str[:idx]
        line_num = val_str[idx + 1 :]
        # Convert line number to int to strip leading zeros
        try:
            line_int = int(line_num)
            return f"{po_num}-{line_int}"
        except ValueError:
            return val_str  # Return as-is if line number isn't numeric

    def clean_po_number(val):
        """Remove .0 suffix from PO numbers (artifact of float conversion)."""
        if pd.isna(val) or str(val) == "nan":
            return pd.NA
        val_str = str(val)
        if val_str.endswith(".0"):
            return val_str[:-2]
        return val_str

    # Normalize PO Line ID column
    if po_line_col in df.columns:
        original_non_null = df[po_line_col].notna().sum()
        df[po_line_col] = df[po_line_col].apply(normalize_po_line_id)
        print(f"  Normalized {original_non_null:,} PO Line IDs (stripped zero-padding)")

    # Clean PO Number column
    if po_num_col in df.columns:
        original_non_null = df[po_num_col].notna().sum()
        df[po_num_col] = df[po_num_col].apply(clean_po_number)
        print(f"  Cleaned {original_non_null:,} PO Numbers (removed .0 suffix)")

    return df


def filter_matching_business_lines(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove rows where both Business Line columns have the same value
    AND that value is one of WCM, WCF, or WCD.

    These represent internal transfers/overhead allocations.
    """
    initial_count = len(df)

    # Normalize columns (strip whitespace, uppercase) while preserving NaN
    # Using .str accessor directly preserves NaN values (won't compare equal)
    pc = df["Business Line by Profit Center"].astype("string").str.strip().str.upper()
    cc = df["Business Line - By Cost Center"].astype("string").str.strip().str.upper()

    # Identify rows to exclude: both columns match AND value is in target set
    exclude_mask = (pc == cc) & pc.isin(EXCLUDED_MATCHING_BUSINESS_LINES)

    # Keep rows that DON'T match the exclusion criteria
    df_filtered = df[~exclude_mask].copy()

    removed_count = initial_count - len(df_filtered)
    bl_list = ", ".join(sorted(EXCLUDED_MATCHING_BUSINESS_LINES))
    print(f"  Removed {removed_count:,} rows with matching Business Lines ({bl_list})")

    # Log breakdown of removed rows
    if removed_count > 0:
        for bl in sorted(EXCLUDED_MATCHING_BUSINESS_LINES):
            bl_count = ((pc == bl) & (cc == bl)).sum()
            if bl_count > 0:
                print(f"    - {bl}: {bl_count:,} rows")

    return df_filtered


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save the cleaned DataFrame to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"  Saved to: {filepath.name}")
    print(f"  Final row count: {len(df):,}")


def main():
    print("=" * 60)
    print("Stage 1: Clean Reservations")
    print("=" * 60)

    print("\n[1/5] Loading data...")
    df = load_data(INPUT_FILE)

    print("\n[2/5] Filtering matching business lines...")
    df = filter_matching_business_lines(df)

    print("\n[3/5] Splitting reservation IDs...")
    df = split_reservation_line_id(df)

    print("\n[4/5] Normalizing PO Line IDs...")
    df = normalize_po_line_ids(df)

    print("\n[5/5] Saving output...")
    save_data(df, OUTPUT_FILE)

    print("\n" + "=" * 60)
    print("Stage 1 Complete: Reservations cleaned")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
