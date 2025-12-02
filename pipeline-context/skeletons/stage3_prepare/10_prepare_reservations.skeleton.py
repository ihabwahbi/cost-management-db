"""
Stage 3: Prepare SAP Reservations for Import

Maps intermediate columns to database schema columns and extracts
derived fields (PO info, asset info).

Transformations:
1. Map CSV columns to database column names
2. Extract po_number and po_line_number from "Main - PO Line to Peg to Reservation"
3. Extract asset_code and asset_serial_number from "Maximo Asset Num"
4. Convert Plant from float to string for plant_code
5. Keep po_line_item_id as the full PO-Line composite key for relationship

Dependencies: scripts/stage1_clean/13_reservations.py
Input: data/intermediate/reservations.csv
Output: data/import-ready/sap_reservations.csv

Column Operations:
  WRITES: asset_code, asset_serial_number, po_line_item_id, po_line_number, po_number, reservation_line_number, reservation_number
  READS:  Plant, po_line_number, po_number, reservation_line_id, reservation_line_number, reservation_number"""
import sys
from pathlib import Path
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
import pandas as pd
from config.column_mappings import REQUIRED_COLUMNS, SAP_RESERVATIONS_MAPPING
PROJECT_ROOT = SCRIPTS_DIR.parent
INPUT_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'reservations.csv'
OUTPUT_FILE = PROJECT_ROOT / 'data' / 'import-ready' / 'sap_reservations.csv'

def load_data() -> pd.DataFrame:
    """Load intermediate reservations data."""
    ...

def extract_po_info(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract PO number and line number from 'Main - PO Line to Peg to Reservation'.

    Format: "4584632148-1" -> po_number="4584632148", po_line_number=1
    Also keeps the full value as po_line_item_id for relationship lookup.
    """
    ...

def extract_asset_info(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract asset code and serial number from 'Maximo Asset Num'.

    Format: "XPS-CA|941" -> asset_code="XPS-CA", asset_serial_number="941"

    Note: Some values may not have "|" separator (e.g., "TCS92314Y1795").
    In those cases, the entire value goes to asset_code.
    """
    ...

def convert_plant_code(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert Plant from float to string.

    Input: 3606.0 -> Output: "3606"
    """
    ...

def clean_numeric_to_string(series: pd.Series) -> pd.Series:
    """Convert numeric series to clean string (remove .0 suffix)."""
    ...

def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map CSV columns to database column names."""
    ...

def validate_output(df: pd.DataFrame) -> bool:
    """Validate output using required column checks."""
    ...

def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save import-ready DataFrame to CSV."""
    ...

def main():
    ...
if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)