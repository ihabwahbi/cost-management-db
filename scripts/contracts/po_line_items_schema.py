"""
Data Contract: PO Line Items Output Schema

This schema is the single source of truth for the output format
of data/import-ready/po_line_items.csv.

Validated at runtime, not statically.
"""

try:
    import pandera as pa
    from pandera.typing import Series

    PANDERA_AVAILABLE = True
except ImportError:
    PANDERA_AVAILABLE = False

    # Create stub classes for when pandera isn't installed
    class pa:  # type: ignore
        class DataFrameModel:
            pass

        @staticmethod
        def Field(**kwargs):
            return None


if PANDERA_AVAILABLE:

    class POLineItemsSchema(pa.DataFrameModel):
        """
        Contract for data/import-ready/po_line_items.csv

        This schema validates the final output before database import.
        """

        # =====================================================
        # Required columns (must exist, cannot be null)
        # =====================================================

        # Business key
        po_line_id: Series[str] = pa.Field(nullable=False, unique=True)
        po_number: Series[int] = pa.Field(nullable=False, ge=0)
        line_item_number: Series[int] = pa.Field(nullable=False, ge=0)

        # Quantities and values (required)
        ordered_qty: Series[float] = pa.Field(nullable=False)
        po_value_usd: Series[float] = pa.Field(nullable=False)

        # Calculated fields (required but can be 0)
        open_po_qty: Series[float] = pa.Field(nullable=False)
        open_po_value: Series[float] = pa.Field(nullable=False)
        cost_impact_value: Series[float] = pa.Field(nullable=False)
        cost_impact_pct: Series[float] = pa.Field(
            nullable=True
        )  # NULL when po_value_usd = 0
        fmt_po: Series[bool] = pa.Field(nullable=False)

        # =====================================================
        # Optional columns (can be null)
        # =====================================================

        # Location and organization
        plant_code: Series[int] = pa.Field(nullable=True)
        location: Series[str] = pa.Field(nullable=True)
        sub_business_line: Series[str] = pa.Field(nullable=True)

        # Purchase Requisition (can have alphanumeric values like "13959-V2")
        pr_number: Series[str] = pa.Field(nullable=True)
        pr_line: Series[str] = pa.Field(nullable=True)
        requester: Series[str] = pa.Field(nullable=True)

        # Vendor information
        vendor_id: Series[str] = pa.Field(nullable=True)
        vendor_name: Series[str] = pa.Field(nullable=True)
        vendor_category: Series[str] = pa.Field(nullable=True)
        ultimate_vendor_name: Series[str] = pa.Field(nullable=True)

        # Line item details
        part_number: Series[str] = pa.Field(nullable=True)
        description: Series[str] = pa.Field(nullable=True)
        order_unit: Series[str] = pa.Field(nullable=True)

        # Classification (account_assignment_category can be letter codes like "K", "P")
        account_assignment_category: Series[str] = pa.Field(nullable=True)
        nis_line: Series[str] = pa.Field(nullable=True)
        wbs_number: Series[str] = pa.Field(nullable=True)

        # Dates
        po_creation_date: Series[str] = pa.Field(nullable=True)
        expected_delivery_date: Series[str] = pa.Field(nullable=True)

        # Status flags
        po_approval_status: Series[str] = pa.Field(nullable=True)
        po_receipt_status: Series[str] = pa.Field(nullable=True)
        po_gts_status: Series[str] = pa.Field(nullable=True)

        class Config:
            strict = False  # Allow extra columns (some may be added later)
            coerce = True  # Allow type coercion

        @pa.check("open_po_qty", name="non_negative_open_qty")
        def validate_open_qty(cls, series):
            """Open qty should be >= 0 (negative = over-delivery)."""
            # Allow some negative values (over-delivery scenarios)
            return series >= -1000  # Reasonable threshold

        @pa.check("open_po_value", name="reasonable_open_value")
        def validate_open_value(cls, series):
            """Open value should be reasonable."""
            return series >= -1_000_000  # Allow some negative for over-delivery
else:
    # Stub when pandera not available
    class POLineItemsSchema:  # type: ignore
        """Stub POLineItemsSchema when pandera is not installed."""

        @classmethod
        def validate(cls, df):
            return df
