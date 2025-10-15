# Database Schema Relationships

## Entity Relationship Diagram

```
┌─────────────────┐
│    projects     │
│─────────────────│
│ • id (PK)       │
│   name          │
│   sub_business  │
└─────────────────┘
        ▲
        │
        ├──────────────┬─────────────────┐
        │              │                 │
        │              │                 │
┌───────┴──────────┐   │   ┌────────────┴──────────┐
│ cost_breakdown   │   │   │ forecast_versions     │
│──────────────────│   │   │───────────────────────│
│ • id (PK)        │   │   │ • id (PK)             │
│   project_id (FK)│───┘   │   project_id (FK)     │
│   cost_line      │        │   version_number      │
│   budget_cost    │        │   reason_for_change   │
└──────────────────┘        └───────────────────────┘
        ▲                            ▲
        │                            │
        │                            │
        ├────────────────┐           │
        │                │           │
┌───────┴──────────┐     │   ┌───────┴───────────────┐
│  po_mappings     │     │   │  budget_forecasts     │
│──────────────────│     │   │───────────────────────│
│ • id (PK)        │     │   │ • id (PK)             │
│   po_line_id (FK)│     │   │   forecast_ver_id (FK)│───┐
│   cost_brkdn (FK)│─────┘   │   cost_brkdn_id (FK)  │───┤
│   mapped_amount  │         │   forecasted_cost     │
└──────────────────┘         └───────────────────────┘
        ▲
        │
┌───────┴──────────┐
│  po_line_items   │
│──────────────────│
│ • id (PK)        │
│   po_id (FK)     │───┐
│   part_number    │   │
│   line_value     │   │
└──────────────────┘   │
                       │
                ┌──────┴────────┐
                │      pos       │
                │────────────────│
                │ • id (PK)      │
                │   po_number    │
                │   vendor_name  │
                │   total_value  │
                └────────────────┘
```

## Foreign Key Relationships

### Core Hierarchy

1. **projects** (root entity)
   - Referenced by: `cost_breakdown`, `forecast_versions`

2. **cost_breakdown** (project budget lines)
   - References: `projects`
   - Referenced by: `po_mappings`, `budget_forecasts`

3. **forecast_versions** (budget forecasts)
   - References: `projects`
   - Referenced by: `budget_forecasts`

### Purchase Order Chain

4. **pos** (purchase orders)
   - Referenced by: `po_line_items`

5. **po_line_items** (PO items)
   - References: `pos`
   - Referenced by: `po_mappings`

### Mapping & Forecasting

6. **po_mappings** (links POs to budget)
   - References: `po_line_items`, `cost_breakdown`

7. **budget_forecasts** (forecast data)
   - References: `forecast_versions`, `cost_breakdown`

## Foreign Key Constraints in dev_v2 Schema

| Table | Column | References | Constraint Name |
|-------|--------|------------|-----------------|
| cost_breakdown | project_id | projects(id) | cost_breakdown_project_id_fkey |
| forecast_versions | project_id | projects(id) | forecast_versions_project_id_fkey |
| po_line_items | po_id | pos(id) | po_line_items_po_id_fkey |
| po_mappings | cost_breakdown_id | cost_breakdown(id) | po_mappings_cost_breakdown_id_fkey |
| po_mappings | po_line_item_id | po_line_items(id) | po_mappings_po_line_item_id_fkey |
| budget_forecasts | forecast_version_id | forecast_versions(id) | budget_forecasts_forecast_version_id_fkey |
| budget_forecasts | cost_breakdown_id | cost_breakdown(id) | budget_forecasts_cost_breakdown_id_fkey |

**Total**: 7 foreign key constraints

## Verification

To view relationships in your PostgreSQL client:

```sql
-- List all foreign keys in dev_v2
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS references_table,
    ccu.column_name AS references_column
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'dev_v2'
ORDER BY tc.table_name;
```

## Why Foreign Keys Matter

1. **Data Integrity**: Prevents orphaned records
2. **Referential Integrity**: Ensures related data stays consistent
3. **Visual Tools**: Database visualizers show relationships
4. **Query Optimization**: Database can optimize joins better
5. **Documentation**: Self-documenting schema structure

## VS Code PostgreSQL Extension

After adding foreign keys, the VS Code PostgreSQL extension should now display:
- ✅ Relationship lines between tables
- ✅ Foreign key indicators on columns
- ✅ ER diagram generation
- ✅ Navigation from foreign keys to referenced tables

Refresh your connection in VS Code to see the relationships!
