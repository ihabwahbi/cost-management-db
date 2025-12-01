#!/usr/bin/env python3
"""
Stage 3: Prepare PO Transactions for Import

Maps cost impact data to database schema columns for po_transactions table.

Dependencies: stage2_transform/05_calculate_cost_impact.py must run first
Input: data/intermediate/cost_impact.csv
Output: data/import-ready/po_transactions.csv
"""

import sys
from pathlib import Path

# Add scripts directory to path for config imports
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import pandas as pd  # noqa: E402
from config.column_mappings import PO_TRANSACTIONS_MAPPING  # noqa: E402

# Import Pandera contract for runtime validation (optional dependency)
try:
    from contracts.po_transactions_schema import (  # type: ignore[import-not-found]  # noqa: E402
        PANDERA_AVAILABLE,
        POTransactionsSchema,
    )
except ImportError:
    PANDERA_AVAILABLE = False
    POTransactionsSchema = None  # type: ignore[misc, assignment]

# Paths
PROJECT_ROOT = SCRIPTS_DIR.parent
COST_IMPACT_FILE = PROJECT_ROOT / "data" / "intermediate" / "cost_impact.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "import-ready" / "po_transactions.csv"


def load_data(filepath: Path) -> pd.DataFrame:
    """Load cost impact data."""
    print(f"Loading data from: {filepath}")
    df = pd.read_csv(filepath)
    print(f"  Loaded {len(df):,} rows")
    return df


def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map CSV columns to database column names."""
    print("Mapping columns to database schema...")

    output_df = pd.DataFrame()

    for csv_col, db_col in PO_TRANSACTIONS_MAPPING.items():
        if csv_col in df.columns:
            output_df[db_col] = df[csv_col]
        else:
            print(f"  Warning: Column '{csv_col}' not found in source data")

    # Round numeric columns
    if "cost_impact_qty" in output_df.columns:
        output_df["cost_impact_qty"] = output_df["cost_impact_qty"].round(4)
    if "cost_impact_amount" in output_df.columns:
        output_df["cost_impact_amount"] = output_df["cost_impact_amount"].round(2)
    if "quantity" in output_df.columns:
        output_df["quantity"] = output_df["quantity"].round(4)

    # Add amount column (same as cost_impact_amount for now)
    # This represents the posting amount before cost impact calculation
    output_df["amount"] = output_df["cost_impact_amount"]

    print(f"  Mapped {len(output_df.columns)} columns")
    return output_df


def validate_output(df: pd.DataFrame) -> bool:
    """Validate output using Pandera contract (with fallback to basic checks)."""
    # Basic column checks first (fast fail)
    required = [
        "po_line_id",
        "transaction_type",
        "posting_date",
        "cost_impact_qty",
        "cost_impact_amount",
    ]
    missing = [col for col in required if col not in df.columns]

    if missing:
        print(f"  ERROR: Missing required columns: {missing}")
        return False

    # Check for valid transaction types (always do this check)
    valid_types = {"GR", "IR"}
    actual_types = set(df["transaction_type"].unique())
    invalid_types = actual_types - valid_types
    if invalid_types:
        print(f"  ERROR: Invalid transaction types: {invalid_types}")
        return False

    # Pandera contract validation (if available)
    if PANDERA_AVAILABLE and POTransactionsSchema is not None:
        try:
            POTransactionsSchema.validate(df, lazy=True)
            print("  Pandera contract validation passed")
        except Exception as e:
            print("  ERROR: Pandera contract validation failed:")
            print(f"    {e}")
            return False
    else:
        print("  Warning: Pandera not available, using basic validation only")

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
    print("Stage 3: Prepare PO Transactions for Import")
    print("=" * 60)

    # Check dependency
    if not COST_IMPACT_FILE.exists():
        print(f"ERROR: Dependency not found: {COST_IMPACT_FILE}")
        return False

    print("\n[1/3] Loading data...")
    df = load_data(COST_IMPACT_FILE)

    print("\n[2/3] Mapping columns...")
    output_df = map_columns(df)

    print("\n[3/3] Validating and saving...")
    if not validate_output(output_df):
        return False
    save_data(output_df, OUTPUT_FILE)

    print("\n" + "=" * 60)
    print("Stage 3 Complete: PO Transactions ready for import")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
