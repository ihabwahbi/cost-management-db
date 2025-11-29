#!/usr/bin/env python3
"""
Stage 2: Enrich PO Line Items

Enriches intermediate PO line items with PR Number and Requester
from the PO Details Report.

Dependencies: 01_po_line_items.py must run first
Input: data/intermediate/po_line_items.csv, data/raw/po details report.xlsx
Output: data/intermediate/po_line_items.csv (updated in place)
"""

import sys
from pathlib import Path

import pandas as pd

# Paths
SCRIPTS_DIR = Path(__file__).parent.parent
PROJECT_ROOT = SCRIPTS_DIR.parent
PO_DETAILS_FILE = PROJECT_ROOT / "data" / "raw" / "po details report.xlsx"
PO_LINE_ITEMS_FILE = PROJECT_ROOT / "data" / "intermediate" / "po_line_items.csv"


def load_po_details(filepath: Path) -> pd.DataFrame:
    """Load PO Details Report and prepare for join."""
    print(f"Loading PO Details from: {filepath}")
    df = pd.read_excel(filepath)
    print(f"  Loaded {len(df):,} rows")
    
    # Create PO Line ID to match format
    df['PO Line Item'] = df['PO Line Item'].fillna(0).astype(int)
    df['PO Line ID'] = df['PO Number'].astype(str) + '-' + df['PO Line Item'].astype(str)
    
    return df


def load_po_line_items(filepath: Path) -> pd.DataFrame:
    """Load intermediate PO line items."""
    print(f"Loading PO Line Items from: {filepath}")
    df = pd.read_csv(filepath)
    print(f"  Loaded {len(df):,} rows")
    return df


def extract_enrichment_data(details: pd.DataFrame) -> pd.DataFrame:
    """Extract Requester and PR Number from PO Details."""
    print("Extracting enrichment data...")
    
    enrichment = pd.DataFrame()
    enrichment['PO Line ID'] = details['PO Line ID']
    
    # Requester: from ARIBA shopping cart number : created by (Text)
    enrichment['Requester'] = details['ARIBA shopping cart number : created by (Text)']
    
    # PR Number: Purchase Requisition Number, fallback to ARIBA Shopping cart number
    pr_number = details['Purchase Requisition Number'].copy()
    ariba_number = details['ARIBA Shopping cart number'].copy()
    
    # Convert from float to string (handle scientific notation)
    pr_number = pr_number.apply(lambda x: str(int(x)) if pd.notna(x) else None)
    ariba_number = ariba_number.apply(lambda x: str(x) if pd.notna(x) else None)
    
    enrichment['PR Number'] = pr_number.where(pr_number.notna(), ariba_number)
    
    # Stats
    print(f"  Requester values: {enrichment['Requester'].notna().sum():,}")
    print(f"  PR Number values: {enrichment['PR Number'].notna().sum():,}")
    
    return enrichment


def enrich_data(po_df: pd.DataFrame, enrichment: pd.DataFrame) -> pd.DataFrame:
    """Left join enrichment data to PO line items."""
    print("Enriching PO line items...")
    
    initial_count = len(po_df)
    
    # Left join to preserve all PO line items
    enriched = po_df.merge(
        enrichment[['PO Line ID', 'Requester', 'PR Number']],
        on='PO Line ID',
        how='left'
    )
    
    assert len(enriched) == initial_count, "Row count changed after merge!"
    
    # Set Requester to "M&S Prime" for PR Numbers starting with 4 and 10 digits
    pr_str = enriched['PR Number'].astype(str)
    ms_prime_mask = pr_str.str.match(r'^4\d{9}$', na=False)
    enriched.loc[ms_prime_mask, 'Requester'] = 'M&S Prime'
    print(f"  Set 'M&S Prime' for {ms_prime_mask.sum():,} rows")
    
    # Stats
    print(f"  Rows with Requester: {enriched['Requester'].notna().sum():,}")
    print(f"  Rows with PR Number: {enriched['PR Number'].notna().sum():,}")
    
    return enriched


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save enriched DataFrame to CSV."""
    df.to_csv(filepath, index=False)
    print(f"  Saved to: {filepath}")
    print(f"  Final row count: {len(df):,}")


def main():
    print("=" * 60)
    print("Stage 2: Enrich PO Line Items")
    print("=" * 60)
    
    # Check dependencies
    if not PO_LINE_ITEMS_FILE.exists():
        print(f"ERROR: Dependency not found: {PO_LINE_ITEMS_FILE}")
        print("Run stage1_clean/01_po_line_items.py first")
        return False
    
    if not PO_DETAILS_FILE.exists():
        print(f"ERROR: Source file not found: {PO_DETAILS_FILE}")
        return False
    
    print("\n[1/4] Loading PO Details Report...")
    details = load_po_details(PO_DETAILS_FILE)
    
    print("\n[2/4] Loading PO Line Items...")
    po_df = load_po_line_items(PO_LINE_ITEMS_FILE)
    
    print("\n[3/4] Extracting and joining data...")
    enrichment = extract_enrichment_data(details)
    enriched = enrich_data(po_df, enrichment)
    
    print("\n[4/4] Saving enriched data...")
    save_data(enriched, PO_LINE_ITEMS_FILE)
    
    print("\n" + "=" * 60)
    print("Stage 2 Complete: PO Line Items enriched")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
