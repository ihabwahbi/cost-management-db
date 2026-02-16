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
    "open_po_qty",  # ordered_qty - SUM(cost_impact_qty)
    "open_po_value",  # po_value_usd - SUM(cost_impact_amount)
    "fmt_po",  # Boolean flag (True when vendor_category = OPS)
    "wbs_validated",  # True if wbs_number exists in wbs_details
    "is_capex",  # True if WBS starts with 'C.' (capitalized, doesn't hit P&L)
    "cost_impact_value",  # po_value_usd - open_po_value (total cost impact recognized)
    "cost_impact_pct",  # cost_impact_value / po_value_usd [0,1], NULL when po_value=0
    # Pre-computed status flags (calculated in stage3)
    "is_gts_blocked",  # po_gts_status contains 'GTS Blocked'
    "is_approval_blocked",  # po_approval_status is 'Blocked'
    "is_effectively_closed",  # CLOSED PO or (qty=0 AND value=0)
    "po_lifecycle_status",  # open|closed|gts_blocked|pending_approval
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

# Columns generated in stage3 for po_transactions (not from source CSV)
PO_TRANSACTIONS_GENERATED = [
    "transaction_id",  # Unique business key: {po_line_id}-{type}-{date}-{seq}
    "amount",  # Copy of cost_impact_amount (posting amount)
]


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
        "transaction_id",  # Unique business key for upserts
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
    "sap_reservations": [
        "reservation_line_id",
        "reservation_number",
        "reservation_line_number",
        "open_reservation_qty",
        "open_reservation_value",
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

# Plant Code → Location mappings (legacy - for PO data)
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

# Ops District → Location mappings (for WBS data from FDP reports)
OPS_DISTRICT_TO_LOCATION = {
    "APG TS": "Jandakot",
    "AUS East Coast WS": "Roma",
    "AUS West Coast WS": "Jandakot",
    "Moomba WL": "Moomba",
    "New Burn WL": "Jandakot",
    "New Plymouth TS": "New Plymouth",
    "New Plymouth WL": "New Plymouth",
    "New Plymouth WS": "New Plymouth",
    "Port Moresby TS": "Port Moresby",
    "Port Moresby WL": "Port Moresby",
    "Roma WL": "Roma",
}

# Sub Business Line full name → SBL code mappings (for Ops Activities)
# These map the explicit "Sub Business Line" column values to SBL codes
SBL_NAME_TO_CODE = {
    "TCP - Tubing-Conveyed Perforation": "TCPF",
    "TCP-Tubing-Conveyed Perforation": "TCPF",
    "TS Downhole Reservoir Testing": "DHT",
    "TS Laboratories": "LABR",
    "TS Production Testing": "PSV",
    "TS Surface Testing": "TSW",
    "Wireline Slickline": "SLKN",
    "WL Evaluation Services": "WLES",
    "WL Production Services": "WLPS",
    "WS Production Services": "WPS",
    "WS Well Integrity": "WIT",
    "WS Well Intervention": "WIS",
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


# =============================================================================
# WBS DETAILS: Intermediate CSV → Database columns
# =============================================================================
WBS_DETAILS_MAPPING = {
    # Primary business key (globally unique across all FDP reports)
    "wbs_number": "wbs_number",
    # Source tracking
    "wbs_source": "wbs_source",  # Project, Operation, Operation Activity
    # Source identifiers
    "project_number": "project_number",
    "operation_number": "operation_number",
    "ops_activity_number": "ops_activity_number",
    # Descriptive fields
    "wbs_name": "wbs_name",
    "client_name": "client_name",
    # Equipment and location
    "rig": "rig",
    "ops_district": "ops_district",  # e.g., "Roma WL", "Moomba WL"
    "location": "location",  # Mapped from ops_district
    # Business classification (JSON array in CSV -> PostgreSQL text[] in DB)
    "sub_business_lines": "sub_business_lines",
}


# =============================================================================
# SAP RESERVATIONS: Intermediate CSV → Database columns
# =============================================================================
SAP_RESERVATIONS_MAPPING = {
    # Business key (created in stage 1)
    "reservation_line_id": "reservation_line_id",
    # Split components (created in stage 1)
    "reservation_number": "reservation_number",
    "reservation_line_number": "reservation_line_number",
    # Dates
    "Creation Date": "reservation_creation_date",
    "Requirements Date": "reservation_requirement_date",
    # Material info
    "Material": "part_number",
    "Material Description": "description",
    # Open values (renamed in DB schema)
    "Open Qty - Reservation": "open_reservation_qty",
    "Open Reservation Value": "open_reservation_value",
    # Status and source
    "Combined SOH & PO Pegging": "reservation_status",
    "Reservation Creation type": "reservation_source",
    # WBS reference
    "WBS Element": "wbs_number",
    # Requester (renamed in DB schema)
    "Goods recipient": "requester_alias",
    # Plant (needs float -> string conversion in stage3)
    "Plant": "plant_code",
}

# Columns derived/extracted in stage3 (not direct mappings)
SAP_RESERVATIONS_DERIVED = {
    # Extracted from "Main - PO Line to Peg to Reservation" (e.g., "4584632148-1")
    "po_number": "Extract before '-' from Main - PO Line to Peg to Reservation",
    "po_line_number": "Extract after '-' from Main - PO Line to Peg to Reservation",
    "po_line_item_id": "Full value from Main - PO Line to Peg to Reservation",
    # Extracted from "Maximo Asset Num" (e.g., "XPS-CA|941")
    "asset_code": "Extract before '|' from Maximo Asset Num",
    "asset_serial_number": "Extract after '|' from Maximo Asset Num",
}
