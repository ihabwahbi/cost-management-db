"""
Stage 2: Calculate GRIR Exposures

Calculates GRIR (Goods Receipt/Invoice Receipt variance) for Simple POs
(GLD vendor + K/P/S/V account assignment). GRIR = IR - GR when IR > GR.

This tracks balance sheet exposure from invoices received but not yet
goods-receipted, which will eventually hit the Net Income Statement.

Dependencies: All stage1 scripts + 05_calculate_cost_impact.py must run first
Input: data/intermediate/po_line_items.csv, gr_postings.csv, ir_postings.csv
Output: data/intermediate/grir_exposures.csv

Column Operations:
  WRITES: Posting Date, Posting Type, Unit Price
  READS:  Ordered Quantity, Posting Date, Purchase Value USD"""
import sys
from pathlib import Path
from datetime import date
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
import pandas as pd
from config.column_mappings import SIMPLE_VENDOR_CATEGORY, SIMPLE_ACCOUNT_CATEGORIES, GRIR_TIME_BUCKETS, GRIR_TIME_BUCKET_MAX
PROJECT_ROOT = SCRIPTS_DIR.parent
PO_LINE_ITEMS_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'po_line_items.csv'
GR_POSTINGS_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'gr_postings.csv'
IR_POSTINGS_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'ir_postings.csv'
OUTPUT_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'grir_exposures.csv'

def load_data():
    """Load all required data files."""
    ...

def get_simple_po_ids(po_df: pd.DataFrame) -> set:
    """
    Get PO Line IDs for Simple POs (GLD + K/P/S/V) that are NOT closed.
    These are the POs where we track GRIR exposure.
    
    Closed POs are excluded - no exposure if PO is already closed.
    """
    ...

def get_unit_prices(po_df: pd.DataFrame) -> dict:
    """Calculate unit price for each PO Line ID."""
    ...

def categorize_time_bucket(days: int) -> str:
    """Categorize days into time bucket."""
    ...

def calculate_grir_exposures(gr_df: pd.DataFrame, ir_df: pd.DataFrame, simple_po_ids: set, unit_prices: dict, snapshot_date: date) -> pd.DataFrame:
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
    ...

def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save GRIR exposures DataFrame to CSV."""
    ...

def main():
    ...
if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)