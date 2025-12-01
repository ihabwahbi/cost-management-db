"""
Stage 2: Process WBS Data - Split, Parse, and Map Location

Combines WBS data from all three sources (Projects, Operations, Ops Activities),
parses WBS numbers and Sub Business Line codes, and maps location from Ops District.

Key transformations:
1. Split comma-separated WBS entries (Projects) into separate rows
2. Parse WBS number format: J.XX.XXXXXX from strings like "J.24.079733(WIS)"
3. Extract Sub Business Line codes as arrays:
   - Projects: single code from brackets -> ["WIS"]
   - Operations: comma-separated codes -> ["SLKN", "WLPS", "WLES"]
   - Ops Activities: map full name to code -> ["WLPS"]
4. Map location from Ops District (available in all three reports)
5. Validate WBS format and flag non-standard entries

Dependencies: 
- scripts/stage1_clean/10_wbs_from_projects.py
- scripts/stage1_clean/11_wbs_from_operations.py
- scripts/stage1_clean/12_wbs_from_ops_activities.py

Input: 
- data/intermediate/wbs_from_projects.csv
- data/intermediate/wbs_from_operations.csv
- data/intermediate/wbs_from_ops_activities.csv

Output: data/intermediate/wbs_processed.csv

Column Operations:
  WRITES: location, sub_business_line_from_wbs, sub_business_line_mapped, sub_business_lines, wbs_number
  READS:  ops_district, sap_wbs_raw, sub_business_line_from_wbs, sub_business_line_mapped, sub_business_line_raw, sub_business_lines_raw"""
import sys
import re
import json
from pathlib import Path
from typing import Optional, Tuple, List
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
import pandas as pd
from config.column_mappings import OPS_DISTRICT_TO_LOCATION, SBL_NAME_TO_CODE
PROJECT_ROOT = SCRIPTS_DIR.parent
INTERMEDIATE_DIR = PROJECT_ROOT / 'data' / 'intermediate'
INPUT_FILES = {'projects': INTERMEDIATE_DIR / 'wbs_from_projects.csv', 'operations': INTERMEDIATE_DIR / 'wbs_from_operations.csv', 'ops_activities': INTERMEDIATE_DIR / 'wbs_from_ops_activities.csv'}
OUTPUT_FILE = INTERMEDIATE_DIR / 'wbs_processed.csv'
WBS_PATTERN = re.compile('J\\.\\d{2}\\.\\d{6}')
BRACKET_PATTERN = re.compile('\\(([A-Z]+)\\)')

def load_all_sources() -> dict:
    """Load all WBS source files."""
    ...

def parse_wbs_entry(wbs_string: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse a single WBS entry to extract WBS number and SBL code.
    
    Examples:
    - "J.24.079733(WIS)" -> ("J.24.079733", "WIS")
    - "J.25.166462" -> ("J.25.166462", None)
    - "Invalid" -> (None, None)
    """
    ...

def to_sbl_array(codes: List[str]) -> str:
    """Convert list of SBL codes to JSON array string for CSV storage."""
    ...

def split_and_parse_projects(df: pd.DataFrame) -> pd.DataFrame:
    """
    Split comma-separated WBS entries in Projects and parse each.
    Each WBS gets a single SBL code wrapped in array format.
    """
    ...

def parse_operations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse Operations WBS entries.
    Operations can have multiple SBL codes (comma-separated in source).
    """
    ...

def parse_ops_activities(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse Ops Activities WBS entries.
    Maps full SBL names to codes, stores as single-element array.
    """
    ...

def map_location_from_ops_district(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """Map location from Ops District using OPS_DISTRICT_TO_LOCATION mapping."""
    ...

def combine_sources(dfs: dict) -> pd.DataFrame:
    """Combine all sources into a single DataFrame."""
    ...

def validate_wbs_format(df: pd.DataFrame) -> pd.DataFrame:
    """Validate WBS number format and flag non-standard entries."""
    ...

def select_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Select and order final output columns."""
    ...

def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save the processed DataFrame to CSV."""
    ...

def main():
    ...
if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)