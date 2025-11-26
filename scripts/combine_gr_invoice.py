import pandas as pd
import os

# Define paths
gr_cleaned_path = 'data/processed/gr_cleaned.csv'
invoice_raw_path = 'data/raw/invoice table.csv'
processed_dir = 'data/processed'
output_path = os.path.join(processed_dir, 'combined_transactions.csv')

def combine_data():
    print("Loading data...")
    
    # Load GR Data
    if not os.path.exists(gr_cleaned_path):
        print(f"Error: File not found at {gr_cleaned_path}")
        return
    gr_df = pd.read_csv(gr_cleaned_path)
    
    # Load Invoice Data
    if not os.path.exists(invoice_raw_path):
        print(f"Error: File not found at {invoice_raw_path}")
        return
    inv_df = pd.read_csv(invoice_raw_path)
    
    # Clean Invoice Columns
    inv_df.columns = inv_df.columns.str.strip().str.lower().str.replace(' ', '_')
    
    print("Transforming data...")
    
    # Transform GR
    gr_transformed = pd.DataFrame()
    gr_transformed['po_line_id'] = gr_df['po_line_id']
    gr_transformed['transaction_type'] = 'GR'
    gr_transformed['transaction_date'] = gr_df['gr_posting_date']
    gr_transformed['transaction_quantity'] = gr_df['gr_effective_quantity']
    gr_transformed['transaction_amount_usd'] = None # Explicitly Null as requested
    
    # Transform Invoice
    inv_transformed = pd.DataFrame()
    inv_transformed['po_line_id'] = inv_df['po_line_id']
    inv_transformed['transaction_type'] = 'Invoice'
    inv_transformed['transaction_date'] = inv_df['invoice_posting_date']
    inv_transformed['transaction_quantity'] = inv_df['ir_effective_quantity']
    inv_transformed['transaction_amount_usd'] = inv_df['ir_amount_usd']
    
    # Combine
    print("Combining datasets...")
    combined_df = pd.concat([gr_transformed, inv_transformed], ignore_index=True)
    
    # Sort for better readability
    combined_df = combined_df.sort_values(['po_line_id', 'transaction_date'])
    
    # Save
    print(f"Saving combined data to {output_path}...")
    combined_df.to_csv(output_path, index=False)
    
    print("\nSummary:")
    print(f"GR rows: {len(gr_transformed)}")
    print(f"Invoice rows: {len(inv_transformed)}")
    print(f"Total Combined rows: {len(combined_df)}")
    print("\nFirst 5 rows:")
    print(combined_df.head().to_string())

if __name__ == "__main__":
    combine_data()
