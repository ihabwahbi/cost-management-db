"""
Stage 1: Clean IR (Invoice Receipt) Postings

Reads raw invoice table, calculates invoice amounts using unit prices
from intermediate PO line items.

Dependencies: 01_po_line_items.py must run first
Input: data/raw/invoice table.csv, data/intermediate/po_line_items.csv
Output: data/intermediate/ir_postings.csv
"""
import sys
from pathlib import Path
import pandas as pd
SCRIPTS_DIR = Path(__file__).parent.parent
PROJECT_ROOT = SCRIPTS_DIR.parent
INPUT_FILE = PROJECT_ROOT / 'data' / 'raw' / 'invoice table.csv'
PO_LINE_ITEMS_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'po_line_items.csv'
OUTPUT_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'ir_postings.csv'

def load_data(filepath: Path) -> pd.DataFrame:
    """Load the raw CSV file."""
    ...

def calculate_invoice_amount(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Invoice Amount based on unit price from PO Line Items.
    Formula: Invoice Amount = (Purchase Value USD / Ordered Quantity) * IR Effective Quantity
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