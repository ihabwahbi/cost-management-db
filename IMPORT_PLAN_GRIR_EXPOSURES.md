# Import Plan: grir_exposures

> **Status:** Planning  
> **Author:** AI Agent  
> **Date:** 2025-12-02  
> **Predecessor:** po_transactions import (completed)

---

## Overview

This document captures the implementation plan for importing `grir_exposures` data into the database. GRIR (Goods Receipt/Invoice Receipt) exposures track financial risk when invoices exceed goods received.

### Why This Table Next?

| Factor | Reasoning |
|--------|-----------|
| **Dependency** | Direct child of `po_line_items` - same FK pattern as po_transactions |
| **Volume** | Only 65 records - excellent for quick validation |
| **Pattern Validation** | Confirms FK lookup pattern works correctly |
| **Business value** | Core financial exposure tracking |

---

## 1. Current State Analysis

### 1.1 Schema Definition

```typescript
// src/schema/grir-exposures.ts
grirExposures = devV3Schema.table('grir_exposures', {
  id: uuid('id').primaryKey().defaultRandom(),
  poLineItemId: uuid('po_line_item_id')
    .notNull()
    .references(() => poLineItems.id),
  grirQty: numeric('grir_qty').notNull().default('0'),
  grirValue: numeric('grir_value').notNull().default('0'),
  firstExposureDate: date('first_exposure_date'),  // nullable
  daysOpen: integer('days_open').default(0),
  timeBucket: varchar('time_bucket', { length: 20 }),
  snapshotDate: date('snapshot_date').notNull(),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});
```

### 1.2 CSV Structure

File: `data/import-ready/grir_exposures.csv`

```csv
po_line_id,grir_qty,grir_value,first_exposure_date,days_open,time_bucket,snapshot_date
4584538403-4,2.0,688.98,2025-11-28,4,<1 month,2025-12-02
4791943218-1,12.0,243.12,2023-07-28,858,>1 year,2025-12-02
```

**Row count:** 65 records
**Unique po_line_ids:** 65 (each PO has at most one exposure)

### 1.3 Data Profile Summary

| Column | Type | Nulls | Unique | Notes |
|--------|------|-------|--------|-------|
| `po_line_id` | string | 0% | 65 | **Unique** - can be upsert key |
| `grir_qty` | float | 0% | 13 | Quantity variance |
| `grir_value` | float | 0% | 53 | Dollar exposure |
| `first_exposure_date` | date | 0% | 31 | When IR first exceeded GR |
| `days_open` | int | 0% | 31 | Duration of exposure |
| `time_bucket` | string | 0% | 5 | Aging category |
| `snapshot_date` | date | 0% | 1 | Constant: 2025-12-02 |

### 1.4 Time Bucket Distribution

| Bucket | Count | % |
|--------|-------|---|
| 6-12 months | 39 | 60% |
| 1-3 months | 12 | 18% |
| >1 year | 7 | 11% |
| 3-6 months | 4 | 6% |
| <1 month | 3 | 5% |

### 1.5 Key Observations

1. **po_line_id is unique** - unlike transactions, each PO has only one GRIR exposure record
2. **Point-in-time snapshots** - snapshot_date captures when calculation was done
3. **No orphans** - all 65 po_line_ids exist in po_line_items
4. **Small volume** - easy to validate and debug

---

## 2. Learnings from Previous Imports

### 2.1 From po_line_items Import

| Issue | Solution |
|-------|----------|
| Numeric strings with `.0` suffix | `clean_numeric_string()` function |
| Slow row-by-row inserts | Bulk upsert with `sql\`excluded.column\`` pattern |
| Environment variables not loading | `import 'dotenv/config'` at top |
| Pre-commit hook failures | Run schema_lock.py --update and stage files |

### 2.2 From po_transactions Import

| Issue | Solution |
|-------|----------|
| FK lookup at scale | Build Map<po_line_id, uuid> once at start |
| Orphan transactions | Skip + log (don't fail entire import) |
| `NOT IN` with 100K+ params | Don't use - exceeds PostgreSQL limit |
| Circuit breaker with mass data | Compare import size ratio, not exact diff |
| Date parsing errors | Use `format="mixed"` for pandas datetime |

### 2.3 Patterns That Work Well

```typescript
// FK Lookup Pattern (proven at 55K+ records)
async function buildPoLineIdLookup(): Promise<Map<string, string>> {
  const rows = await db
    .select({ poLineId: poLineItems.poLineId, id: poLineItems.id })
    .from(poLineItems)
    .where(eq(poLineItems.isActive, true));
  return new Map(rows.map(r => [r.poLineId, r.id]));
}

// Bulk Upsert Pattern
await db.insert(table).values(batch).onConflictDoUpdate({
  target: table.uniqueKey,
  set: { column: sql`excluded.column`, updatedAt: new Date() },
});
```

---

## 3. Design Decisions

### 3.1 Unique Key Strategy

**Problem:** Need a unique key for upserts. Schema has no natural unique constraint.

**Options Considered:**

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Composite: `(po_line_item_id, snapshot_date)` | Natural key, allows history | Schema change needed |
| B | Use `po_line_id` only | Simple, current data shows uniqueness | May break if history added |
| C | Generate synthetic ID | Same pattern as transactions | Over-engineering for small table |

**Decision:** Option A - Composite unique constraint on `(po_line_item_id, snapshot_date)`

**Rationale:**
- Semantically correct: A PO can only have one exposure record per snapshot
- Supports future history: If we add daily snapshots, they'll be separate records
- Matches business reality: GRIR is calculated at a point in time

### 3.2 Foreign Key Resolution

Same pattern as po_transactions - build lookup map once:

```typescript
const lookup = await buildPoLineIdLookup();
const parentId = lookup.get(row.po_line_id);
if (!parentId) { /* skip orphan */ }
```

### 3.3 Orphan Handling

**Decision:** Skip and log (same as transactions)

Current analysis shows 0 orphans, but defensive coding is important:
- Log orphan po_line_ids
- Continue with valid records
- Report count at end

### 3.4 Snapshot Date Semantics

The current CSV has a single snapshot_date (2025-12-02). Future considerations:

- **Historical tracking:** Keep old snapshots to see exposure trends
- **Replacement:** Each import replaces records for that snapshot_date
- **Recommendation:** Support both by:
  1. Upsert on `(po_line_item_id, snapshot_date)`
  2. Don't delete records from other snapshot dates

---

## 4. Implementation Checklist

### 4.1 Pre-Implementation

- [ ] Profile CSV: `python3 scripts/profile_data.py data/import-ready/grir_exposures.csv`
- [ ] Verify no orphan po_line_ids
- [ ] Confirm po_line_id uniqueness in current data

### 4.2 Schema Updates

File: `src/schema/grir-exposures.ts`

- [ ] Add unique index on `(po_line_item_id, snapshot_date)`
- [ ] Run `npm run type-check`
- [ ] Run `npm run db:push`

```typescript
// Add to table definition:
}, (table) => [
  uniqueIndex('grir_exposures_po_snapshot_idx')
    .on(table.poLineItemId, table.snapshotDate),
  // ... existing indexes
]);
```

### 4.3 Pipeline Updates

**Note:** No changes needed to `scripts/stage3_prepare/08_prepare_grir_exposures.py`

The current script already:
- Maps all required columns
- Rounds numeric values
- Validates with Pandera contract

**Verify only:**
- [ ] Run pipeline: `python3 scripts/stage3_prepare/08_prepare_grir_exposures.py`
- [ ] Confirm output matches expected structure

### 4.4 Import Script

File: `src/imports/grir-exposures.ts`

- [ ] Copy structure from `po-transactions.ts`
- [ ] Simplify (no transaction_id generation needed)
- [ ] FK lookup for `po_line_id` → UUID
- [ ] Upsert on `(po_line_item_id, snapshot_date)`
- [ ] Orphan handling (skip + log)
- [ ] Circuit breaker (check import size)
- [ ] Stats logging (total exposure value, time bucket breakdown)

### 4.5 Testing

- [ ] Run with `--dry-run` first
- [ ] Verify FK relationships
- [ ] Check time bucket values are valid
- [ ] Test idempotency (run twice)
- [ ] Verify exposure values sum correctly

### 4.6 Post-Implementation

- [ ] Add npm scripts to package.json
- [ ] Run tests: `pytest tests/test_pipeline_golden_set.py`
- [ ] Commit changes

---

## 5. Code Templates

### 5.1 Schema Update

```typescript
// src/schema/grir-exposures.ts
import { uniqueIndex } from 'drizzle-orm/pg-core';

// Add to table indexes:
}, (table) => [
  uniqueIndex('grir_exposures_po_snapshot_idx')
    .on(table.poLineItemId, table.snapshotDate),
  index('grir_exposures_po_line_item_id_idx').on(table.poLineItemId),
  index('grir_exposures_time_bucket_idx').on(table.timeBucket),
  index('grir_exposures_snapshot_date_idx').on(table.snapshotDate),
  index('grir_exposures_days_open_idx').on(table.daysOpen),
]);
```

### 5.2 Import Script Structure

```typescript
#!/usr/bin/env npx tsx
import 'dotenv/config';
import { createReadStream } from 'fs';
import { parse } from 'csv-parse';
import { db } from '../client';
import { grirExposures, poLineItems } from '../schema';
import { eq, sql } from 'drizzle-orm';

const CSV_PATH = './data/import-ready/grir_exposures.csv';
const BATCH_SIZE = 100; // Small batches for small dataset

interface CsvRow {
  po_line_id: string;
  grir_qty: string;
  grir_value: string;
  first_exposure_date: string;
  days_open: string;
  time_bucket: string;
  snapshot_date: string;
}

async function buildPoLineIdLookup(): Promise<Map<string, string>> {
  const rows = await db
    .select({ poLineId: poLineItems.poLineId, id: poLineItems.id })
    .from(poLineItems)
    .where(eq(poLineItems.isActive, true));
  return new Map(rows.map(r => [r.poLineId, r.id]));
}

// ... transform, validate, upsert logic
```

### 5.3 Upsert Pattern for Composite Key

```typescript
await db
  .insert(grirExposures)
  .values(records)
  .onConflictDoUpdate({
    target: [grirExposures.poLineItemId, grirExposures.snapshotDate],
    set: {
      grirQty: sql`excluded.grir_qty`,
      grirValue: sql`excluded.grir_value`,
      firstExposureDate: sql`excluded.first_exposure_date`,
      daysOpen: sql`excluded.days_open`,
      timeBucket: sql`excluded.time_bucket`,
      updatedAt: new Date(),
    },
  });
```

---

## 6. Validation Queries

After import, run these to verify data integrity:

```sql
-- Count records
SELECT COUNT(*) FROM dev_v3.grir_exposures;
-- Expected: 65

-- Check FK integrity
SELECT COUNT(*) FROM dev_v3.grir_exposures g
LEFT JOIN dev_v3.po_line_items p ON g.po_line_item_id = p.id
WHERE p.id IS NULL;
-- Expected: 0

-- Total exposure value
SELECT SUM(grir_value::numeric) FROM dev_v3.grir_exposures;
-- Compare with CSV sum

-- Time bucket breakdown
SELECT time_bucket, COUNT(*), SUM(grir_value::numeric)
FROM dev_v3.grir_exposures
GROUP BY time_bucket
ORDER BY time_bucket;
```

---

## 7. Potential Pitfalls

| Pitfall | Symptom | Mitigation |
|---------|---------|------------|
| **Empty import file** | 0 records imported | Check stage2 calculation ran |
| **Date format mismatch** | Import error | Use `format="mixed"` or handle explicitly |
| **Composite key conflict** | Same PO + snapshot exists | Upsert handles this |
| **Negative exposure** | Invalid business logic | Pandera contract validates >= 0 |
| **Invalid time bucket** | Constraint violation | Validate against known buckets |

---

## 8. Success Criteria

- [ ] All 65 exposures imported
- [ ] 0 orphan po_line_ids
- [ ] All FK relationships valid
- [ ] Time bucket values match allowed set
- [ ] Total grir_value matches CSV sum
- [ ] Import completes in < 5 seconds
- [ ] Idempotent (run twice, same result)

---

## 9. Execution Order

1. **Verify pre-conditions** - Ensure po_line_items is imported
2. **Run data profile** - Confirm CSV structure
3. **Update schema** - Add composite unique index
4. **Push schema** - `npm run db:push`
5. **Create import script** - Based on templates above
6. **Dry run** - Test without changes
7. **Import** - Run actual import
8. **Verify** - Run validation queries
9. **Test idempotency** - Run import again
10. **Commit** - Save all changes

---

## Appendix A: File Locations

| Component | Path |
|-----------|------|
| Schema | `src/schema/grir-exposures.ts` |
| Import script (to create) | `src/imports/grir-exposures.ts` |
| Pipeline prepare script | `scripts/stage3_prepare/08_prepare_grir_exposures.py` |
| Column mappings | `scripts/config/column_mappings.py` |
| Import-ready CSV | `data/import-ready/grir_exposures.csv` |
| Pandera contract | `scripts/contracts/grir_exposures_schema.py` |

---

## Appendix B: Business Context

### What is GRIR Exposure?

GRIR exposure occurs when **Invoice Receipt (IR) > Goods Receipt (GR)** for a purchase order. This means:

- Vendor has been paid for goods not yet received
- Money is "out the door" without corresponding inventory
- Creates balance sheet liability and potential NIS impact

### Who Cares About This?

- **Finance:** Monitors exposure for month-end close
- **Procurement:** Investigates long-open exposures
- **Operations:** Expedites GR to clear exposures

### Time Bucket Thresholds

From `scripts/config/column_mappings.py`:

```python
GRIR_TIME_BUCKETS = {
    30: "<1 month",    # Normal
    90: "1-3 months",  # Monitor
    180: "3-6 months", # Investigate
    365: "6-12 months",# Escalate
}
GRIR_TIME_BUCKET_MAX = ">1 year"  # Critical
```

---

## Appendix C: Comparison with po_transactions

| Aspect | po_transactions | grir_exposures |
|--------|-----------------|----------------|
| Volume | 106K | 65 |
| Unique key | Synthetic (transaction_id) | Natural (po_line_id + snapshot) |
| Historical | Yes (many per PO) | Snapshot (one per PO per date) |
| FK handling | Same | Same |
| Orphan rate | 0% | 0% |
| Import time | ~12s | Expected < 1s |
