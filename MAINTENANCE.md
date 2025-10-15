# Database Maintenance Tasks

This document tracks deferred maintenance tasks and monitoring procedures for the database.

---

## Unused Index Cleanup (Deferred)

**Status**: ⏸️ Pending production monitoring  
**Created**: 2025-10-10  
**Review Date**: 2025-11-10 (30 days from creation)  
**Migration**: `0002_remove_unused_indexes.sql`

### Overview

7 indexes with 0 scans detected in development environment. These indexes consume storage space (~112 kB) and add overhead to write operations without providing query performance benefits.

### Identified Unused Indexes

1. `idx_po_line_items_open_pos`
2. `idx_projects_sub_business_line`
3. `po_mappings_po_line_item_id_cost_breakdown_id_key`
4. `idx_forecast_versions_version_number`
5. `idx_po_line_items_invoice_date`
6. `idx_po_line_items_supplier_promise_date`
7. `idx_po_line_items_pl_timeline`

**Space Impact**: ~112 kB  
**Performance Impact**: Reduced write overhead after removal

### Monitoring Period

**Duration**: 30 days in production  
**Start Date**: [To be set when deployed to production]  
**End Date**: [30 days after production deployment]

### Monitoring Instructions

Run the following query weekly to track index usage:

```sql
-- Check index usage statistics
SELECT 
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND idx_scan = 0
  AND indexname IN (
    'idx_po_line_items_open_pos',
    'idx_projects_sub_business_line',
    'po_mappings_po_line_item_id_cost_breakdown_id_key',
    'idx_forecast_versions_version_number',
    'idx_po_line_items_invoice_date',
    'idx_po_line_items_supplier_promise_date',
    'idx_po_line_items_pl_timeline'
  )
ORDER BY tablename, indexname;
```

### Removal Criteria

Execute `0002_remove_unused_indexes.sql` ONLY if **ALL** conditions are met:

- [ ] 30+ days in production
- [ ] All 7 indexes show `idx_scan = 0` in production `pg_stat_user_indexes`
- [ ] No planned features identified that require these indexes
- [ ] Migration script reviewed and approved
- [ ] Database backup taken before execution

### Execution Procedure

When all criteria are met:

1. **Backup**: Take full database backup
   ```bash
   # Backup command (adjust for your environment)
   pg_dump $DATABASE_URL > backup_before_index_removal_$(date +%Y%m%d).sql
   ```

2. **Verify criteria**: Confirm all removal criteria met

3. **Execute migration**:
   ```bash
   cd packages/db
   pnpm db:push
   ```

4. **Verify removal**:
   ```sql
   -- Confirm indexes are dropped
   SELECT indexname 
   FROM pg_indexes 
   WHERE schemaname = 'public' 
   AND indexname IN (
     'idx_po_line_items_open_pos',
     'idx_projects_sub_business_line',
     'po_mappings_po_line_item_id_cost_breakdown_id_key',
     'idx_forecast_versions_version_number',
     'idx_po_line_items_invoice_date',
     'idx_po_line_items_supplier_promise_date',
     'idx_po_line_items_pl_timeline'
   );
   -- Expected: Empty result (0 rows)
   ```

5. **Monitor performance**: Watch for any query performance degradation over next 7 days

### Rollback Plan

If query performance degrades after removal:

1. Review `0000_baseline_schema.sql` for original index definitions
2. Re-create specific indexes as needed
3. Document which indexes were needed and why (update this file)

### Notes

- This is a **deferred** maintenance task - DO NOT execute the migration immediately
- Development environment data may not reflect production query patterns
- Always verify in production before removing indexes
- When in doubt, keep the index

---

## Future Maintenance Tasks

(Add new maintenance tasks here as they are identified)
