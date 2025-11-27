"""
Data Exploration Script for Cost Management Database
=====================================================
Purpose: Gather comprehensive information about xlsx data files for AI-driven analysis.

This script explores:
1. File structure (sheets, columns, data types)
2. Data quality (nulls, duplicates, outliers)
3. Column statistics (unique values, distributions, ranges)
4. Key identification (what uniquely identifies records)
5. Cross-file relationships (how files link together)
6. Business logic mapping (columns for cost recognition rules)
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
PO_DETAILS_FILE = DATA_DIR / "po details report.xlsx"
PO_HISTORY_FILE = DATA_DIR / "po history report.xlsx"

def get_dtype_category(dtype):
    """Categorize pandas dtype into readable category."""
    dtype_str = str(dtype)
    if 'int' in dtype_str:
        return 'integer'
    elif 'float' in dtype_str:
        return 'float'
    elif 'datetime' in dtype_str:
        return 'datetime'
    elif 'bool' in dtype_str:
        return 'boolean'
    else:
        return 'string/object'

def analyze_column(series, col_name, max_unique_display=20):
    """Deep analysis of a single column."""
    analysis = {
        'name': col_name,
        'dtype': str(series.dtype),
        'dtype_category': get_dtype_category(series.dtype),
        'total_count': len(series),
        'null_count': int(series.isna().sum()),
        'null_percentage': round(series.isna().sum() / len(series) * 100, 2),
        'unique_count': int(series.nunique()),
        'unique_percentage': round(series.nunique() / len(series) * 100, 2),
    }
    
    # For non-null values
    non_null = series.dropna()
    
    if len(non_null) > 0:
        # Check if numeric
        if pd.api.types.is_numeric_dtype(series):
            analysis['min'] = float(non_null.min()) if not pd.isna(non_null.min()) else None
            analysis['max'] = float(non_null.max()) if not pd.isna(non_null.max()) else None
            analysis['mean'] = round(float(non_null.mean()), 4) if not pd.isna(non_null.mean()) else None
            analysis['median'] = float(non_null.median()) if not pd.isna(non_null.median()) else None
            analysis['std'] = round(float(non_null.std()), 4) if not pd.isna(non_null.std()) else None
            # Check for potential ID column (all unique integers)
            if analysis['unique_count'] == analysis['total_count'] - analysis['null_count']:
                analysis['potential_id'] = True
        
        # Check if datetime
        elif pd.api.types.is_datetime64_any_dtype(series):
            analysis['min_date'] = str(non_null.min())
            analysis['max_date'] = str(non_null.max())
            analysis['date_range_days'] = (non_null.max() - non_null.min()).days
        
        # Sample values for all types
        if analysis['unique_count'] <= max_unique_display:
            # Show all unique values with counts
            value_counts = series.value_counts(dropna=False).head(max_unique_display)
            analysis['value_distribution'] = {
                str(k): int(v) for k, v in value_counts.items()
            }
        else:
            # Show top values only
            value_counts = series.value_counts(dropna=False).head(10)
            analysis['top_10_values'] = {
                str(k): int(v) for k, v in value_counts.items()
            }
            # Show sample of unique values
            sample_values = non_null.drop_duplicates().head(10).tolist()
            analysis['sample_unique_values'] = [str(v) for v in sample_values]
    
    return analysis

def explore_excel_file(filepath, file_label):
    """Comprehensive exploration of an Excel file."""
    print(f"\n{'='*80}")
    print(f"EXPLORING: {file_label}")
    print(f"File: {filepath}")
    print(f"{'='*80}")
    
    if not filepath.exists():
        print(f"ERROR: File not found!")
        return None
    
    # Get file info
    file_size_mb = filepath.stat().st_size / (1024 * 1024)
    print(f"File size: {file_size_mb:.2f} MB")
    
    result = {
        'file': str(filepath.name),
        'file_size_mb': round(file_size_mb, 2),
        'sheets': {}
    }
    
    # Read all sheets
    xlsx = pd.ExcelFile(filepath)
    sheet_names = xlsx.sheet_names
    print(f"Sheets found: {sheet_names}")
    result['sheet_names'] = sheet_names
    
    for sheet_name in sheet_names:
        print(f"\n{'-'*60}")
        print(f"Sheet: '{sheet_name}'")
        print(f"{'-'*60}")
        
        # Read the sheet
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        
        sheet_info = {
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': list(df.columns),
            'memory_usage_mb': round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
            'column_analysis': {}
        }
        
        print(f"Rows: {sheet_info['row_count']:,}")
        print(f"Columns: {sheet_info['column_count']}")
        print(f"Memory: {sheet_info['memory_usage_mb']:.2f} MB")
        
        # Analyze each column
        print(f"\nColumn Analysis:")
        print("-" * 40)
        
        for col in df.columns:
            col_analysis = analyze_column(df[col], col)
            sheet_info['column_analysis'][col] = col_analysis
            
            # Print summary
            null_indicator = f" [NULL: {col_analysis['null_percentage']}%]" if col_analysis['null_count'] > 0 else ""
            print(f"  {col}: {col_analysis['dtype_category']} | {col_analysis['unique_count']:,} unique{null_indicator}")
        
        # Show sample data
        print(f"\nFirst 3 rows (sample):")
        print(df.head(3).to_string())
        
        # Check for potential composite keys
        print(f"\nPotential Key Analysis:")
        # Try common key column patterns
        potential_key_cols = [col for col in df.columns if any(
            kw in col.lower() for kw in ['po', 'item', 'line', 'number', 'id', 'key', 'doc']
        )]
        if potential_key_cols:
            print(f"  Potential key columns: {potential_key_cols}")
            # Check uniqueness of combinations
            for col in potential_key_cols[:5]:  # Limit to first 5
                unique_ratio = df[col].nunique() / len(df) * 100
                print(f"    {col}: {df[col].nunique():,} unique ({unique_ratio:.1f}%)")
        
        # Store sample data
        sheet_info['sample_data'] = df.head(5).to_dict(orient='records')
        
        result['sheets'][sheet_name] = sheet_info
    
    return result

def find_common_columns(result1, result2):
    """Find columns that exist in both files (potential join keys)."""
    if not result1 or not result2:
        return []
    
    cols1 = set()
    cols2 = set()
    
    for sheet_info in result1['sheets'].values():
        cols1.update(sheet_info['columns'])
    
    for sheet_info in result2['sheets'].values():
        cols2.update(sheet_info['columns'])
    
    common = cols1.intersection(cols2)
    return sorted(list(common))

def find_business_logic_columns(result):
    """Identify columns relevant to cost recognition business logic."""
    if not result:
        return {}
    
    business_columns = {
        'vendor_related': [],
        'account_assignment': [],
        'transaction_type': [],
        'quantity_amount': [],
        'date_fields': [],
        'po_identifiers': []
    }
    
    keywords = {
        'vendor_related': ['vendor', 'supplier', 'slb', 'gld', 'category'],
        'account_assignment': ['account', 'assignment', 'category', 'acct'],
        'transaction_type': ['type', 'posting', 'movement', 'gr', 'invoice', 'ir'],
        'quantity_amount': ['qty', 'quantity', 'amount', 'value', 'price', 'cost'],
        'date_fields': ['date', 'time', 'period', 'year', 'month'],
        'po_identifiers': ['po', 'purchase', 'order', 'item', 'line', 'doc', 'document']
    }
    
    for sheet_info in result['sheets'].values():
        for col in sheet_info['columns']:
            col_lower = col.lower()
            for category, kws in keywords.items():
                if any(kw in col_lower for kw in kws):
                    if col not in business_columns[category]:
                        business_columns[category].append(col)
    
    return business_columns

def main():
    """Main exploration function."""
    print("=" * 80)
    print("DATA EXPLORATION FOR COST MANAGEMENT DATABASE")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    
    results = {}
    
    # Explore PO Details
    results['po_details'] = explore_excel_file(PO_DETAILS_FILE, "PO Details Report")
    
    # Explore PO History
    results['po_history'] = explore_excel_file(PO_HISTORY_FILE, "PO History Report")
    
    # Cross-file analysis
    print("\n" + "=" * 80)
    print("CROSS-FILE ANALYSIS")
    print("=" * 80)
    
    common_cols = find_common_columns(results['po_details'], results['po_history'])
    print(f"\nCommon columns between files: {common_cols}")
    results['common_columns'] = common_cols
    
    # Business logic column identification
    print("\n" + "-" * 60)
    print("BUSINESS LOGIC COLUMN MAPPING")
    print("-" * 60)
    
    for file_key, file_result in results.items():
        if isinstance(file_result, dict) and 'sheets' in file_result:
            print(f"\n{file_key}:")
            biz_cols = find_business_logic_columns(file_result)
            results[f'{file_key}_business_columns'] = biz_cols
            for category, cols in biz_cols.items():
                if cols:
                    print(f"  {category}: {cols}")
    
    # Save raw results to JSON for reference
    output_file = Path(__file__).parent.parent / "data" / "exploration_results.json"
    
    # Convert to JSON-serializable format
    def make_serializable(obj):
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_serializable(v) for v in obj]
        elif isinstance(obj, (pd.Timestamp, datetime)):
            return str(obj)
        elif pd.isna(obj):
            return None
        else:
            return obj
    
    serializable_results = make_serializable(results)
    
    with open(output_file, 'w') as f:
        json.dump(serializable_results, f, indent=2, default=str)
    
    print(f"\n\nRaw results saved to: {output_file}")
    print("\n" + "=" * 80)
    print("EXPLORATION COMPLETE")
    print("=" * 80)
    
    return results

if __name__ == "__main__":
    main()
