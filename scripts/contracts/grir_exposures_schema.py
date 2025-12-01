"""
Data Contract: GRIR Exposures Output Schema

This schema is the single source of truth for the output format
of data/import-ready/grir_exposures.csv.

GRIR = Goods Receipt / Invoice Receipt exposure (when IR > GR)

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

    class GRIRExposuresSchema(pa.DataFrameModel):
        """
        Contract for data/import-ready/grir_exposures.csv

        This schema validates GRIR exposure records.
        """

        # =====================================================
        # Required columns
        # =====================================================

        # Business key (links to po_line_items)
        po_line_id: Series[str] = pa.Field(nullable=False)

        # GRIR values (exposure = IR - GR when IR > GR)
        grir_qty: Series[float] = pa.Field(nullable=False, ge=0)
        grir_value: Series[float] = pa.Field(nullable=False, ge=0)

        # Dates
        first_exposure_date: Series[str] = pa.Field(nullable=True)
        snapshot_date: Series[str] = pa.Field(nullable=False)

        # Aging
        days_open: Series[int] = pa.Field(nullable=False, ge=0)
        time_bucket: Series[str] = pa.Field(
            nullable=False,
            isin=["<1 month", "1-3 months", "3-6 months", "6-12 months", ">1 year"],
        )

        class Config:
            strict = False  # Allow extra columns
            coerce = True  # Allow type coercion

        @pa.check("grir_qty", name="positive_grir_qty")
        def validate_grir_qty(cls, series):
            """GRIR quantity should be positive (exposure only when IR > GR)."""
            return series >= 0

        @pa.check("grir_value", name="positive_grir_value")
        def validate_grir_value(cls, series):
            """GRIR value should be positive."""
            return series >= 0

        @pa.check("time_bucket", name="valid_time_bucket")
        def validate_time_bucket(cls, series):
            """Time bucket must be one of the valid values."""
            valid_buckets = [
                "<1 month",
                "1-3 months",
                "3-6 months",
                "6-12 months",
                ">1 year",
            ]
            return series.isin(valid_buckets)
else:
    # Stub when pandera not available
    class GRIRExposuresSchema:  # type: ignore
        """Stub GRIRExposuresSchema when pandera is not installed."""

        @classmethod
        def validate(cls, df):
            return df
