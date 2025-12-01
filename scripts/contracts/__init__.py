"""
Data Contracts Package

Contains Pandera schema definitions for validating pipeline outputs.
These are the single source of truth for output data formats.

Usage:
    from scripts.contracts import POLineItemsSchema, POTransactionsSchema

    # Validate a DataFrame
    POLineItemsSchema.validate(df)

    # Use as a decorator
    @pa.check_output(POLineItemsSchema)
    def process_data(df):
        ...
"""

from .grir_exposures_schema import GRIRExposuresSchema
from .po_line_items_schema import POLineItemsSchema
from .po_transactions_schema import POTransactionsSchema

__all__ = [
    "POLineItemsSchema",
    "POTransactionsSchema",
    "GRIRExposuresSchema",
]
