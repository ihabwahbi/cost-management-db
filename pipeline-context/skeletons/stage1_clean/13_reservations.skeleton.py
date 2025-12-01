"""
Stage 1: Clean Reservations

Reads raw reservations Excel file and performs:
1. Removes rows where both business line columns (Profit Center and Cost Center)
   have matching values of WCM, WCF, or WCD (internal transfers/overhead).
2. Splits "Reservation -Line" column into components:
   - reservation_line_id: Original combined key (e.g., "6086214878-1")
   - reservation_number: The reservation part (e.g., "6086214878")
   - reservation_line_number: The line number as integer (e.g., 1)
3. Normalizes PO Line IDs to match po_line_items format:
   - Strips leading zeros from line numbers (e.g., "4584632148-00001" -> "4584632148-1")
   - Cleans PO numbers (removes .0 suffix from float conversion)

Dependencies: None (independent stage 1 script)
Input: data/raw/reservations/Data Table - Open Reservation - *.xlsx
Output: data/intermediate/reservations.csv

Column Operations:
  WRITES: reservation_line_id, reservation_line_number, reservation_number
  READS:  Reservation -Line"""
import sys
from pathlib import Path
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
import pandas as pd
PROJECT_ROOT = SCRIPTS_DIR.parent
INPUT_FILE = PROJECT_ROOT / 'data' / 'raw' / 'reservations' / 'Data Table - Open Reservation - Supply Element Availability Status (1).xlsx'
OUTPUT_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'reservations.csv'
EXCLUDED_MATCHING_BUSINESS_LINES = {'WCM', 'WCF', 'WCD'}

def load_data(filepath: Path) -> pd.DataFrame:
    """Load the raw Excel file."""
    ...

def split_reservation_line_id(df: pd.DataFrame) -> pd.DataFrame:
    """
    Split 'Reservation -Line' column into components.

    Input format: "6086214878-1" (reservation_number-line_number)

    Creates:
    - reservation_line_id: Original combined value (for lookups/traceability)
    - reservation_number: The reservation part (for grouping)
    - reservation_line_number: The line number as integer (for sorting)
    """
    ...

def normalize_po_line_ids(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize PO Line IDs to match po_line_items format.

    Reservations format: "4584632148-00001" (5-digit zero-padded line number)
    PO Line Items format: "4581850069-1" (no padding)

    This ensures proper joins between sap_reservations and po_line_items tables.
    """
    ...

def filter_matching_business_lines(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove rows where both Business Line columns have the same value
    AND that value is one of WCM, WCF, or WCD.

    These represent internal transfers/overhead allocations.
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