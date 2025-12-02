#!/usr/bin/env python3
"""
Stage 3: Prepare SAP Reservations for Import

Maps intermediate columns to database schema columns and extracts
derived fields (PO info, asset info).

Transformations:
1. Map CSV columns to database column names
2. Extract po_number and po_line_number from "Main - PO Line to Peg to Reservation"
3. Extract asset_code and asset_serial_number from "Maximo Asset Num"
4. Convert Plant from float to string for plant_code
5. Keep po_line_item_id as the full PO-Line composite key for relationship

Dependencies: scripts/stage1_clean/13_reservations.py
Input: data/intermediate/reservations.csv
Output: data/import-ready/sap_reservations.csv
"""

import sys
from pathlib import Path

# Add scripts directory to path for config imports
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import pandas as pd  # noqa: E402
from config.column_mappings import (  # noqa: E402
    REQUIRED_COLUMNS,
    SAP_RESERVATIONS_MAPPING,
)

# Paths
PROJECT_ROOT = SCRIPTS_DIR.parent
INPUT_FILE = PROJECT_ROOT / "data" / "intermediate" / "reservations.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "import-ready" / "sap_reservations.csv"


def load_data() -> pd.DataFrame:
    """Load intermediate reservations data."""
    print("Loading intermediate data...")
    df = pd.read_csv(INPUT_FILE)
    initial_count = len(df)
    print(f"  Loaded: {initial_count:,} rows")

    # Filter out rows with null reservation_line_id (empty artifact rows)
    df = df[df["reservation_line_id"].notna()].copy()
    filtered_count = initial_count - len(df)
    if filtered_count > 0:
        print(
            f"  Filtered out {filtered_count:,} empty rows (null reservation_line_id)"
        )

    print(f"  Reservations: {len(df):,} rows")
    return df


def extract_po_info(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract PO number and line number from 'Main - PO Line to Peg to Reservation'.

    Format: "4584632148-1" -> po_number="4584632148", po_line_number=1
    Also keeps the full value as po_line_item_id for relationship lookup.
    """
    print("Extracting PO information...")
    source_col = "Main - PO Line to Peg to Reservation"

    if source_col not in df.columns:
        print(f"  Warning: Column '{source_col}' not found")
        df["po_number"] = pd.NA
        df["po_line_number"] = pd.NA
        df["po_line_item_id"] = pd.NA
        return df

    def extract_parts(val):
        """Extract PO number and line number from composite key."""
        if pd.isna(val) or str(val) == "nan":
            return pd.NA, pd.NA
        val_str = str(val)
        if "-" not in val_str:
            return val_str, pd.NA
        # Split from right on last hyphen (safer if PO number contains hyphens)
        idx = val_str.rfind("-")
        po_num = val_str[:idx]
        line_num = val_str[idx + 1 :]
        try:
            line_int = int(line_num)
            return po_num, line_int
        except ValueError:
            return po_num, pd.NA

    parts = df[source_col].apply(extract_parts)
    df["po_number"] = parts.apply(lambda x: x[0])
    df["po_line_number"] = pd.to_numeric(
        parts.apply(lambda x: x[1]), errors="coerce"
    ).astype("Int64")

    # Keep full value as po_line_item_id for relationship
    df["po_line_item_id"] = df[source_col].where(
        df[source_col].notna() & (df[source_col] != "nan"), pd.NA
    )

    non_null = df["po_number"].notna().sum()
    print(f"  Extracted {non_null:,} PO references (out of {len(df):,} rows)")

    return df


def extract_asset_info(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract asset code and serial number from 'Maximo Asset Num'.

    Format: "XPS-CA|941" -> asset_code="XPS-CA", asset_serial_number="941"

    Note: Some values may not have "|" separator (e.g., "TCS92314Y1795").
    In those cases, the entire value goes to asset_code.
    """
    print("Extracting asset information...")
    source_col = "Maximo Asset Num"

    if source_col not in df.columns:
        print(f"  Warning: Column '{source_col}' not found")
        df["asset_code"] = pd.NA
        df["asset_serial_number"] = pd.NA
        return df

    def extract_asset_parts(val):
        """Extract asset code and serial number from composite value."""
        if pd.isna(val) or str(val) == "nan":
            return pd.NA, pd.NA
        val_str = str(val)
        if "|" in val_str:
            parts = val_str.split("|", 1)  # Split on first "|" only
            return parts[0].strip(), parts[1].strip() if len(parts) > 1 else pd.NA
        else:
            # No separator - put entire value in asset_code
            return val_str, pd.NA

    parts = df[source_col].apply(extract_asset_parts)
    df["asset_code"] = parts.apply(lambda x: x[0])
    df["asset_serial_number"] = parts.apply(lambda x: x[1])

    # Count extractions
    with_separator = df["asset_serial_number"].notna().sum()
    without_separator = (
        df["asset_code"].notna() & df["asset_serial_number"].isna()
    ).sum()
    total_null = df["asset_code"].isna().sum()

    print(f"  With '|' separator: {with_separator:,} rows")
    print(f"  Without separator (asset_code only): {without_separator:,} rows")
    print(f"  Null values: {total_null:,} rows")

    return df


def convert_plant_code(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert Plant from float to string.

    Input: 3606.0 -> Output: "3606"
    """
    print("Converting Plant to string...")
    source_col = "Plant"

    if source_col not in df.columns:
        print(f"  Warning: Column '{source_col}' not found")
        return df

    # Convert float to int to string (removes .0)
    def float_to_str(val):
        if pd.isna(val):
            return pd.NA
        try:
            return str(int(float(val)))
        except (ValueError, TypeError):
            return str(val)

    df[source_col] = df[source_col].apply(float_to_str)

    unique_plants = df[source_col].dropna().unique()
    print(
        f"  Converted {len(unique_plants)} unique plant codes: {sorted(unique_plants)}"
    )

    return df


def clean_numeric_to_string(series: pd.Series) -> pd.Series:
    """Convert numeric series to clean string (remove .0 suffix)."""

    def clean_val(val):
        if pd.isna(val):
            return pd.NA
        val_str = str(val)
        # Remove .0 suffix from float conversion
        if val_str.endswith(".0"):
            return val_str[:-2]
        return val_str

    return series.apply(clean_val)


def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map CSV columns to database column names."""
    print("Mapping columns to database schema...")

    # Build the output dataframe with mapped columns
    output_df = pd.DataFrame()

    # Map columns from SAP_RESERVATIONS_MAPPING
    for csv_col, db_col in SAP_RESERVATIONS_MAPPING.items():
        if csv_col in df.columns:
            output_df[db_col] = df[csv_col]
        else:
            print(f"  Warning: Column '{csv_col}' not found in source data")
            output_df[db_col] = pd.NA

    # Add derived columns (already in df with db names)
    derived_cols = [
        "po_number",
        "po_line_number",
        "po_line_item_id",
        "asset_code",
        "asset_serial_number",
    ]
    for col in derived_cols:
        if col in df.columns:
            output_df[col] = df[col]

    # Clean up data types
    # reservation_number should be clean string (no .0)
    if "reservation_number" in output_df.columns:
        output_df["reservation_number"] = clean_numeric_to_string(
            output_df["reservation_number"]
        )

    # reservation_line_number should be integer
    if "reservation_line_number" in output_df.columns:
        output_df["reservation_line_number"] = pd.to_numeric(
            output_df["reservation_line_number"], errors="coerce"
        ).astype("Int64")

    # po_number should be clean string (no .0)
    if "po_number" in output_df.columns:
        output_df["po_number"] = clean_numeric_to_string(output_df["po_number"])

    # po_line_number should be integer
    if "po_line_number" in output_df.columns:
        output_df["po_line_number"] = pd.to_numeric(
            output_df["po_line_number"], errors="coerce"
        ).astype("Int64")

    print(f"  Mapped {len(output_df.columns)} columns")
    return output_df


def validate_output(df: pd.DataFrame) -> bool:
    """Validate output using required column checks."""
    print("Validating output...")

    required = REQUIRED_COLUMNS.get("sap_reservations", [])
    missing = [col for col in required if col not in df.columns]

    if missing:
        print(f"  ERROR: Missing required columns: {missing}")
        return False

    # Check for nulls in required columns
    for col in required:
        null_count = df[col].isna().sum()
        if null_count > 0:
            print(f"  Warning: {null_count:,} nulls in required column '{col}'")

    # Verify uniqueness of reservation_line_id
    dup_mask = df.duplicated(subset=["reservation_line_id"], keep=False)
    if dup_mask.any():
        dup_count = dup_mask.sum()
        print(f"  ERROR: {dup_count:,} duplicate reservation_line_id values")
        return False
    else:
        print("  reservation_line_id is unique")

    print("  Validation passed")
    return True


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save import-ready DataFrame to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"  Saved to: {filepath}")
    print(f"  Final row count: {len(df):,}")
    print(f"  Columns: {list(df.columns)}")


def main():
    print("=" * 60)
    print("Stage 3: Prepare SAP Reservations for Import")
    print("=" * 60)

    # Check dependencies
    if not INPUT_FILE.exists():
        print(f"ERROR: Dependency not found: {INPUT_FILE}")
        return False

    print("\n[1/6] Loading data...")
    df = load_data()

    print("\n[2/6] Converting plant code...")
    df = convert_plant_code(df)

    print("\n[3/6] Extracting PO information...")
    df = extract_po_info(df)

    print("\n[4/6] Extracting asset information...")
    df = extract_asset_info(df)

    print("\n[5/6] Mapping columns...")
    output_df = map_columns(df)

    print("\n[6/6] Validating and saving...")
    if not validate_output(output_df):
        return False
    save_data(output_df, OUTPUT_FILE)

    # Print summary
    print("\n" + "-" * 40)
    print("Summary:")
    print(f"  Total rows: {len(output_df):,}")
    print(f"  With PO reference: {output_df['po_line_item_id'].notna().sum():,}")
    print(f"  With asset info: {output_df['asset_code'].notna().sum():,}")
    print(f"  With WBS: {output_df['wbs_number'].notna().sum():,}")

    if "reservation_status" in output_df.columns:
        print("\nReservation Status Distribution:")
        print(output_df["reservation_status"].value_counts().to_string())

    print("\n" + "=" * 60)
    print("Stage 3 Complete: SAP Reservations ready for import")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
