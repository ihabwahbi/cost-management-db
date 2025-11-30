#!/usr/bin/env python3
"""
Data Profiling Tool for Agent-Assisted Development

Profiles a column from a CSV file to help agents understand data before coding.
This prevents blind assumptions about data values, distributions, and edge cases.

Usage:
    python3 scripts/profile_data.py <file_path> <column_name>
    python3 scripts/profile_data.py data/intermediate/po_line_items.csv "PO Receipt Status"

Output: JSON with dtype, nulls, unique values, and distribution.
"""

import pandas as pd
import sys
import json
from pathlib import Path


def profile_column(file_path: str, column_name: str) -> dict:
    """Profile a single column from a CSV file."""
    df = pd.read_csv(file_path, low_memory=False)
    
    if column_name not in df.columns:
        return {
            "error": f"Column '{column_name}' not found",
            "available_columns": sorted(df.columns.tolist())
        }
    
    col = df[column_name]
    
    # Basic stats
    stats = {
        "file": str(file_path),
        "column": column_name,
        "dtype": str(col.dtype),
        "total_rows": len(df),
        "null_count": int(col.isna().sum()),
        "null_pct": round(col.isna().mean() * 100, 2),
        "non_null_count": int(col.notna().sum()),
        "unique_count": int(col.nunique()),
    }
    
    # For categorical/object columns: show value distribution
    if col.dtype == 'object' or col.nunique() <= 20:
        value_counts = col.value_counts(dropna=False)
        stats["value_distribution"] = {
            str(k) if pd.notna(k) else "<NULL>": int(v) 
            for k, v in value_counts.head(20).items()
        }
        stats["sample_values"] = [
            str(v) for v in col.dropna().unique()[:10]
        ]
    
    # For numeric columns: show summary stats
    if pd.api.types.is_numeric_dtype(col):
        stats["min"] = float(col.min()) if col.notna().any() else None
        stats["max"] = float(col.max()) if col.notna().any() else None
        stats["mean"] = round(float(col.mean()), 4) if col.notna().any() else None
        stats["median"] = float(col.median()) if col.notna().any() else None
    
    return stats


def profile_file(file_path: str) -> dict:
    """Profile all columns from a CSV file (summary only)."""
    df = pd.read_csv(file_path, low_memory=False)
    
    return {
        "file": str(file_path),
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "columns": [
            {
                "name": col,
                "dtype": str(df[col].dtype),
                "null_pct": round(df[col].isna().mean() * 100, 2),
                "unique_count": int(df[col].nunique())
            }
            for col in df.columns
        ]
    }


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 scripts/profile_data.py <file_path> <column_name>  # Profile specific column")
        print("  python3 scripts/profile_data.py <file_path>                # Profile all columns (summary)")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not Path(file_path).exists():
        print(json.dumps({"error": f"File not found: {file_path}"}, indent=2))
        sys.exit(1)
    
    if len(sys.argv) >= 3:
        column_name = sys.argv[2]
        result = profile_column(file_path, column_name)
    else:
        result = profile_file(file_path)
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
