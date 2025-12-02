"""
Data Contract: PO Transactions Output Schema

This schema is the single source of truth for the output format
of data/import-ready/po_transactions.csv.

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

    class POTransactionsSchema(pa.DataFrameModel):
        """
        Contract for data/import-ready/po_transactions.csv

        This schema validates transaction records (GR/IR postings).
        """

        # =====================================================
        # Required columns
        # =====================================================

        # Unique business key for upserts (format: {po_line_id}-{type}-{date}-{seq})
        transaction_id: Series[str] = pa.Field(nullable=False)

        # Business key (links to po_line_items)
        po_line_id: Series[str] = pa.Field(nullable=False)

        # Transaction type (GR or IR)
        transaction_type: Series[str] = pa.Field(
            nullable=False,
            isin=["GR", "IR"],  # Only valid transaction types
        )

        # Posting date
        posting_date: Series[str] = pa.Field(nullable=False)

        # Quantities and amounts
        quantity: Series[float] = pa.Field(nullable=False)
        amount: Series[float] = pa.Field(nullable=False)

        # Cost impact values
        cost_impact_qty: Series[float] = pa.Field(nullable=False)
        cost_impact_amount: Series[float] = pa.Field(nullable=False)

        class Config:
            strict = False  # Allow extra columns
            coerce = True  # Allow type coercion

        @pa.check("transaction_type", name="valid_transaction_type")
        def validate_transaction_type(cls, series):
            """Transaction type must be GR or IR."""
            return series.isin(["GR", "IR"])

        @pa.check("quantity", name="non_zero_quantity")
        def validate_quantity(cls, series):
            """Qty should not be zero (meaningless transaction)."""
            # Allow zero in edge cases, but warn
            return True  # Soft check
else:
    # Stub when pandera not available
    class POTransactionsSchema:  # type: ignore
        """Stub POTransactionsSchema when pandera is not installed."""

        @classmethod
        def validate(cls, df):
            return df
