"""
Stage 2: Enrich PO Line Items

Enriches intermediate PO line items with PR Number and Requester
from the PO Details Report.

Dependencies: 01_po_line_items.py must run first
Input: data/intermediate/po_line_items.csv, data/raw/po details report.xlsx
Output: data/intermediate/po_line_items.csv (updated in place)

Column Operations:
  WRITES: PO Line ID, PO Line Item, PR Number, Requester
  READS:  ARIBA Shopping cart number, ARIBA shopping cart number : created by (Text), PO Line ID, PO Line Item, PO Number, Purchase Requisition Number"""
import sys
from pathlib import Path
import pandas as pd
SCRIPTS_DIR = Path(__file__).parent.parent
PROJECT_ROOT = SCRIPTS_DIR.parent
PO_DETAILS_FILE = PROJECT_ROOT / 'data' / 'raw' / 'po details report.xlsx'
PO_LINE_ITEMS_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'po_line_items.csv'

def load_po_details(filepath: Path) -> pd.DataFrame:
    """Load PO Details Report and prepare for join."""
    ...

def load_po_line_items(filepath: Path) -> pd.DataFrame:
    """Load intermediate PO line items."""
    ...

def extract_enrichment_data(details: pd.DataFrame) -> pd.DataFrame:
    """Extract Requester and PR Number from PO Details."""
    ...

def enrich_data(po_df: pd.DataFrame, enrichment: pd.DataFrame) -> pd.DataFrame:
    """Left join enrichment data to PO line items."""
    ...

def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save enriched DataFrame to CSV."""
    ...

def main():
    ...
if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)