"""
Stage 1: Extract WBS Data from Operation Activities Report

Reads the FDP Operation Activities dashboard export and extracts/cleans WBS-related fields.
This script maintains 1:1 row traceability with the source file.

Note: Ops Activities has single WBS per row (no comma-separated entries).
Note: Has explicit "Sub Business Line" column with full names (not bracket codes).
Note: No Plant Code column - will be enriched from Projects in Stage 2.

Caching: Extracts data from xlsx to CSV cache. Only reprocesses xlsx if:
- Source file changed (different filename, mtime, or size)
- Script code changed (including config dependencies)
- Use --force to bypass cache

Dependencies: None (reads from raw)
Input: data/raw/fdp/OperationActivityDashboard_Export_*.xlsx
Output: data/intermediate/wbs_from_ops_activities.csv

Column Operations:
  WRITES: location, wbs_source"""
import argparse
import sys
from pathlib import Path
from typing import Optional
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
import pandas as pd
from utils.xlsx_cache import XlsxCacheManager
PROJECT_ROOT = SCRIPTS_DIR.parent
RAW_DIR = PROJECT_ROOT / 'data' / 'raw' / 'fdp'
OUTPUT_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'wbs_from_ops_activities.csv'
SOURCE_PATTERN = 'OperationActivityDashboard_Export_*.xlsx'
SOURCE_COLUMNS = ['Project Number', 'Operation Number', 'Ops Activity Number', 'Ops Activity Name', 'Customer', 'Rig', 'SAP WBS # / SO #', 'Sub Business Line', 'Ops District']

def find_input_file() -> Optional[Path]:
    """Find the Operation Activities dashboard export file."""
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

def main(force: bool=False) -> bool:
    ...
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract WBS data from Operation Activities dashboard export')
    parser.add_argument('--force', '-f', action='store_true', help='Force processing even if cache is valid')
    args = parser.parse_args()
    success = main(force=args.force)
    sys.exit(0 if success else 1)