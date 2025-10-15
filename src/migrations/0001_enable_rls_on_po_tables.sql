-- Enable Row-Level Security on PO tables
-- Migration: enable_rls_on_po_tables
-- Date: 2025-10-10
-- Reason: Security compliance - prevent unrestricted data access

-- 1. Enable RLS on pos table
ALTER TABLE pos ENABLE ROW LEVEL SECURITY;

-- 2. Enable RLS on po_line_items table
ALTER TABLE po_line_items ENABLE ROW LEVEL SECURITY;

-- 3. Enable RLS on po_mappings table
ALTER TABLE po_mappings ENABLE ROW LEVEL SECURITY;

-- 4. Create permissive policies (maintain current access patterns)
-- NOTE: These are temporary permissive policies. 
-- Replace with proper auth-based policies when authentication is implemented.

CREATE POLICY "Allow all operations on pos"
  ON pos
  FOR ALL
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow all operations on po_line_items"
  ON po_line_items
  FOR ALL
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow all operations on po_mappings"
  ON po_mappings
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 5. Add comment documenting future auth requirement
COMMENT ON POLICY "Allow all operations on pos" ON pos IS 
  'Temporary permissive policy. TODO: Replace with project-based access control when auth implemented.';

COMMENT ON POLICY "Allow all operations on po_line_items" ON po_line_items IS 
  'Temporary permissive policy. TODO: Replace with project-based access control when auth implemented.';

COMMENT ON POLICY "Allow all operations on po_mappings" ON po_mappings IS 
  'Temporary permissive policy. TODO: Replace with project-based access control when auth implemented.';
