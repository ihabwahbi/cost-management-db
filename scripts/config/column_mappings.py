"""
Column Mappings Configuration

Central source of truth for CSV column → Database column mappings.
Used by stage3_prepare scripts to create import-ready files.

Naming conventions:
- CSV columns: Original names from source files (mixed case, spaces)
- DB columns: snake_case matching Drizzle schema
"""

# =============================================================================
# PO LINE ITEMS: Intermediate CSV → Database columns
# =============================================================================
PO_LINE_ITEMS_MAPPING = {
    # Business key
    "PO Line ID": "po_line_id",
    
    # PO Header fields
    "PO Number": "po_number",
    "PO Document Date": "po_creation_date",
    "Plant Code": "plant_code",
    "Location": "location",
    "SL Sub-Business Line Code (BV Lvl 3)": "sub_business_line",
    
    # Purchase Requisition
    "PR Number": "pr_number",
    "PR Line": "pr_line",
    "Requester": "requester",
    
    # Vendor information
    "Main Vendor ID": "vendor_id",
    "Main Vendor Name": "vendor_name",
    "Main Vendor SLB Vendor Category": "vendor_category",
    "Ultimate Vendor Name": "ultimate_vendor_name",
    
    # Line item fields
    "PO Line": "line_item_number",
    "PO Material Number": "part_number",
    "PO Material description": "description",
    "Ordered Quantity": "ordered_qty",
    "PO Order Unit": "order_unit",
    "Purchase Value USD": "po_value_usd",
    
    # Cost classification
    "PO Account Assignment Category": "account_assignment_category",
    "NIS Line": "nis_line",
    "PO WBS Element": "wbs_number",
    
    # Asset reference (placeholder - not in current CSV)
    # "Asset Code": "asset_code",
    
    # Dates
    "Expected Delivery Date": "expected_delivery_date",
    
    # Status flags
    "PO Approval Status": "po_approval_status",
    "PO Receipt Status": "po_receipt_status",
    "PO GTS Status": "po_gts_status",
    # "FMT PO": "fmt_po",  # Calculated field
    
    # Open PO values (calculated in stage3 from cost_impact)
    # "Open PO Qty": "open_po_qty",
    # "Open PO Value": "open_po_value",
}

# Columns that are calculated/derived in stage3 (not from source CSV)
PO_LINE_ITEMS_CALCULATED = [
    "open_po_qty",      # ordered_qty - SUM(cost_impact_qty)
    "open_po_value",    # po_value_usd - SUM(cost_impact_amount)
    "fmt_po",           # Boolean flag (default False for now)
]


# =============================================================================
# PO TRANSACTIONS: Cost Impact CSV → Database columns
# =============================================================================
PO_TRANSACTIONS_MAPPING = {
    "PO Line ID": "po_line_id",  # Used to lookup po_line_item_id
    "Posting Type": "transaction_type",
    "Posting Date": "posting_date",
    "Posting Qty": "quantity",
    # "Posting Amount": "amount",  # Need to add this to cost_impact.csv
    "Cost Impact Qty": "cost_impact_qty",
    "Cost Impact Amount": "cost_impact_amount",
}


# =============================================================================
# VALIDATION: Required columns for each import-ready file
# =============================================================================
REQUIRED_COLUMNS = {
    "po_line_items": [
        "po_line_id",
        "po_number",
        "line_item_number",
        "ordered_qty",
        "po_value_usd",
    ],
    "po_transactions": [
        "po_line_id",  # Will be converted to po_line_item_id during import
        "transaction_type",
        "posting_date",
        "quantity",
        "cost_impact_qty",
        "cost_impact_amount",
    ],
    "grir_exposures": [
        "po_line_id",  # Will be converted to po_line_item_id during import
        "grir_qty",
        "grir_value",
        "snapshot_date",
    ],
}


# =============================================================================
# BUSINESS RULES: Transformations and defaults
# =============================================================================

# Vendor ID → Vendor Name mappings (for hub vendors)
VENDOR_NAME_MAPPING = {
    "P9516": "Dubai Hub",
    "P9109": "Houston Hub",
    "P9517": "Shanghai Hub",
    "P9518": "Singapore Hub",
    "P9514": "Canada Hub",
    "P9519": "Japan Hub",
    "P9097": "Rotterdam Hub",
    "P9107": "NAM RDC",
    "P9071": "PPCU",
    "P9052": "SRC",
    "P9057": "SKK",
    "P9060": "SRPC",
    "P9036": "HFE",
    "P9035": "HCS",
    "P9086": "ONESUBSEA",
    "P9064": "PPCS",
    "P9066": "SWTC",
    "P9562": "QRTC",
    "P9032": "FCS",
}

# Plant Code → Location mappings
PLANT_CODE_TO_LOCATION = {
    "3601": "Perth",
    "3606": "Jandakot",
    "3608": "Kewdale",
    "3609": "Toowoomba",
    "3610": "Roma",
    "3611": "Dampier",
    "3613": "Roma",
    "3614": "Moomba",
    "3617": "Brisbane",
    "3649": "Port Moresby",
    "3650": "New Plymouth",
    "3651": "Dili",
    "3880": "Port Moresby",
    "3881": "New Plymouth",
    "3882": "Jandakot",
    "3892": "Roma",
    "3893": "Dampier",
    "3916": "Adelaide",
    "4039": "Roma",
    "4062": "Toowoomba",
    "4063": "Dampier",
}

# Valuation classes to exclude during cleaning
EXCLUDED_VALUATION_CLASSES = [7800, 7900, 5008]

# NIS Level descriptions to exclude during cleaning
EXCLUDED_NIS_LEVELS = [
    "Compensation Business Delivery",
    "Compensation Business Enablement",
]

# Classification for simple cost impact (Type 1) - also used for GRIR
SIMPLE_VENDOR_CATEGORY = "GLD"
SIMPLE_ACCOUNT_CATEGORIES = ["K", "P", "S", "V"]


# =============================================================================
# GRIR EXPOSURES: GRIR CSV → Database columns
# =============================================================================
GRIR_EXPOSURES_MAPPING = {
    "PO Line ID": "po_line_id",  # Used to lookup po_line_item_id
    "GRIR Qty": "grir_qty",
    "GRIR Value": "grir_value",
    "First Exposure Date": "first_exposure_date",
    "Days Open": "days_open",
    "Time Bucket": "time_bucket",
    "Snapshot Date": "snapshot_date",
}

# Time bucket thresholds (in days)
GRIR_TIME_BUCKETS = {
    30: "<1 month",
    90: "1-3 months",
    180: "3-6 months",
    365: "6-12 months",
}
GRIR_TIME_BUCKET_MAX = ">1 year"
