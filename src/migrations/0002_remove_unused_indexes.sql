-- Remove unused indexes (0 scans in development)
-- Migration: remove_unused_indexes
-- Date: 2025-10-10
-- Status: DEFERRED - DO NOT EXECUTE YET
-- Rationale: Performance optimization (7 indexes with 0 usage detected)

-- ⚠️  IMPORTANT: This migration is DEFERRED
-- Monitor production for 30 days before executing
-- Review Date: 2025-11-10
-- See: packages/db/MAINTENANCE.md for monitoring instructions

-- NOTE: Only execute after 30-day production monitoring confirms zero usage

-- Unused indexes identified (0 scans in development):
DROP INDEX IF EXISTS idx_po_line_items_open_pos;
DROP INDEX IF EXISTS idx_projects_sub_business_line;
DROP INDEX IF EXISTS po_mappings_po_line_item_id_cost_breakdown_id_key;
DROP INDEX IF EXISTS idx_forecast_versions_version_number;
DROP INDEX IF EXISTS idx_po_line_items_invoice_date;
DROP INDEX IF EXISTS idx_po_line_items_supplier_promise_date;
DROP INDEX IF EXISTS idx_po_line_items_pl_timeline;

-- Expected space savings: ~112 kB

-- EXECUTION CRITERIA (all must be met):
-- ✓ 30+ days in production
-- ✓ pg_stat_user_indexes shows idx_scan = 0 for all indexes
-- ✓ No planned features requiring these indexes
-- ✓ This migration script reviewed and approved
-- ✓ Backup taken before execution

-- Rollback plan (if needed after execution):
-- Re-create indexes using original definitions from 0000_baseline_schema.sql
