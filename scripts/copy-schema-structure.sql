-- Copy table structures from public schema to dev_v2
-- This script creates the same table structure in dev_v2 without copying data

-- Note: This is a template. The actual structure will be created by Drizzle migrations.
-- To copy structure and data from existing public schema:

-- Copy projects table
CREATE TABLE dev_v2.projects (LIKE public.projects INCLUDING ALL);
INSERT INTO dev_v2.projects SELECT * FROM public.projects;

-- Copy cost_breakdown table
CREATE TABLE dev_v2.cost_breakdown (LIKE public.cost_breakdown INCLUDING ALL);
INSERT INTO dev_v2.cost_breakdown SELECT * FROM public.cost_breakdown;

-- Copy pos table
CREATE TABLE dev_v2.pos (LIKE public.pos INCLUDING ALL);
INSERT INTO dev_v2.pos SELECT * FROM public.pos;

-- Copy po_line_items table
CREATE TABLE dev_v2.po_line_items (LIKE public.po_line_items INCLUDING ALL);
INSERT INTO dev_v2.po_line_items SELECT * FROM public.po_line_items;

-- Copy po_mappings table
CREATE TABLE dev_v2.po_mappings (LIKE public.po_mappings INCLUDING ALL);
INSERT INTO dev_v2.po_mappings SELECT * FROM public.po_mappings;

-- Copy forecast_versions table
CREATE TABLE dev_v2.forecast_versions (LIKE public.forecast_versions INCLUDING ALL);
INSERT INTO dev_v2.forecast_versions SELECT * FROM public.forecast_versions;

-- Copy budget_forecasts table
CREATE TABLE dev_v2.budget_forecasts (LIKE public.budget_forecasts INCLUDING ALL);
INSERT INTO dev_v2.budget_forecasts SELECT * FROM public.budget_forecasts;

-- Verify copy
SELECT 
    schemaname, 
    tablename, 
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname IN ('public', 'dev_v2') 
ORDER BY schemaname, tablename;
