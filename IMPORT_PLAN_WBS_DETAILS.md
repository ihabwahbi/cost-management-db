# Import Plan: wbs_details

> **Status:** Planning  
> **Author:** AI Agent  
> **Date:** 2025-12-02  
> **Predecessor:** grir_exposures import (completed)

---

## Overview

This document captures the implementation plan for importing `wbs_details` data into the database. WBS (Work Breakdown Structure) provides project/operation context for PO line items and reservations.

### Why This Table Next?

| Factor | Reasoning |
|--------|-----------|
| **Parent Table** | `sap_reservations` has FK to `wbs_details.wbs_number` - must import first |
| **New Pattern** | Uses VARCHAR PK (not UUID) - validates different approach |
| **Array Column** | `sub_business_lines` is PostgreSQL `text[]` - new data type handling |
| **Medium Volume** | 7,852 records - good for validation |
| **Clean Data** | 0 orphans (this is a root table with no FKs) |

---

## 1. Current State Analysis

### 1.1 Schema Definition

```typescript
// src/schema/wbs-details.ts
wbsDetails = devV3Schema.table('wbs_details', {
  // VARCHAR primary key (NOT UUID!)
  wbsNumber: varchar('wbs_number').primaryKey(),
  
  // Source tracking
  wbsSource: varchar('wbs_source').notNull(),  // 'Project', 'Operation', 'Operation Activity'
  
  // Source identifiers (nullable)
  projectNumber: varchar('project_number'),
  operationNumber: varchar('operation_number'),
  opsActivityNumber: varchar('ops_activity_number'),
  
  // Descriptive fields
  wbsName: text('wbs_name'),
  clientName: text('client_name'),
  
  // Equipment and location
  rig: varchar('rig'),
  opsDistrict: varchar('ops_district'),
  location: varchar('location'),
  
  // PostgreSQL text[] array
  subBusinessLines: text('sub_business_lines').array(),
  
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
}, (table) => [
  index('wbs_details_wbs_source_idx').on(table.wbsSource),
  index('wbs_details_project_number_idx').on(table.projectNumber),
  index('wbs_details_location_idx').on(table.location),
  // GIN index for array containment queries
  index('wbs_details_sub_business_lines_idx').using('gin', table.subBusinessLines),
]);
```

### 1.2 CSV Structure

File: `data/import-ready/wbs_details.csv`

```csv
wbs_number,wbs_source,project_number,operation_number,ops_activity_number,wbs_name,client_name,rig,ops_district,location,sub_business_lines
J.22.111697,Project,P.1033291,,,Q3 U420 Rigless,SANTOS LIMITED,RIGLESS - AUSTRALIA,Moomba WL,Moomba,{SLKN}
J.21.111685,Project,P.1024839,,,Sav 408 Drilling,SANTOS LIMITED,"SAVANNA DRILLING #408, ...",Roma WL,Roma,{WLES}
```

**Row count:** 7,852 records
**Unique wbs_numbers:** 7,852 (100% unique - natural PK)

### 1.3 Data Profile Summary

| Column | Type | Nulls | Unique | Notes |
|--------|------|-------|--------|-------|
| `wbs_number` | string | 0% | 7,852 | **PK** - format: `J.XX.XXXXXX` |
| `wbs_source` | string | 0% | 3 | Project, Operation, Operation Activity |
| `project_number` | string | 0% | 555 | Always populated |
| `operation_number` | string | 6.7% | 1,239 | Null for Project source |
| `ops_activity_number` | string | 8.5% | 7,182 | Null for Project/Operation source |
| `wbs_name` | string | 0% | 5,552 | Description |
| `client_name` | string | 0% | 132 | Customer name |
| `rig` | string | 2.95% | 184 | Equipment name |
| `ops_district` | string | 0% | 11 | District code |
| `location` | string | 0% | 5 | Mapped location |
| `sub_business_lines` | string | 0% | 23 | **PostgreSQL array format** |

### 1.4 Source Distribution

| Source | Count | % |
|--------|-------|---|
| Operation Activity | 7,182 | 91.5% |
| Project | 526 | 6.7% |
| Operation | 144 | 1.8% |

### 1.5 Key Observations

1. **VARCHAR Primary Key** - Unlike other tables, uses `wbs_number` string as PK (not UUID)
2. **PostgreSQL Array Column** - `sub_business_lines` uses `{val1,val2}` format
3. **No Foreign Keys** - This is a root/parent table
4. **Hierarchical Nulls** - operation_number/ops_activity_number null based on source type
5. **Standard WBS Format** - `J.XX.XXXXXX` (e.g., `J.22.111697`)

---

## 2. Learnings from Previous Imports

### 2.1 Consolidated Learnings

| Issue | Root Cause | Solution |
|-------|------------|----------|
| Numeric strings with `.0` suffix | Pandas reads nullable int as float | `clean_numeric_string()` or `.astype(str)` |
| Slow row-by-row inserts | Individual INSERT statements | Bulk upsert with `sql\`excluded.column\`` |
| Environment variables not loading | Missing dotenv import | `import 'dotenv/config'` at top |
| Pre-commit hook failures | Schema lock, Oracle regen | Stage generated files |
| FK lookup at scale | N+1 queries | Build Map<key, value> once at start |
| Orphan records | Missing parent data | Skip + log (don't fail import) |
| Composite key upserts | Need array target | `target: [col1, col2]` |

### 2.2 Patterns That Work Well

```typescript
// Bulk Upsert Pattern (proven pattern)
await db.insert(table).values(batch).onConflictDoUpdate({
  target: table.uniqueKey,
  set: {
    column: sql`excluded.column`,
    updatedAt: new Date(),
  },
});

// Batch Processing Pattern
const BATCH_SIZE = 1000;
for (let i = 0; i < records.length; i += BATCH_SIZE) {
  const batch = records.slice(i, i + BATCH_SIZE);
  await processBatch(batch);
}
```

### 2.3 Performance Benchmarks

| Import | Records | Time | Rate |
|--------|---------|------|------|
| po_line_items | 57K | ~14s | ~4,000/s |
| po_transactions | 106K | ~12s | ~9,000/s |
| grir_exposures | 65 | <1s | instant |

**Expectation for wbs_details:** 7,852 records should take ~1-2 seconds.

---

## 3. New Challenges for This Import

### 3.1 VARCHAR Primary Key (Not UUID)

Previous imports used UUID primary keys with `defaultRandom()`. This table uses VARCHAR PK.

**Impact on Import:**
- No need to track `id` column - `wbs_number` IS the primary key
- Upsert target is `wbsNumber` directly
- Simpler record structure (no UUID generation)

```typescript
// Upsert on VARCHAR PK
await db.insert(wbsDetails).values(records).onConflictDoUpdate({
  target: wbsDetails.wbsNumber,  // VARCHAR PK, not id
  set: { ... },
});
```

### 3.2 PostgreSQL Array Column

The `sub_business_lines` column is `text[]` - a PostgreSQL array.

**CSV Format:** `{WLPS,SLKN,WLES}` (PostgreSQL array literal)

**Drizzle Handling:**
```typescript
// Option A: Parse as JavaScript array
subBusinessLines: parseArrayLiteral(row.sub_business_lines),
// Where: '{WLPS,SLKN}' -> ['WLPS', 'SLKN']

// Option B: Insert as raw SQL
subBusinessLines: sql`${row.sub_business_lines}::text[]`,
```

**Recommended Approach:** Option A - Parse to JS array for type safety.

```typescript
function parseArrayLiteral(pgArray: string): string[] | null {
  if (!pgArray || pgArray === '{}') return [];
  // Remove { } and split by comma
  return pgArray.slice(1, -1).split(',').filter(Boolean);
}
```

### 3.3 No Foreign Keys = Simpler Import

Unlike po_transactions and grir_exposures:
- No FK lookup step needed
- No orphan handling required
- Direct CSV → DB mapping

---

## 4. Design Decisions

### 4.1 Unique Key Strategy

**Decision:** Use `wbs_number` VARCHAR column as the upsert target.

**Rationale:**
- `wbs_number` is already the primary key in the schema
- 100% unique in source data (verified)
- No need for composite key or synthetic ID

### 4.2 Array Column Strategy

**Decision:** Parse PostgreSQL array literal to JavaScript array before insert.

```typescript
// CSV: '{WLPS,SLKN}'
// JS:  ['WLPS', 'SLKN']
// DB:  text[] array
```

**Rationale:**
- Drizzle ORM handles JS arrays correctly for PostgreSQL array columns
- Type-safe parsing catches malformed data
- Easier to validate and log

### 4.3 Soft Delete Strategy

**Decision:** No soft delete for WBS records.

**Rationale:**
- WBS is reference data (relatively static)
- Deleting WBS would break FK integrity with reservations
- If WBS disappears from source, investigate (don't auto-delete)
- Use circuit breaker instead

---

## 5. Implementation Checklist

### 5.1 Pre-Implementation

- [ ] Profile CSV: `python3 scripts/profile_data.py data/import-ready/wbs_details.csv`
- [ ] Verify wbs_number uniqueness (100% unique expected)
- [ ] Verify array format in sub_business_lines column
- [ ] Check that schema already exists with correct structure

### 5.2 Schema Updates

**Status:** Schema already exists with correct structure.

File: `src/schema/wbs-details.ts`

- [ ] Verify VARCHAR PK is correct (not UUID)
- [ ] Verify text[] array type for sub_business_lines
- [ ] Verify indexes exist (already defined)
- [ ] Run `npm run type-check`
- [ ] No db:push needed (schema unchanged)

### 5.3 Pipeline Updates

**Status:** No changes needed.

File: `scripts/stage3_prepare/09_prepare_wbs_details.py`

The current script already:
- Maps all columns correctly
- Converts JSON arrays to PostgreSQL literal format `{val1,val2}`
- Validates required columns
- Handles duplicates (keeps first)

**Verify only:**
- [ ] Run pipeline to confirm output is current
- [ ] Confirm array format: `{WLPS,SLKN}` (not JSON `["WLPS","SLKN"]`)

### 5.4 Import Script

File: `src/imports/wbs-details.ts`

- [ ] Create new import script (simpler than po-transactions)
- [ ] Parse sub_business_lines array literal → JS array
- [ ] Upsert on `wbsNumber` VARCHAR PK
- [ ] Batch processing (1000 records per batch)
- [ ] Circuit breaker (check import size vs existing)
- [ ] Stats logging (source distribution, location breakdown)

### 5.5 Testing

- [ ] Run with `--dry-run` first
- [ ] Verify VARCHAR PK upsert works
- [ ] Verify array column inserts correctly
- [ ] Query with array containment: `WHERE 'WLPS' = ANY(sub_business_lines)`
- [ ] Test idempotency (run twice, same result)

### 5.6 Post-Implementation

- [ ] Add npm scripts to package.json
- [ ] Run tests: `npm test && pytest tests/test_pipeline_golden_set.py`
- [ ] Commit changes

---

## 6. Code Templates

### 6.1 Import Script Structure

```typescript
#!/usr/bin/env npx tsx
import 'dotenv/config';
import { createReadStream } from 'fs';
import { parse } from 'csv-parse';
import { db } from '../client';
import { wbsDetails } from '../schema';
import { sql } from 'drizzle-orm';

const CSV_PATH = './data/import-ready/wbs_details.csv';
const BATCH_SIZE = 1000;

interface CsvRow {
  wbs_number: string;
  wbs_source: string;
  project_number: string;
  operation_number: string;
  ops_activity_number: string;
  wbs_name: string;
  client_name: string;
  rig: string;
  ops_district: string;
  location: string;
  sub_business_lines: string;  // '{WLPS,SLKN}' format
}

type WbsDetailsInsert = typeof wbsDetails.$inferInsert;
```

### 6.2 Array Parsing Function

```typescript
/**
 * Parse PostgreSQL array literal to JavaScript array.
 * 
 * @example
 * parseArrayLiteral('{WLPS,SLKN}') => ['WLPS', 'SLKN']
 * parseArrayLiteral('{}') => []
 * parseArrayLiteral('') => null
 */
function parseArrayLiteral(pgArray: string): string[] | null {
  if (!pgArray || pgArray.trim() === '') return null;
  if (pgArray === '{}') return [];
  
  // Remove { } and split by comma
  const inner = pgArray.slice(1, -1);
  return inner.split(',').map(s => s.trim()).filter(Boolean);
}
```

### 6.3 Transform Function

```typescript
function transformRow(row: CsvRow): WbsDetailsInsert {
  const str = (val: string): string | null => val === '' ? null : val;
  
  return {
    wbsNumber: row.wbs_number,
    wbsSource: row.wbs_source,
    projectNumber: str(row.project_number),
    operationNumber: str(row.operation_number),
    opsActivityNumber: str(row.ops_activity_number),
    wbsName: str(row.wbs_name),
    clientName: str(row.client_name),
    rig: str(row.rig),
    opsDistrict: str(row.ops_district),
    location: str(row.location),
    subBusinessLines: parseArrayLiteral(row.sub_business_lines),
    updatedAt: new Date(),
  };
}
```

### 6.4 Upsert Pattern for VARCHAR PK

```typescript
async function upsertBatch(records: WbsDetailsInsert[]): Promise<number> {
  if (records.length === 0) return 0;
  
  await db
    .insert(wbsDetails)
    .values(records)
    .onConflictDoUpdate({
      target: wbsDetails.wbsNumber,  // VARCHAR PK
      set: {
        wbsSource: sql`excluded.wbs_source`,
        projectNumber: sql`excluded.project_number`,
        operationNumber: sql`excluded.operation_number`,
        opsActivityNumber: sql`excluded.ops_activity_number`,
        wbsName: sql`excluded.wbs_name`,
        clientName: sql`excluded.client_name`,
        rig: sql`excluded.rig`,
        opsDistrict: sql`excluded.ops_district`,
        location: sql`excluded.location`,
        subBusinessLines: sql`excluded.sub_business_lines`,
        updatedAt: new Date(),
      },
    });
  
  return records.length;
}
```

---

## 7. Validation Queries

After import, run these to verify data integrity:

```sql
-- Count records
SELECT COUNT(*) FROM dev_v3.wbs_details;
-- Expected: 7,852

-- Check for duplicates (should be 0)
SELECT wbs_number, COUNT(*) 
FROM dev_v3.wbs_details 
GROUP BY wbs_number 
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Source distribution
SELECT wbs_source, COUNT(*) 
FROM dev_v3.wbs_details 
GROUP BY wbs_source 
ORDER BY COUNT(*) DESC;
-- Expected: Operation Activity ~7182, Project ~526, Operation ~144

-- Location distribution  
SELECT location, COUNT(*) 
FROM dev_v3.wbs_details 
GROUP BY location 
ORDER BY COUNT(*) DESC;

-- Test array containment query
SELECT COUNT(*) FROM dev_v3.wbs_details 
WHERE 'WLPS' = ANY(sub_business_lines);

-- Test GIN index (should use index scan)
EXPLAIN SELECT * FROM dev_v3.wbs_details 
WHERE sub_business_lines @> ARRAY['WLPS'];
```

---

## 8. Potential Pitfalls

| Pitfall | Symptom | Mitigation |
|---------|---------|------------|
| **Array parsing fails** | Import error on sub_business_lines | Validate format before parsing |
| **Non-standard WBS format** | Validation warning | Log but don't fail (warn only) |
| **Empty array vs null** | Inconsistent queries | `{}` → empty array, blank → null |
| **VARCHAR PK conflict** | "duplicate key" error | Upsert handles this automatically |
| **Unicode in names** | Encoding errors | CSV is UTF-8, should be fine |

---

## 9. Success Criteria

- [ ] All 7,852 WBS records imported
- [ ] Source distribution matches: Operation Activity (91.5%), Project (6.7%), Operation (1.8%)
- [ ] Array containment queries work: `WHERE 'WLPS' = ANY(sub_business_lines)`
- [ ] Import completes in < 5 seconds
- [ ] Idempotent (run twice, same result)
- [ ] GIN index used for array queries (verify with EXPLAIN)

---

## 10. Execution Order

1. **Verify pre-conditions** - Confirm CSV is current
2. **Run data profile** - Confirm structure matches expectations
3. **Verify schema** - No changes needed
4. **Create import script** - Based on templates above
5. **Dry run** - Test without changes
6. **Import** - Run actual import
7. **Verify** - Run validation queries
8. **Test array queries** - Confirm GIN index works
9. **Test idempotency** - Run import again
10. **Commit** - Save all changes

---

## Appendix A: File Locations

| Component | Path |
|-----------|------|
| Schema | `src/schema/wbs-details.ts` |
| Import script (to create) | `src/imports/wbs-details.ts` |
| Pipeline prepare script | `scripts/stage3_prepare/09_prepare_wbs_details.py` |
| Column mappings | `scripts/config/column_mappings.py` |
| Import-ready CSV | `data/import-ready/wbs_details.csv` |

---

## Appendix B: Business Context

### What is WBS?

WBS (Work Breakdown Structure) is a hierarchical decomposition of project work:

```
Project (P.1020480)
  └── Operation (O.1020480.01)
        └── Operation Activity (A.1020480.01.05)
              └── WBS (J.22.111697)
```

### WBS Sources

| Source | Description | Count |
|--------|-------------|-------|
| **Project** | High-level project WBS from ProjectDashboard | 526 |
| **Operation** | Operation-level WBS from OperationDashboard | 144 |
| **Operation Activity** | Detailed activity WBS from OperationActivityDashboard | 7,182 |

### Sub Business Lines

WBS records are tagged with one or more Sub Business Lines:

| Code | Meaning |
|------|---------|
| WLPS | Wireline Production Services |
| SLKN | Slickline |
| WLES | Wireline Evaluation Services |
| FPPS | Formation Pressure Testing |

Operations can have multiple SBL codes (e.g., `{WLPS,SLKN,WLES}`).

---

## Appendix C: Next Steps After wbs_details

After successfully importing `wbs_details`, the next table should be `sap_reservations`:

### sap_reservations Complexity

| Aspect | Details |
|--------|---------|
| **Volume** | 1,483 records |
| **FK to wbs_details** | Nullable, ~80% null, 1 orphan |
| **FK to po_line_items** | Nullable VARCHAR FK (not UUID!), ~65% null, 9 orphans |
| **Unique constraint** | `reservation_line_id` (already unique in schema) |

### Key Differences from Previous Imports

1. **Nullable FKs** - Unlike grir_exposures where FK was required
2. **VARCHAR FK to VARCHAR** - `po_line_item_id` references `poLineItems.poLineId` (not UUID!)
3. **Orphan handling with nulls** - Can set FK to null if orphan (not skip entire record)
4. **Dual FK resolution** - Need to check both wbs_details and po_line_items

### Recommended Orphan Strategy for sap_reservations

```typescript
// For orphan WBS - set to null (80% are already null)
if (row.wbs_number && !wbsExists(row.wbs_number)) {
  record.wbsNumber = null;
  logOrphanWbs(row.wbs_number);
}

// For orphan PO Line ID - set to null (65% are already null)
if (row.po_line_item_id && !poLineExists(row.po_line_item_id)) {
  record.poLineItemId = null;
  logOrphanPoLineId(row.po_line_item_id);
}
```

---

## Appendix D: Comparison Table

| Aspect | po_transactions | grir_exposures | wbs_details |
|--------|-----------------|----------------|-------------|
| Volume | 106K | 65 | 7,852 |
| PK Type | UUID | UUID | **VARCHAR** |
| Unique Key | transaction_id | (po_line_item_id, snapshot_date) | wbs_number |
| FK Lookup | UUID lookup | UUID lookup | **None** |
| Array Columns | No | No | **Yes** |
| Import Time | ~12s | <1s | Expected <2s |
