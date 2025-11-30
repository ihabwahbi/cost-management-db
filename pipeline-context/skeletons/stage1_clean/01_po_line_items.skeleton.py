"""
Stage 1: Clean PO Line Items

Reads raw PO line items CSV, applies filtering and transformations,
outputs to intermediate folder.

Dependencies: None (first script in pipeline)
Input: data/raw/po line items.csv
Output: data/intermediate/po_line_items.csv

Column Operations:
  WRITES: Expected Delivery Date, Location, Main Vendor Name, NIS Level 0 Desc, Ultimate Vendor Name
  READS:  Main Vendor ID, Plant Code, Ultimate Vendor Number"""
import sys
from pathlib import Path
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
import pandas as pd
from config.column_mappings import EXCLUDED_VALUATION_CLASSES, EXCLUDED_NIS_LEVELS, VENDOR_NAME_MAPPING, PLANT_CODE_TO_LOCATION
PROJECT_ROOT = SCRIPTS_DIR.parent
INPUT_FILE = PROJECT_ROOT / 'data' / 'raw' / 'po line items.csv'
OUTPUT_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'po_line_items.csv'

def load_data(filepath: Path) -> pd.DataFrame:
    """Load the raw CSV file."""
    ...

def filter_valuation_classes(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with excluded PO Valuation Classes."""
    ...

def filter_nis_levels(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with excluded NIS Level 0 Desc values."""
    ...

def fill_nis_level_for_3021(df: pd.DataFrame) -> pd.DataFrame:
    """Set NIS Level 0 Desc to 'Materials and Supplies' for Valuation Class 3021 where null."""
    ...

def transform_nis_column(df: pd.DataFrame) -> pd.DataFrame:
    """Rename NIS Level 0 Desc to NIS Line and clean up values."""
    ...

def map_vendor_names(df: pd.DataFrame) -> pd.DataFrame:
    """Map Main Vendor Name and Ultimate Vendor Name based on vendor IDs."""
    ...

def map_location(df: pd.DataFrame) -> pd.DataFrame:
    """Map Plant Code to Location."""
    ...

def consolidate_delivery_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Consolidate delivery date columns into 'Expected Delivery Date'."""
    ...

def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save the cleaned DataFrame to CSV."""
    ...

def main():
    ...
if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)