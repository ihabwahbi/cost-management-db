#!/usr/bin/env python3
"""
Stage 2: Enrich PO Line Items

Enriches intermediate PO line items with PR Number and Requester
from the PO Details Report.

Dependencies: 01_po_line_items.py must run first
Input: data/intermediate/po_line_items.csv, data/raw/po details report.xlsx
Output: data/intermediate/po_line_items.csv (updated in place)

Caching: Extracts enrichment data from xlsx to CSV cache. Only reprocesses
xlsx if the source file is newer than the cache.
"""

import sys
from pathlib import Path

import pandas as pd

# Paths
SCRIPTS_DIR = Path(__file__).parent.parent
PROJECT_ROOT = SCRIPTS_DIR.parent
PO_DETAILS_FILE = PROJECT_ROOT / "data" / "raw" / "po details report.xlsx"
PO_LINE_ITEMS_FILE = PROJECT_ROOT / "data" / "intermediate" / "po_line_items.csv"
# Cache for enrichment data extracted from xlsx (speeds up subsequent runs)
ENRICHMENT_CACHE_FILE = PROJECT_ROOT / "data" / "intermediate" / "po_details_enrichment.csv"


def is_cache_fresh() -> bool:
    """Check if enrichment cache exists and is newer than the xlsx source."""
    if not ENRICHMENT_CACHE_FILE.exists():
        return False
    if not PO_DETAILS_FILE.exists():
        return False
    
    cache_mtime = ENRICHMENT_CACHE_FILE.stat().st_mtime
    source_mtime = PO_DETAILS_FILE.stat().st_mtime
    
    return cache_mtime > source_mtime


def load_enrichment_from_cache() -> pd.DataFrame:
    """Load enrichment data from cache CSV."""
    print(f"Loading enrichment data from cache: {ENRICHMENT_CACHE_FILE.name}")
    df = pd.read_csv(ENRICHMENT_CACHE_FILE)
    print(f"  Loaded {len(df):,} rows from cache")
    return df


def save_enrichment_to_cache(enrichment: pd.DataFrame) -> None:
    """Save enrichment data to cache CSV for future runs."""
    enrichment.to_csv(ENRICHMENT_CACHE_FILE, index=False)
    print(f"  Cached enrichment data to: {ENRICHMENT_CACHE_FILE.name}")


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
    """Extract Requester, PR Number, and PR Line from PO Details."""
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
    
    # PR Line: Purchase Requisition Item (nullable integer)
    # SAP PR line items are typically 10, 20, 30, etc.
    enrichment['PR Line'] = pd.to_numeric(
        details['Purchase Requisition Item'], errors='coerce'
    ).astype('Int64')
    
    # Stats
    print(f"  Requester values: {enrichment['Requester'].notna().sum():,}")
    print(f"  PR Number values: {enrichment['PR Number'].notna().sum():,}")
    print(f"  PR Line values: {enrichment['PR Line'].notna().sum():,}")
    
    return enrichment


def enrich_data(po_df: pd.DataFrame, enrichment: pd.DataFrame) -> pd.DataFrame:
    """Left join enrichment data to PO line items."""
    print("Enriching PO line items...")
    
    initial_count = len(po_df)
    
    # Drop existing enrichment columns if present (from previous runs)
    cols_to_drop = [col for col in ['Requester', 'PR Number', 'PR Line'] if col in po_df.columns]
    if cols_to_drop:
        po_df = po_df.drop(columns=cols_to_drop)
        print(f"  Dropped existing columns: {cols_to_drop}")
    
    # Left join to preserve all PO line items
    enriched = po_df.merge(
        enrichment[['PO Line ID', 'Requester', 'PR Number', 'PR Line']],
        on='PO Line ID',
        how='left'
    )
    
    assert len(enriched) == initial_count, "Row count changed after merge!"
    
    # Set Requester to "M&S Prime" for PR Numbers starting with 4 and 10 digits
    pr_str = enriched['PR Number'].astype(str)
    ms_prime_mask = pr_str.str.match(r'^4\d{9}$', na=False)
    enriched.loc[ms_prime_mask, 'Requester'] = 'M&S Prime'
    print(f"  Set 'M&S Prime' for {ms_prime_mask.sum():,} rows")
    
    # Set Requester to "FMT" for OPS vendor category
    vendor_category_col = "Main Vendor SLB Vendor Category"
    if vendor_category_col in enriched.columns:
        is_ops_vendor = enriched[vendor_category_col] == "OPS"
        enriched.loc[is_ops_vendor, 'Requester'] = 'FMT'
        print(f"  Set 'FMT' for {is_ops_vendor.sum():,} rows (OPS vendor category)")
    
    # Stats
    print(f"  Rows with Requester: {enriched['Requester'].notna().sum():,}")
    print(f"  Rows with PR Number: {enriched['PR Number'].notna().sum():,}")
    print(f"  Rows with PR Line: {enriched['PR Line'].notna().sum():,}")
    
    return enriched


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save enriched DataFrame to CSV."""
    # Sort by PO Line ID for deterministic output (avoids hash randomization issues)
    df = df.sort_values("PO Line ID").reset_index(drop=True)
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
    
    # Check if we can use cached enrichment data
    if is_cache_fresh():
        print("\n[1/3] Using cached enrichment data (xlsx unchanged)...")
        enrichment = load_enrichment_from_cache()
    else:
        print("\n[1/3] Processing xlsx file (cache missing or stale)...")
        details = load_po_details(PO_DETAILS_FILE)
        enrichment = extract_enrichment_data(details)
        save_enrichment_to_cache(enrichment)
    
    print("\n[2/3] Loading PO Line Items...")
    po_df = load_po_line_items(PO_LINE_ITEMS_FILE)
    
    print("\n[3/3] Enriching and saving data...")
    enriched = enrich_data(po_df, enrichment)
    save_data(enriched, PO_LINE_ITEMS_FILE)
    
    print("\n" + "=" * 60)
    print("Stage 2 Complete: PO Line Items enriched")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
