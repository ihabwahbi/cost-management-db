#!/usr/bin/env python3
"""
Enrich PO Line Items with PR Number and Requester

This script enriches the cleaned PO line items CSV with data from 
the PO Details Report (xlsx):
- Requester: from "ARIBA shopping cart number : created by (Text)"
- PR Number: from "Purchase Requisition Number", fallback to "ARIBA Shopping cart number"
"""

import pandas as pd
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
PO_DETAILS_FILE = PROJECT_ROOT / "data" / "raw" / "po details report.xlsx"
CLEANED_FILE = PROJECT_ROOT / "data" / "processed" / "po_line_items_cleaned.csv"


def load_po_details(filepath: Path) -> pd.DataFrame:
    """Load PO Details Report and prepare for join."""
    print(f"Loading PO Details from: {filepath}")
    df = pd.read_excel(filepath)
    print(f"  Loaded {len(df):,} rows")
    
    # Create PO Line ID to match cleaned data format
    df['PO Line Item'] = df['PO Line Item'].fillna(0).astype(int)
    df['PO Line ID'] = df['PO Number'].astype(str) + '-' + df['PO Line Item'].astype(str)
    
    return df


def load_cleaned_data(filepath: Path) -> pd.DataFrame:
    """Load cleaned PO line items."""
    print(f"Loading cleaned PO Line Items from: {filepath}")
    df = pd.read_csv(filepath)
    print(f"  Loaded {len(df):,} rows")
    return df


def extract_enrichment_data(details: pd.DataFrame) -> pd.DataFrame:
    """Extract Requester and PR Number from PO Details."""
    print("Extracting enrichment data...")
    
    # Create enrichment dataframe
    enrichment = pd.DataFrame()
    enrichment['PO Line ID'] = details['PO Line ID']
    
    # Requester: always from ARIBA shopping cart number : created by (Text)
    enrichment['Requester'] = details['ARIBA shopping cart number : created by (Text)']
    
    # PR Number: Purchase Requisition Number, fallback to ARIBA Shopping cart number
    pr_number = details['Purchase Requisition Number'].copy()
    ariba_number = details['ARIBA Shopping cart number'].copy()
    
    # Convert PR Number from float to string (handle scientific notation)
    pr_number = pr_number.apply(lambda x: str(int(x)) if pd.notna(x) else None)
    ariba_number = ariba_number.apply(lambda x: str(x) if pd.notna(x) else None)
    
    # Use PR Number if available, otherwise ARIBA Shopping cart number
    enrichment['PR Number'] = pr_number.where(pr_number.notna(), ariba_number)
    
    # Stats
    requester_count = enrichment['Requester'].notna().sum()
    pr_from_pr = pr_number.notna().sum()
    pr_from_ariba = (enrichment['PR Number'].notna() & pr_number.isna()).sum()
    
    print(f"  Requester values: {requester_count:,}")
    print(f"  PR Number from Purchase Requisition: {pr_from_pr:,}")
    print(f"  PR Number from ARIBA (fallback): {pr_from_ariba:,}")
    
    return enrichment


def enrich_cleaned_data(cleaned: pd.DataFrame, enrichment: pd.DataFrame) -> pd.DataFrame:
    """Left join enrichment data to cleaned PO line items."""
    print("Enriching cleaned data...")
    
    initial_count = len(cleaned)
    
    # Left join to preserve all cleaned rows
    enriched = cleaned.merge(
        enrichment[['PO Line ID', 'Requester', 'PR Number']],
        on='PO Line ID',
        how='left'
    )
    
    # Verify no rows lost
    assert len(enriched) == initial_count, "Row count changed after merge!"
    
    # Set Requester to "M&S Prime" for PR Numbers starting with 4 and 10 digits long
    pr_str = enriched['PR Number'].astype(str)
    ms_prime_mask = pr_str.str.match(r'^4\d{9}$', na=False)
    ms_prime_count = ms_prime_mask.sum()
    enriched.loc[ms_prime_mask, 'Requester'] = 'M&S Prime'
    print(f"  Set Requester to 'M&S Prime' for {ms_prime_count:,} rows (PR starts with 4, 10 digits)")
    
    # Stats
    requester_filled = enriched['Requester'].notna().sum()
    pr_filled = enriched['PR Number'].notna().sum()
    
    print(f"  Rows enriched with Requester: {requester_filled:,} ({requester_filled/len(enriched)*100:.1f}%)")
    print(f"  Rows enriched with PR Number: {pr_filled:,} ({pr_filled/len(enriched)*100:.1f}%)")
    
    return enriched


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save enriched DataFrame back to CSV."""
    df.to_csv(filepath, index=False)
    print(f"  Saved to: {filepath}")


def main():
    print("=" * 60)
    print("PO Line Items Enrichment Script")
    print("=" * 60)
    
    # Load data
    print("\n[1/4] Loading PO Details Report...")
    details = load_po_details(PO_DETAILS_FILE)
    
    print("\n[2/4] Loading cleaned PO Line Items...")
    cleaned = load_cleaned_data(CLEANED_FILE)
    
    # Extract enrichment data
    print("\n[3/4] Extracting and joining data...")
    enrichment = extract_enrichment_data(details)
    enriched = enrich_cleaned_data(cleaned, enrichment)
    
    # Save
    print("\n[4/4] Saving enriched data...")
    save_data(enriched, CLEANED_FILE)
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
