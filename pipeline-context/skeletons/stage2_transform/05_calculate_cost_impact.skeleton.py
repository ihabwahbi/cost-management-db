"""
Stage 2: Calculate Cost Impact

Calculates cost impact from GR and IR postings for each PO Line Item.
Two types: Simple (GLD + K/P/S/V) uses GR only, Complex uses GR/IR logic.

Dependencies: All stage1 scripts must run first
Input: data/intermediate/po_line_items.csv, gr_postings.csv, ir_postings.csv
Output: data/intermediate/cost_impact.csv
"""
import sys
from pathlib import Path
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
import pandas as pd
from config.column_mappings import SIMPLE_VENDOR_CATEGORY, SIMPLE_ACCOUNT_CATEGORIES
PROJECT_ROOT = SCRIPTS_DIR.parent
PO_LINE_ITEMS_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'po_line_items.csv'
GR_POSTINGS_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'gr_postings.csv'
IR_POSTINGS_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'ir_postings.csv'
OUTPUT_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'cost_impact.csv'

def load_data():
    """Load all required data files."""
    ...

def classify_po_line_items(po_df: pd.DataFrame) -> tuple:
    """
    Classify PO Line Items into simple (Type 1) and complex (Type 2).
    
    Type 1 (Simple): Vendor Category = GLD AND Account Category IN (K, P, S, V)
    Type 2 (Complex): All others
    """
    ...

def calculate_simple_cost_impact(gr_df: pd.DataFrame, simple_po_ids: set) -> pd.DataFrame:
    """
    Type 1: Cost impact = GR postings only (IR ignored).
    """
    ...

def calculate_complex_cost_impact(gr_df: pd.DataFrame, ir_df: pd.DataFrame, complex_po_ids: set, po_df: pd.DataFrame) -> pd.DataFrame:
    """
    Type 2: Cost impact based on GR/IR chronological processing.
    """
    ...

def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save cost impact DataFrame to CSV."""
    ...

def main():
    ...
if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)