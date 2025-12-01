"""
Stage 3: Prepare WBS Details for Import

Maps intermediate columns to database schema columns and handles
duplicate WBS entries (same WBS from different sources).

Duplicate handling strategy:
- wbs_number is the primary key (globally unique across all FDP reports)
- If duplicates found (shouldn't happen), keep first occurrence

Array column handling:
- sub_business_lines: JSON array in CSV -> PostgreSQL text[] literal format
- Example: '["WLPS", "SLKN"]' -> '{WLPS,SLKN}'

Dependencies: scripts/stage2_transform/07_process_wbs.py
Input: data/intermediate/wbs_processed.csv
Output: data/import-ready/wbs_details.csv

Column Operations:
  WRITES: sub_business_lines
  READS:  sub_business_lines"""
import sys
import json
from pathlib import Path
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
import pandas as pd
from config.column_mappings import WBS_DETAILS_MAPPING
PROJECT_ROOT = SCRIPTS_DIR.parent
INPUT_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'wbs_processed.csv'
OUTPUT_FILE = PROJECT_ROOT / 'data' / 'import-ready' / 'wbs_details.csv'

def load_data() -> pd.DataFrame:
    """Load intermediate WBS data."""
    ...

def json_to_pg_array(json_str: str) -> str:
    """
    Convert JSON array string to PostgreSQL text[] literal format.
    
    Examples:
    - '["WLPS"]' -> '{WLPS}'
    - '["WLPS", "SLKN", "WLES"]' -> '{WLPS,SLKN,WLES}'
    - None/NaN -> None
    """
    ...

def handle_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle duplicate WBS entries.
    
    Since wbs_number is the primary key (globally unique across all FDP reports),
    we check for any duplicates and fail if found.
    """
    ...

def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map intermediate columns to database column names."""
    ...

def validate_output(df: pd.DataFrame) -> bool:
    """Validate required columns are present and data is valid."""
    ...

def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save import-ready DataFrame to CSV."""
    ...

def main():
    ...
if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)