"""
Stage 1: Clean GR (Goods Receipt) Postings

Reads raw GR table, filters and calculates GR amounts using unit prices
from intermediate PO line items.

Dependencies: 01_po_line_items.py must run first
Input: data/raw/gr table.csv, data/intermediate/po_line_items.csv
Output: data/intermediate/gr_postings.csv

Column Operations:
  WRITES: GR Amount, Unit Price
  READS:  GR Effective Quantity, Ordered Quantity, PO Line ID, Purchase Value USD, Unit Price"""
import sys
from pathlib import Path
import pandas as pd
SCRIPTS_DIR = Path(__file__).parent.parent
PROJECT_ROOT = SCRIPTS_DIR.parent
INPUT_FILE = PROJECT_ROOT / 'data' / 'raw' / 'gr table.csv'
PO_LINE_ITEMS_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'po_line_items.csv'
OUTPUT_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'gr_postings.csv'

def load_data(filepath: Path) -> pd.DataFrame:
    """Load the raw CSV file."""
    ...

def filter_zero_quantity(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with zero GR Effective Quantity."""
    ...

def calculate_gr_amount(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate GR Amount based on unit price from PO Line Items.
    Formula: GR Amount = (Purchase Value USD / Ordered Quantity) * GR Effective Quantity
    """
    ...

def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save the cleaned DataFrame to CSV."""
    ...

def main():
    ...
if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)