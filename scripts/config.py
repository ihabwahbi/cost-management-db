"""
Centralized configuration for data processing pipeline.

This module contains all paths, column mappings, and constants used
across the data processing scripts.
"""

import os

# =============================================================================
# BASE PATHS
# =============================================================================

# Get the project root (parent of scripts/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Data directories
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
RAW_DIR = os.path.join(DATA_DIR, 'raw')
INTERMEDIATE_DIR = os.path.join(DATA_DIR, 'intermediate')
IMPORT_READY_DIR = os.path.join(DATA_DIR, 'import_ready')

# =============================================================================
# RAW FILE PATHS
# =============================================================================

RAW_GR_FILE = os.path.join(RAW_DIR, 'gr table.csv')
RAW_INVOICE_FILE = os.path.join(RAW_DIR, 'invoice table.csv')
RAW_PO_LINE_ITEMS_FILE = os.path.join(RAW_DIR, 'po line items.csv')

# =============================================================================
# INTERMEDIATE FILE PATHS
# =============================================================================

INTERMEDIATE_GR_CLEANED = os.path.join(INTERMEDIATE_DIR, 'gr_cleaned.csv')
INTERMEDIATE_INVOICE_CLEANED = os.path.join(INTERMEDIATE_DIR, 'invoice_cleaned.csv')
INTERMEDIATE_PO_LOOKUP = os.path.join(INTERMEDIATE_DIR, 'po_cost_recognition_lookup.csv')

# =============================================================================
# IMPORT-READY FILE PATHS
# =============================================================================

IMPORT_READY_PO_TRANSACTIONS = os.path.join(IMPORT_READY_DIR, 'po_transactions.csv')

# =============================================================================
# COLUMN MAPPINGS - RAW TO STANDARDIZED
# =============================================================================

# GR Table columns (raw -> clean)
GR_COLUMNS = {
    'po_line_id': 'po_line_id',
    'gr_posting_date': 'gr_posting_date',
    'gr_line': 'gr_line',
    'gr_effective_quantity': 'gr_effective_quantity',
    'gr_amount_usd': 'gr_amount_usd',
}

# Invoice Table columns (raw -> clean)
INVOICE_COLUMNS = {
    'po_line_id': 'po_line_id',
    'invoice_posting_date': 'invoice_posting_date',
    'ir_effective_quantity': 'ir_effective_quantity',
    'ir_amount_usd': 'ir_amount_usd',
}

# PO Line Items columns used for cost recognition lookup
PO_LINE_ITEMS_COLUMNS = {
    'po_line_id': 'PO Line ID',
    'vendor_category': 'Main Vendor SLB Vendor Category',
    'account_assignment': 'PO Account Assignment Category',
}

# =============================================================================
# BUSINESS RULES - COST RECOGNITION
# =============================================================================

# Cost is recognized at GR (Goods Receipt) if:
#   1. Main Vendor SLB Vendor Category = "3rd Party"
#   OR
#   2. PO Account Assignment Category IN ("P", "K") AND Main Vendor SLB Vendor Category = "GLD"
#
# Otherwise, cost is recognized at IR (Invoice Receipt)

VENDOR_CATEGORY_3RD_PARTY = '3rd Party'
VENDOR_CATEGORY_GLD = 'GLD'
ACCOUNT_ASSIGNMENTS_FOR_GLD = ['P', 'K']

# =============================================================================
# OUTPUT SCHEMA - MATCHES DB SCHEMA
# =============================================================================

# Final po_transactions columns (matching src/schema/po-transactions.ts)
PO_TRANSACTIONS_SCHEMA = {
    'po_line_id': str,           # Will be linked to po_line_items.id later
    'transaction_type': str,      # 'GR' or 'Invoice'
    'posting_date': str,          # Date of transaction
    'quantity': float,            # Transaction quantity
    'amount': float,              # Transaction amount (USD)
    'is_cost_recognized': bool,   # Whether this transaction hits the P&L
    'reference_number': str,      # Optional reference
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def ensure_directories():
    """Create all required directories if they don't exist."""
    for directory in [RAW_DIR, INTERMEDIATE_DIR, IMPORT_READY_DIR]:
        os.makedirs(directory, exist_ok=True)


def print_config():
    """Print current configuration for debugging."""
    print("=" * 60)
    print("PIPELINE CONFIGURATION")
    print("=" * 60)
    print(f"Project Root:     {PROJECT_ROOT}")
    print(f"Raw Data:         {RAW_DIR}")
    print(f"Intermediate:     {INTERMEDIATE_DIR}")
    print(f"Import Ready:     {IMPORT_READY_DIR}")
    print("=" * 60)


if __name__ == '__main__':
    print_config()
