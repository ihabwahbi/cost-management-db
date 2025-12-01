"""
Stage 1: Extract WBS Data from Operations Report

Reads the FDP Operations dashboard export and extracts/cleans WBS-related fields.
This script maintains 1:1 row traceability with the source file.

Note: Operations file has single WBS per row (no comma-separated entries).
Note: Most operations rows (89%) have NULL WBS - these are filtered out.
Note: No Plant Code column - will be enriched from Projects in Stage 2.

Dependencies: None (reads from raw)
Input: data/raw/fdp/OperationDashboard_Export_*.xlsx
Output: data/intermediate/wbs_from_operations.csv

Column Operations:
  WRITES: location, ops_activity_number, wbs_source"""
import sys
from pathlib import Path
from typing import Optional
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
import pandas as pd
PROJECT_ROOT = SCRIPTS_DIR.parent
RAW_DIR = PROJECT_ROOT / 'data' / 'raw' / 'fdp'
OUTPUT_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'wbs_from_operations.csv'
SOURCE_COLUMNS = ['Project Number', 'Operation Number', 'Operation Name', 'Customer', 'Rig', 'SAP WBS # / SO #', 'Ops District', 'Sub Business Line(s)']

def find_input_file() -> Optional[Path]:
    """Find the Operations dashboard export file."""
    ...

def load_data(filepath: Path) -> pd.DataFrame:
    """Load the Excel file and select relevant columns."""
    ...

def filter_rows_with_wbs(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to only rows that have WBS data."""
    ...

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to standardized intermediate format."""
    ...

def add_source_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Add source tracking and placeholder columns."""
    ...

def select_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Select and order final output columns."""
    ...

def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save the cleaned DataFrame to CSV."""
    ...

def main():
    ...
if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)