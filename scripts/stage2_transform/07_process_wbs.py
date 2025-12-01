#!/usr/bin/env python3
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
"""

import sys
import re
import json
from pathlib import Path
from typing import Optional, Tuple, List

# Add scripts directory to path for config imports
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import pandas as pd
from config.column_mappings import OPS_DISTRICT_TO_LOCATION, SBL_NAME_TO_CODE

# Paths
PROJECT_ROOT = SCRIPTS_DIR.parent
INTERMEDIATE_DIR = PROJECT_ROOT / "data" / "intermediate"

INPUT_FILES = {
    "projects": INTERMEDIATE_DIR / "wbs_from_projects.csv",
    "operations": INTERMEDIATE_DIR / "wbs_from_operations.csv",
    "ops_activities": INTERMEDIATE_DIR / "wbs_from_ops_activities.csv",
}
OUTPUT_FILE = INTERMEDIATE_DIR / "wbs_processed.csv"

# WBS pattern: J.XX.XXXXXX (J, dot, 2 digits, dot, 6 digits)
WBS_PATTERN = re.compile(r'J\.\d{2}\.\d{6}')
# Pattern to extract code from brackets: (XXX)
BRACKET_PATTERN = re.compile(r'\(([A-Z]+)\)')


def load_all_sources() -> dict:
    """Load all WBS source files."""
    dfs = {}
    for name, filepath in INPUT_FILES.items():
        if filepath.exists():
            df = pd.read_csv(filepath)
            print(f"  Loaded {len(df):,} rows from {filepath.name}")
            dfs[name] = df
        else:
            print(f"  WARNING: File not found: {filepath.name}")
            dfs[name] = pd.DataFrame()
    return dfs


def parse_wbs_entry(wbs_string: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse a single WBS entry to extract WBS number and SBL code.
    
    Examples:
    - "J.24.079733(WIS)" -> ("J.24.079733", "WIS")
    - "J.25.166462" -> ("J.25.166462", None)
    - "Invalid" -> (None, None)
    """
    if pd.isna(wbs_string) or not wbs_string:
        return None, None
    
    wbs_string = str(wbs_string).strip()
    
    # Extract WBS number
    wbs_match = WBS_PATTERN.search(wbs_string)
    wbs_number = wbs_match.group(0) if wbs_match else None
    
    # Extract SBL code from brackets
    bracket_match = BRACKET_PATTERN.search(wbs_string)
    sbl_code = bracket_match.group(1) if bracket_match else None
    
    return wbs_number, sbl_code


def to_sbl_array(codes: List[str]) -> str:
    """Convert list of SBL codes to JSON array string for CSV storage."""
    if not codes:
        return None
    # Filter out None/empty values
    valid_codes = [c for c in codes if c]
    if not valid_codes:
        return None
    return json.dumps(valid_codes)


def split_and_parse_projects(df: pd.DataFrame) -> pd.DataFrame:
    """
    Split comma-separated WBS entries in Projects and parse each.
    Each WBS gets a single SBL code wrapped in array format.
    """
    if len(df) == 0:
        return df
    
    initial_count = len(df)
    rows = []
    
    for _, row in df.iterrows():
        wbs_raw = row.get("sap_wbs_raw", "")
        if pd.isna(wbs_raw) or not wbs_raw:
            continue
        
        # Split by comma
        wbs_entries = [w.strip() for w in str(wbs_raw).split(",")]
        
        for entry in wbs_entries:
            wbs_number, sbl_code = parse_wbs_entry(entry)
            if wbs_number:
                new_row = row.copy()
                new_row["wbs_number"] = wbs_number
                # Store as JSON array with single element
                new_row["sub_business_lines"] = to_sbl_array([sbl_code]) if sbl_code else None
                rows.append(new_row)
    
    result = pd.DataFrame(rows)
    print(f"  Projects: {initial_count:,} rows -> {len(result):,} rows (split WBS entries)")
    return result


def parse_operations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse Operations WBS entries.
    Operations can have multiple SBL codes (comma-separated in source).
    """
    if len(df) == 0:
        return df
    
    initial_count = len(df)
    
    # Parse WBS entries
    parsed = df["sap_wbs_raw"].apply(lambda x: pd.Series(parse_wbs_entry(x)))
    df["wbs_number"] = parsed[0]
    
    # Parse comma-separated SBL codes to array
    def parse_sbl_codes(raw_value):
        if pd.isna(raw_value) or not raw_value:
            return None
        codes = [c.strip() for c in str(raw_value).split(",")]
        return to_sbl_array(codes)
    
    if "sub_business_lines_raw" in df.columns:
        df["sub_business_lines"] = df["sub_business_lines_raw"].apply(parse_sbl_codes)
        df = df.drop(columns=["sub_business_lines_raw"])
        
        sbl_filled = df["sub_business_lines"].notna().sum()
        print(f"  Operations: Parsed {sbl_filled:,} SBL arrays")
    else:
        df["sub_business_lines"] = None
    
    # Filter out rows where WBS couldn't be parsed
    valid_mask = df["wbs_number"].notna()
    invalid_count = (~valid_mask).sum()
    if invalid_count > 0:
        print(f"  WARNING: {invalid_count} rows with unparseable WBS")
    
    df = df[valid_mask].copy()
    print(f"  Operations: {initial_count:,} rows -> {len(df):,} rows (parsed)")
    return df


def parse_ops_activities(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse Ops Activities WBS entries.
    Maps full SBL names to codes, stores as single-element array.
    """
    if len(df) == 0:
        return df
    
    initial_count = len(df)
    
    # Parse WBS entries
    parsed = df["sap_wbs_raw"].apply(lambda x: pd.Series(parse_wbs_entry(x)))
    df["wbs_number"] = parsed[0]
    df["sub_business_line_from_wbs"] = parsed[1]
    
    # Map full SBL names to codes
    if "sub_business_line_raw" in df.columns:
        df["sub_business_line_mapped"] = df["sub_business_line_raw"].map(SBL_NAME_TO_CODE)
        
        # Check for unmapped values
        unmapped = df["sub_business_line_raw"].notna() & df["sub_business_line_mapped"].isna()
        if unmapped.any():
            unmapped_values = df.loc[unmapped, "sub_business_line_raw"].unique().tolist()
            print(f"  WARNING: Unmapped SBL names: {unmapped_values}")
        
        # Use mapped code, fall back to WBS-extracted code
        sbl_code = df["sub_business_line_mapped"].where(
            df["sub_business_line_mapped"].notna(),
            df["sub_business_line_from_wbs"]
        )
        
        # Convert to JSON array
        df["sub_business_lines"] = sbl_code.apply(lambda x: to_sbl_array([x]) if pd.notna(x) else None)
        df = df.drop(columns=["sub_business_line_raw", "sub_business_line_from_wbs", "sub_business_line_mapped"])
        
        mapped_count = df["sub_business_lines"].notna().sum()
        print(f"  Ops Activities: Mapped {mapped_count:,} SBL names to codes")
    else:
        df["sub_business_lines"] = df["sub_business_line_from_wbs"].apply(
            lambda x: to_sbl_array([x]) if pd.notna(x) else None
        )
        df = df.drop(columns=["sub_business_line_from_wbs"])
    
    # Filter out rows where WBS couldn't be parsed
    valid_mask = df["wbs_number"].notna()
    invalid_count = (~valid_mask).sum()
    if invalid_count > 0:
        print(f"  WARNING: {invalid_count} rows with unparseable WBS")
    
    df = df[valid_mask].copy()
    print(f"  Ops Activities: {initial_count:,} rows -> {len(df):,} rows (parsed)")
    return df


def map_location_from_ops_district(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """Map location from Ops District using OPS_DISTRICT_TO_LOCATION mapping."""
    if len(df) == 0:
        return df
    
    df["location"] = df["ops_district"].map(OPS_DISTRICT_TO_LOCATION)
    
    mapped_count = df["location"].notna().sum()
    unmapped = df["ops_district"].notna() & df["location"].isna()
    unmapped_districts = df.loc[unmapped, "ops_district"].unique().tolist()
    
    print(f"  {source_name}: Mapped {mapped_count:,}/{len(df):,} rows to location")
    if unmapped_districts:
        print(f"  WARNING: Unmapped Ops Districts: {unmapped_districts}")
    
    return df


def combine_sources(dfs: dict) -> pd.DataFrame:
    """Combine all sources into a single DataFrame."""
    all_dfs = []
    for name, df in dfs.items():
        if len(df) > 0:
            all_dfs.append(df)
    
    if not all_dfs:
        return pd.DataFrame()
    
    combined = pd.concat(all_dfs, ignore_index=True)
    print(f"  Combined total: {len(combined):,} rows")
    return combined


def validate_wbs_format(df: pd.DataFrame) -> pd.DataFrame:
    """Validate WBS number format and flag non-standard entries."""
    if len(df) == 0:
        return df
    
    valid_format = df["wbs_number"].str.match(r'^J\.\d{2}\.\d{6}$', na=False)
    invalid_count = (~valid_format).sum()
    
    if invalid_count > 0:
        print(f"  WARNING: {invalid_count} rows with non-standard WBS format")
        invalid_wbs = df.loc[~valid_format, "wbs_number"].unique()
        print(f"  Sample invalid: {list(invalid_wbs[:5])}")
    
    print(f"  Valid WBS format: {valid_format.sum():,} rows")
    return df


def select_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Select and order final output columns."""
    output_cols = [
        "wbs_number",
        "wbs_source",
        "project_number",
        "operation_number",
        "ops_activity_number",
        "wbs_name",
        "client_name",
        "rig",
        "ops_district",
        "location",
        "sub_business_lines",  # JSON array format
    ]
    
    available = [c for c in output_cols if c in df.columns]
    missing = set(output_cols) - set(available)
    if missing:
        print(f"  Note: Missing columns (will be added as NULL): {missing}")
        for col in missing:
            df[col] = None
        available = output_cols
    
    df = df[available]
    print(f"  Selected {len(available)} output columns")
    return df


def save_data(df: pd.DataFrame, filepath: Path) -> None:
    """Save the processed DataFrame to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"  Saved to: {filepath}")
    print(f"  Final row count: {len(df):,}")


def main():
    print("=" * 60)
    print("Stage 2: Process WBS Data - Split, Parse, and Map Location")
    print("=" * 60)
    
    print("\n[1/7] Loading source files...")
    dfs = load_all_sources()
    
    print("\n[2/7] Splitting and parsing Projects WBS...")
    df_projects = split_and_parse_projects(dfs.get("projects", pd.DataFrame()))
    
    print("\n[3/7] Parsing Operations WBS...")
    df_operations = parse_operations(dfs.get("operations", pd.DataFrame()))
    
    print("\n[4/7] Parsing Ops Activities WBS...")
    df_ops_activities = parse_ops_activities(dfs.get("ops_activities", pd.DataFrame()))
    
    print("\n[5/7] Mapping location from Ops District...")
    df_projects = map_location_from_ops_district(df_projects, "Projects")
    df_operations = map_location_from_ops_district(df_operations, "Operations")
    df_ops_activities = map_location_from_ops_district(df_ops_activities, "Ops Activities")
    
    print("\n[6/7] Combining all sources...")
    processed_dfs = {
        "projects": df_projects,
        "operations": df_operations,
        "ops_activities": df_ops_activities,
    }
    combined = combine_sources(processed_dfs)
    
    if len(combined) == 0:
        print("ERROR: No WBS data to process")
        return False
    
    print("\n[7/7] Validating and selecting output columns...")
    combined = validate_wbs_format(combined)
    combined = select_output_columns(combined)
    
    print("\n[Save] Writing output...")
    save_data(combined, OUTPUT_FILE)
    
    # Print summary
    print("\n" + "-" * 40)
    print("Summary by Source:")
    print(combined["wbs_source"].value_counts().to_string())
    
    print("\nLocation Fill Rate:")
    total = len(combined)
    mapped = combined["location"].notna().sum()
    print(f"  {mapped:,}/{total:,} ({mapped/total*100:.1f}%) rows have location")
    
    print("\nSBL Fill Rate:")
    sbl_filled = combined["sub_business_lines"].notna().sum()
    print(f"  {sbl_filled:,}/{total:,} ({sbl_filled/total*100:.1f}%) rows have SBL codes")
    
    print("\n" + "=" * 60)
    print("Stage 2 Complete: WBS data processed and combined")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
