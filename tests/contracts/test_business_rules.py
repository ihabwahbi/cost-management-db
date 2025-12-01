"""
Business Rule Contract Tests

These tests encode business rules from COST_MANAGEMENT_LOGIC.md that must ALWAYS be true.
They catch logic errors that Pandera schema validation cannot detect.

Run: .venv/bin/pytest tests/contracts/test_business_rules.py -v
"""

import pandas as pd
import pytest
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
IMPORT_READY = PROJECT_ROOT / "data" / "import-ready"
INTERMEDIATE = PROJECT_ROOT / "data" / "intermediate"


# =============================================================================
# GRIR Exposure Business Rules (COST_MANAGEMENT_LOGIC.md lines 162-185)
# =============================================================================

class TestGRIRBusinessRules:
    """
    Business rules for GRIR Exposures.
    
    GRIR tracks the difference between invoiced and goods-received quantities
    for Type 1 (Simple) POs only. These rules are critical for balance sheet accuracy.
    """

    @pytest.fixture
    def grir_with_po_data(self):
        """Load GRIR exposures joined with PO line items for rule validation."""
        grir_file = IMPORT_READY / "grir_exposures.csv"
        po_file = INTERMEDIATE / "po_line_items.csv"
        
        if not grir_file.exists():
            pytest.skip("GRIR exposures file not found")
        if not po_file.exists():
            pytest.skip("PO line items file not found")
        
        grir = pd.read_csv(grir_file)
        po = pd.read_csv(po_file)
        
        # Skip if no GRIR data
        if len(grir) == 0:
            pytest.skip("No GRIR exposures to validate")
        
        return grir.merge(po, left_on="po_line_id", right_on="PO Line ID", how="left")

    def test_no_closed_po_exposures(self, grir_with_po_data):
        """
        CLOSED POs cannot have GRIR exposure.
        
        Business Rule: PO Receipt Status ≠ "CLOSED PO"
        Reason: Closed POs are fully settled - no future NIS impact possible.
        Source: COST_MANAGEMENT_LOGIC.md line 165
        """
        df = grir_with_po_data
        closed_pos = df[df["PO Receipt Status"] == "CLOSED PO"]
        
        assert len(closed_pos) == 0, (
            f"Found {len(closed_pos)} CLOSED PO exposures. "
            f"PO Line IDs: {closed_pos['po_line_id'].head(5).tolist()}"
        )

    def test_only_gld_vendor_category(self, grir_with_po_data):
        """
        GRIR only applies to GLD (Simple) vendor category.
        
        Business Rule: Main Vendor SLB Vendor Category = "GLD"
        Reason: Only Type 1 POs have GRIR exposure (Type 2 recognizes IR immediately).
        Source: COST_MANAGEMENT_LOGIC.md lines 162-163
        """
        df = grir_with_po_data
        non_gld = df[df["Main Vendor SLB Vendor Category"] != "GLD"]
        
        assert len(non_gld) == 0, (
            f"Found {len(non_gld)} non-GLD vendor exposures. "
            f"Categories found: {non_gld['Main Vendor SLB Vendor Category'].unique().tolist()}"
        )

    def test_only_valid_account_categories(self, grir_with_po_data):
        """
        GRIR only applies to specific account assignment categories.
        
        Business Rule: PO Account Assignment Category IN ("K", "P", "S", "V")
        Reason: These are the "Simple PO" categories for Type 1 classification.
        Source: COST_MANAGEMENT_LOGIC.md line 164
        """
        df = grir_with_po_data
        valid_categories = {"K", "P", "S", "V"}
        
        # Handle NaN values
        df_with_cat = df[df["PO Account Assignment Category"].notna()]
        invalid = df_with_cat[~df_with_cat["PO Account Assignment Category"].isin(valid_categories)]
        
        assert len(invalid) == 0, (
            f"Found {len(invalid)} exposures with invalid account categories. "
            f"Invalid categories: {invalid['PO Account Assignment Category'].unique().tolist()}"
        )

    def test_positive_grir_qty(self):
        """
        GRIR quantity must be positive (IR > GR).
        
        Business Rule: GRIR Qty > 0
        Reason: Negative GRIR means GR > IR, which is not an exposure.
        Source: COST_MANAGEMENT_LOGIC.md line 173
        """
        grir_file = IMPORT_READY / "grir_exposures.csv"
        if not grir_file.exists():
            pytest.skip("GRIR exposures file not found")
        
        df = pd.read_csv(grir_file)
        if len(df) == 0:
            pytest.skip("No GRIR exposures to validate")
        
        non_positive = df[df["grir_qty"] <= 0]
        
        assert len(non_positive) == 0, (
            f"Found {len(non_positive)} non-positive GRIR quantities. "
            f"Min value: {df['grir_qty'].min()}"
        )

    def test_valid_time_buckets(self):
        """
        Time bucket must be one of the defined aging categories.
        
        Business Rule: Valid buckets for risk assessment
        Source: COST_MANAGEMENT_LOGIC.md lines 179-185
        """
        grir_file = IMPORT_READY / "grir_exposures.csv"
        if not grir_file.exists():
            pytest.skip("GRIR exposures file not found")
        
        df = pd.read_csv(grir_file)
        if len(df) == 0:
            pytest.skip("No GRIR exposures to validate")
        
        valid_buckets = {"<1 month", "1-3 months", "3-6 months", "6-12 months", ">1 year"}
        invalid = df[~df["time_bucket"].isin(valid_buckets)]
        
        assert len(invalid) == 0, (
            f"Found {len(invalid)} invalid time buckets. "
            f"Invalid values: {invalid['time_bucket'].unique().tolist()}"
        )


# =============================================================================
# PO Line Items Business Rules (COST_MANAGEMENT_LOGIC.md lines 37-49)
# =============================================================================

class TestPOLineItemsBusinessRules:
    """
    Business rules for PO Line Items cleaning.
    
    These rules ensure excluded data doesn't leak into the pipeline.
    """

    @pytest.fixture
    def po_line_items(self):
        """Load cleaned PO line items."""
        po_file = INTERMEDIATE / "po_line_items.csv"
        if not po_file.exists():
            pytest.skip("PO line items file not found")
        return pd.read_csv(po_file)

    def test_excluded_valuation_classes(self, po_line_items):
        """
        Excluded valuation classes must not appear in cleaned data.
        
        Business Rule: Exclude valuation classes 7800, 7900, 5008
        Reason: These are non-NIS impacting categories.
        Source: COST_MANAGEMENT_LOGIC.md line 39
        """
        excluded = {7800, 7900, 5008}
        
        if "PO Valuation Class" not in po_line_items.columns:
            pytest.skip("PO Valuation Class column not found")
        
        found = po_line_items[po_line_items["PO Valuation Class"].isin(excluded)]
        
        assert len(found) == 0, (
            f"Found {len(found)} rows with excluded valuation classes. "
            f"Classes found: {found['PO Valuation Class'].unique().tolist()}"
        )

    def test_excluded_nis_descriptions(self, po_line_items):
        """
        Excluded NIS descriptions must not appear in cleaned data.
        
        Business Rule: Exclude "Compensation Business Delivery/Enablement"
        Reason: These are compensation-related, not procurement costs.
        Source: COST_MANAGEMENT_LOGIC.md line 40
        """
        excluded = {
            "Compensation Business Delivery",
            "Compensation Business Enablement"
        }
        
        nis_col = "NIS Level 0 Desc"
        if nis_col not in po_line_items.columns:
            # Try alternate column name
            nis_col = "NIS Line"
            if nis_col not in po_line_items.columns:
                pytest.skip("NIS description column not found")
        
        found = po_line_items[po_line_items[nis_col].isin(excluded)]
        
        assert len(found) == 0, (
            f"Found {len(found)} rows with excluded NIS descriptions. "
            f"Descriptions found: {found[nis_col].unique().tolist()}"
        )


# =============================================================================
# PO Transactions Business Rules (COST_MANAGEMENT_LOGIC.md lines 85-92)
# =============================================================================

class TestPOTransactionsBusinessRules:
    """
    Business rules for PO Transactions (cost impact).
    """

    def test_valid_transaction_types(self):
        """
        Transaction type must be GR or IR.
        
        Business Rule: Only GR and IR postings are valid
        Source: COST_MANAGEMENT_LOGIC.md lines 96-123
        """
        txn_file = IMPORT_READY / "po_transactions.csv"
        if not txn_file.exists():
            pytest.skip("PO transactions file not found")
        
        df = pd.read_csv(txn_file)
        valid_types = {"GR", "IR"}
        invalid = df[~df["transaction_type"].isin(valid_types)]
        
        assert len(invalid) == 0, (
            f"Found {len(invalid)} invalid transaction types. "
            f"Invalid values: {invalid['transaction_type'].unique().tolist()}"
        )


# =============================================================================
# Cross-Table Referential Integrity
# =============================================================================

class TestReferentialIntegrity:
    """
    Cross-table business rules ensuring data consistency.
    """

    def test_grir_po_line_ids_exist_in_po_line_items(self):
        """
        All GRIR po_line_ids must exist in PO line items.
        
        Business Rule: Referential integrity between tables
        Reason: Orphan GRIR records indicate data pipeline issues.
        """
        grir_file = IMPORT_READY / "grir_exposures.csv"
        po_file = IMPORT_READY / "po_line_items.csv"
        
        if not grir_file.exists() or not po_file.exists():
            pytest.skip("Required files not found")
        
        grir = pd.read_csv(grir_file)
        po = pd.read_csv(po_file)
        
        if len(grir) == 0:
            pytest.skip("No GRIR exposures to validate")
        
        grir_ids = set(grir["po_line_id"])
        po_ids = set(po["po_line_id"])
        orphans = grir_ids - po_ids
        
        assert len(orphans) == 0, (
            f"Found {len(orphans)} GRIR records with no matching PO line item. "
            f"Orphan IDs: {list(orphans)[:5]}"
        )

    def test_transactions_po_line_ids_exist_in_po_line_items(self):
        """
        All transaction po_line_ids must exist in PO line items.
        
        Business Rule: Referential integrity between tables
        """
        txn_file = IMPORT_READY / "po_transactions.csv"
        po_file = IMPORT_READY / "po_line_items.csv"
        
        if not txn_file.exists() or not po_file.exists():
            pytest.skip("Required files not found")
        
        txn = pd.read_csv(txn_file)
        po = pd.read_csv(po_file)
        
        txn_ids = set(txn["po_line_id"])
        po_ids = set(po["po_line_id"])
        orphans = txn_ids - po_ids
        
        assert len(orphans) == 0, (
            f"Found {len(orphans)} transaction records with no matching PO line item. "
            f"Orphan IDs: {list(orphans)[:5]}"
        )
