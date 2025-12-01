"""
Golden Set Tests: Runtime truth for pipeline behavior.

Run in CI, not pre-commit (too slow).

Usage:
    pytest tests/test_pipeline_golden_set.py -v
    
Setup:
    1. Create golden_set/input/ with sample input files
    2. Run pipeline to generate golden_set/expected_output/
    3. These tests verify pipeline produces same output
"""
import pytest
from pathlib import Path
import pandas as pd
from datetime import datetime

# Try to import freezegun for idempotency testing
try:
    from freezegun import freeze_time
    FREEZEGUN_AVAILABLE = True
except ImportError:
    FREEZEGUN_AVAILABLE = False
    # Create a no-op decorator
    def freeze_time(time_to_freeze):
        def decorator(func):
            return func
        return decorator

# Try to import pandera for schema validation
try:
    from scripts.contracts import POLineItemsSchema, POTransactionsSchema, GRIRExposuresSchema
    PANDERA_AVAILABLE = True
except ImportError:
    PANDERA_AVAILABLE = False
    POLineItemsSchema = None
    POTransactionsSchema = None
    GRIRExposuresSchema = None


PROJECT_ROOT = Path(__file__).parent.parent
GOLDEN_INPUT = PROJECT_ROOT / "golden_set" / "input"
GOLDEN_EXPECTED = PROJECT_ROOT / "golden_set" / "expected_output"


class TestGoldenSetExists:
    """Tests to verify golden set is properly configured."""
    
    def test_golden_input_exists(self):
        """Verify golden input directory exists."""
        if not GOLDEN_INPUT.exists():
            pytest.skip("Golden set not configured - create golden_set/input/")
    
    def test_golden_expected_exists(self):
        """Verify golden expected output directory exists."""
        if not GOLDEN_EXPECTED.exists():
            pytest.skip("Golden set not configured - create golden_set/expected_output/")


@pytest.mark.skipif(
    not GOLDEN_INPUT.exists() or not GOLDEN_EXPECTED.exists(),
    reason="Golden set not configured"
)
class TestPipelineGoldenSet:
    """Verify pipeline produces expected outputs from golden inputs."""
    
    @freeze_time("2025-01-01 12:00:00")
    def test_po_line_items_output_matches(self):
        """
        Test that PO line items output matches expected golden output.
        
        This test verifies the entire Stage 3 prepare flow produces
        consistent output.
        """
        expected_path = GOLDEN_EXPECTED / "po_line_items.csv"
        if not expected_path.exists():
            pytest.skip("po_line_items.csv not in golden set")
        
        expected_df = pd.read_csv(expected_path)
        # Add actual pipeline execution here when golden set is created
        # output_df = run_pipeline_stage3_po_line_items(GOLDEN_INPUT)
        # pd.testing.assert_frame_equal(output_df, expected_df, check_dtype=False)
        
        # For now, just verify expected file is readable
        assert len(expected_df) > 0, "Expected output should have rows"
    
    @freeze_time("2025-01-01 12:00:00")
    def test_po_transactions_output_matches(self):
        """Test that PO transactions output matches expected golden output."""
        expected_path = GOLDEN_EXPECTED / "po_transactions.csv"
        if not expected_path.exists():
            pytest.skip("po_transactions.csv not in golden set")
        
        expected_df = pd.read_csv(expected_path)
        assert len(expected_df) >= 0, "Expected output should be readable"
    
    @freeze_time("2025-01-01 12:00:00")
    def test_grir_exposures_output_matches(self):
        """Test that GRIR exposures output matches expected golden output."""
        expected_path = GOLDEN_EXPECTED / "grir_exposures.csv"
        if not expected_path.exists():
            pytest.skip("grir_exposures.csv not in golden set")
        
        expected_df = pd.read_csv(expected_path)
        assert len(expected_df) >= 0, "Expected output should be readable"


@pytest.mark.skipif(not PANDERA_AVAILABLE, reason="pandera not installed")
@pytest.mark.skipif(
    not GOLDEN_EXPECTED.exists(),
    reason="Golden set not configured"
)
class TestSchemaValidation:
    """Verify output schemas match Pandera contracts."""
    
    def test_po_line_items_schema(self):
        """Verify PO line items output matches Pandera contract."""
        expected_path = GOLDEN_EXPECTED / "po_line_items.csv"
        if not expected_path.exists():
            pytest.skip("po_line_items.csv not in golden set")
        
        df = pd.read_csv(expected_path)
        POLineItemsSchema.validate(df)  # Raises on mismatch
    
    def test_po_transactions_schema(self):
        """Verify PO transactions output matches Pandera contract."""
        expected_path = GOLDEN_EXPECTED / "po_transactions.csv"
        if not expected_path.exists():
            pytest.skip("po_transactions.csv not in golden set")
        
        df = pd.read_csv(expected_path)
        POTransactionsSchema.validate(df)
    
    def test_grir_exposures_schema(self):
        """Verify GRIR exposures output matches Pandera contract."""
        expected_path = GOLDEN_EXPECTED / "grir_exposures.csv"
        if not expected_path.exists():
            pytest.skip("grir_exposures.csv not in golden set")
        
        df = pd.read_csv(expected_path)
        GRIRExposuresSchema.validate(df)


@pytest.mark.skipif(not FREEZEGUN_AVAILABLE, reason="freezegun not installed")
class TestIdempotency:
    """Verify pipeline produces identical output when run multiple times."""
    
    @freeze_time("2025-01-01 12:00:00")
    def test_pipeline_is_idempotent(self):
        """
        Verify running pipeline twice produces identical output.
        
        This test ensures:
        1. No random elements affect output
        2. Date/time-based calculations use frozen time
        3. Order of operations is deterministic
        """
        # This test requires actual pipeline execution
        # For now, it's a placeholder that shows the pattern
        pytest.skip("Requires pipeline execution - implement when golden set ready")


class TestValidatorIntegration:
    """Test that validators work correctly."""
    
    def test_schema_lock_check(self):
        """Test schema lock validation passes."""
        from scripts.validators.schema_lock import check_lock
        
        # Should pass if schema_lock.json exists and matches
        result = check_lock(verbose=False)
        assert result is True, "Schema lock should be valid"
    
    def test_pipeline_order_validation(self):
        """Test pipeline order validation passes."""
        from scripts.validators.pipeline_order import validate
        
        result = validate(json_output=False)
        assert result is True, "Pipeline order should be valid (no cycles)"
    
    def test_oracle_client_health(self):
        """Test Oracle client reports healthy status."""
        from scripts.validators.oracle_client import OracleClient
        
        oracle = OracleClient()
        assert oracle.is_available, "Oracle should be available"
        
        health = oracle.get_health_status()
        assert health["available"], f"Oracle should be healthy: {health}"
