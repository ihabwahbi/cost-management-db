"""
Stage 1: Extract WBS Data from Projects Report

Reads the FDP Projects dashboard export and extracts/cleans WBS-related fields.
This script maintains 1:1 row traceability with the source file.
WBS splitting (for comma-separated entries) happens in Stage 2.

Caching: Extracts data from xlsx to CSV cache. Only reprocesses xlsx if:
- Source file changed (different filename, mtime, or size)
- Script code changed (including config dependencies)
- Use --force to bypass cache

Dependencies: None (reads from raw)
Input: data/raw/fdp/ProjectDashboard_Export_*.xlsx
Output: data/intermediate/wbs_from_projects.csv

Column Operations:
  WRITES: location, operation_number, ops_activity_number, rig, wbs_source
  READS:  ops_district, project_type, rigs"""
import argparse
import sys
from pathlib import Path
from typing import Optional
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
import pandas as pd
from config.column_mappings import OPS_DISTRICT_TO_LOCATION
from utils.xlsx_cache import XlsxCacheManager
PROJECT_ROOT = SCRIPTS_DIR.parent
RAW_DIR = PROJECT_ROOT / 'data' / 'raw' / 'fdp'
OUTPUT_FILE = PROJECT_ROOT / 'data' / 'intermediate' / 'wbs_from_projects.csv'
SOURCE_PATTERN = 'ProjectDashboard_Export_*.xlsx'
CONFIG_FILE = SCRIPTS_DIR / 'config' / 'column_mappings.py'
SOURCE_COLUMNS = ['Project Number', 'Project Name', 'Customer', 'Rigs', 'SAP WBS # / SO #', 'Ops District', 'Project Type']

def find_input_file() -> Optional[Path]:
    """Find the Projects dashboard export file."""
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

def map_location(df: pd.DataFrame) -> pd.DataFrame:
    """Map Ops District to Location."""
    ...

def determine_rig(df: pd.DataFrame) -> pd.DataFrame:
    """Determine rig value - use Rigs column, fallback to Project Type."""
    ...

def add_source_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Add source tracking columns."""
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
    parser = argparse.ArgumentParser(description='Extract WBS data from Projects dashboard export')
    parser.add_argument('--force', '-f', action='store_true', help='Force processing even if cache is valid')
    args = parser.parse_args()
    success = main(force=args.force)
    sys.exit(0 if success else 1)