-- Add foreign key constraints to dev_v2 schema
-- These match the constraints in the public schema

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

-- Verify foreign keys were created
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'dev_v2'
ORDER BY tc.table_name;
