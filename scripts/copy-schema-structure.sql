-- Copy table structures and data from public schema to dev_v2
-- This creates a complete replica including structure, data, and relationships

-- Step 1: Copy table structures and data
-- Note: LIKE ... INCLUDING ALL copies defaults, constraints, indexes
--       but NOT foreign keys (they're added separately below)

-- Copy projects table (no dependencies)
CREATE TABLE dev_v2.projects (LIKE public.projects INCLUDING ALL);
INSERT INTO dev_v2.projects SELECT * FROM public.projects;

-- Copy cost_breakdown table
CREATE TABLE dev_v2.cost_breakdown (LIKE public.cost_breakdown INCLUDING ALL);
INSERT INTO dev_v2.cost_breakdown SELECT * FROM public.cost_breakdown;

-- Copy pos table (no dependencies)
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

-- Step 2: Add foreign key constraints
-- These create the relationships between tables

-- cost_breakdown -> projects
ALTER TABLE dev_v2.cost_breakdown
ADD CONSTRAINT cost_breakdown_project_id_fkey
FOREIGN KEY (project_id) REFERENCES dev_v2.projects(id);

-- forecast_versions -> projects
ALTER TABLE dev_v2.forecast_versions
ADD CONSTRAINT forecast_versions_project_id_fkey
FOREIGN KEY (project_id) REFERENCES dev_v2.projects(id);

-- po_line_items -> pos
ALTER TABLE dev_v2.po_line_items
ADD CONSTRAINT po_line_items_po_id_fkey
FOREIGN KEY (po_id) REFERENCES dev_v2.pos(id);

-- po_mappings -> cost_breakdown
ALTER TABLE dev_v2.po_mappings
ADD CONSTRAINT po_mappings_cost_breakdown_id_fkey
FOREIGN KEY (cost_breakdown_id) REFERENCES dev_v2.cost_breakdown(id);

-- po_mappings -> po_line_items
ALTER TABLE dev_v2.po_mappings
ADD CONSTRAINT po_mappings_po_line_item_id_fkey
FOREIGN KEY (po_line_item_id) REFERENCES dev_v2.po_line_items(id);

-- budget_forecasts -> forecast_versions
ALTER TABLE dev_v2.budget_forecasts
ADD CONSTRAINT budget_forecasts_forecast_version_id_fkey
FOREIGN KEY (forecast_version_id) REFERENCES dev_v2.forecast_versions(id);

-- budget_forecasts -> cost_breakdown
ALTER TABLE dev_v2.budget_forecasts
ADD CONSTRAINT budget_forecasts_cost_breakdown_id_fkey
FOREIGN KEY (cost_breakdown_id) REFERENCES dev_v2.cost_breakdown(id);

-- Verify copy (tables and sizes)
SELECT 
    schemaname, 
    tablename, 
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname IN ('public', 'dev_v2') 
ORDER BY schemaname, tablename;
