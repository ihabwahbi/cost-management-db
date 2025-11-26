import pandas as pd
import os

# Define paths
raw_file_path = 'data/raw/gr table.csv'
processed_dir = 'data/processed'
processed_file_path = os.path.join(processed_dir, 'gr_cleaned.csv')

# Ensure processed directory exists
os.makedirs(processed_dir, exist_ok=True)

def clean_gr_data():
    print(f"Reading data from {raw_file_path}...")
    
    if not os.path.exists(raw_file_path):
        print(f"Error: File not found at {raw_file_path}")
        return

    try:
        df = pd.read_csv(raw_file_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # Standardize column names
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    
    # Convert types
    print("Converting types...")
    if 'gr_effective_quantity' in df.columns:
        df['gr_effective_quantity'] = pd.to_numeric(df['gr_effective_quantity'], errors='coerce')
        df['gr_effective_quantity'] = df['gr_effective_quantity'].fillna(0)
    else:
        print("Error: 'gr_effective_quantity' column not found.")
        return

    if 'gr_posting_date' in df.columns:
        df['gr_posting_date'] = pd.to_datetime(df['gr_posting_date'], errors='coerce')
    else:
        print("Error: 'gr_posting_date' column not found.")
        return

    # Count before
    total_rows = len(df)
    print(f"Total rows read: {total_rows}")
    
    # 1. Filter: Remove rows where quantity is 0
    df_filtered = df[df['gr_effective_quantity'] != 0].copy()
    rows_after_filter = len(df_filtered)
    print(f"Rows after removing 0 quantity: {rows_after_filter} (Removed {total_rows - rows_after_filter})")

    # 2. Group by PO Line ID and Posting Date, Sum Quantity
    # This effectively drops 'gr_line' and 'gr_amount_usd' as requested
    print("Grouping by 'po_line_id' and 'gr_posting_date' and summing 'gr_effective_quantity'...")
    
    df_cleaned = df_filtered.groupby(['po_line_id', 'gr_posting_date'], as_index=False)['gr_effective_quantity'].sum()
    
    # Count after aggregation
    final_rows = len(df_cleaned)
    print(f"Final rows after aggregation: {final_rows}")

    # Save
    print(f"Saving cleaned data to {processed_file_path}...")
    df_cleaned.to_csv(processed_file_path, index=False)
    print("Done.")

if __name__ == "__main__":
    clean_gr_data()
