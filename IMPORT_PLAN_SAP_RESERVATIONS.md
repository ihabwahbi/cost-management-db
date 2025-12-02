# Import Plan: sap_reservations

> **Status:** Planning  
> **Author:** AI Agent  
> **Date:** 2025-12-02  
> **Predecessor:** wbs_details import (pending)

---

## Overview

This document captures the implementation plan for importing `sap_reservations` data into the database. SAP Reservations track material requirements for operations, linking to WBS elements and purchase orders.

### Why This Table Last?

| Factor | Reasoning |
|--------|-----------|
| **Dependencies** | FK to `wbs_details.wbs_number` - must import wbs_details first |
| **Also References** | FK to `po_line_items.poLineId` - already imported |
| **Nullable FKs** | Both FKs are nullable (~80% null WBS, ~65% null PO) |
| **Orphan Handling** | Has orphans in both FK columns - needs special handling |
| **Final Table** | Completes all 5 pipeline-generated imports |

---

## 1. Current State Analysis

### 1.1 Schema Definition

```typescript
// src/schema/sap-reservations.ts
sapReservations = devV3Schema.table('sap_reservations', {
  id: uuid('id').primaryKey().defaultRandom(),
  
  // Business key - unique
  reservationLineId: varchar('reservation_line_id').notNull().unique(),
  
  // Split components
  reservationNumber: varchar('reservation_number').notNull(),
  reservationLineNumber: integer('reservation_line_number').notNull(),
  reservationRequirementDate: date('reservation_requirement_date'),
  reservationCreationDate: date('reservation_creation_date'),
  
  partNumber: varchar('part_number'),
  description: text('description'),
  
  openReservationQty: numeric('open_reservation_qty'),
  openReservationValue: numeric('open_reservation_value'),
  
  reservationStatus: varchar('reservation_status'),
  reservationSource: varchar('reservation_source'),
  
  poNumber: varchar('po_number'),
  poLineNumber: integer('po_line_number'),
  
  // FK to wbs_details (VARCHAR to VARCHAR - nullable)
  wbsNumber: varchar('wbs_number').references(() => wbsDetails.wbsNumber),
  
  assetCode: varchar('asset_code'),
  assetSerialNumber: varchar('asset_serial_number'),
  plantCode: varchar('plant_code'),
  requesterAlias: varchar('requester_alias'),
  
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
  
  // FK to po_line_items via business key (VARCHAR to VARCHAR - nullable!)
  poLineItemId: varchar('po_line_item_id').references(() => poLineItems.poLineId),
}, (table) => [
  unique('sap_reservations_unique_line').on(table.reservationNumber, table.reservationLineNumber),
  index('sap_reservations_po_line_item_id_idx').on(table.poLineItemId),
]);
```

### 1.2 CSV Structure

File: `data/import-ready/sap_reservations.csv`

```csv
reservation_line_id,reservation_number,reservation_line_number,reservation_creation_date,reservation_requirement_date,part_number,description,open_reservation_qty,open_reservation_value,reservation_status,reservation_source,wbs_number,requester_alias,plant_code,po_number,po_line_number,po_line_item_id,asset_code,asset_serial_number
6086214878-1,6086214878,1,2025-11-24,2025-11-25,100109883,"CENTER BODY, ARM MOUNTING",1.0,5757.2104,04. PO Available to Peg,MAXIMO,,02307312,3606,4584632148,1,4584632148-1,,
```

**Row count:** 1,483 records

### 1.3 Data Profile Summary

| Column | Type | Nulls | Unique | Notes |
|--------|------|-------|--------|-------|
| `reservation_line_id` | string | 0% | 1,483 | **Unique** - business key |
| `reservation_number` | int | 0% | 592 | Reservation header ID |
| `reservation_line_number` | int | 0% | 36 | Line within reservation |
| `reservation_creation_date` | date | 0% | 295 | When created |
| `reservation_requirement_date` | date | 0% | 314 | When needed |
| `part_number` | string | 0% | 1,134 | Material number |
| `description` | string | 0% | 1,105 | Material description |
| `open_reservation_qty` | float | 0% | 48 | Quantity needed |
| `open_reservation_value` | float | 0% | 1,247 | Value in USD |
| `reservation_status` | string | 0% | 6 | Status code |
| `reservation_source` | string | 0% | 3 | MAXIMO, SAP - MANUAL, etc. |
| `wbs_number` | string | **79.97%** | 21 | FK to wbs_details |
| `requester_alias` | string | 0.94% | 93 | Who requested |
| `plant_code` | int | 0% | 6 | Plant location |
| `po_number` | float | **65.14%** | 228 | PO number (if pegged) |
| `po_line_number` | float | **65.14%** | 35 | PO line (if pegged) |
| `po_line_item_id` | string | **65.14%** | 494 | FK to po_line_items |
| `asset_code` | string | 54.62% | 165 | Asset identifier |
| `asset_serial_number` | string | 56.57% | 254 | Asset serial |

### 1.4 Key Observations

1. **High null rates on FKs** - 80% null WBS, 65% null PO (by design - not all reservations are pegged)
2. **VARCHAR FK to VARCHAR** - `po_line_item_id` references `poLineItems.poLineId` (business key, NOT UUID!)
3. **Orphan WBS exists** - 1 WBS (`C.FT003347`) not in wbs_details
4. **Orphan PO IDs exist** - 9 po_line_ids not in po_line_items
5. **Unique constraints** - `reservation_line_id` is unique, also `(reservation_number, reservation_line_number)`

### 1.5 Orphan Analysis

```
Reservations with WBS: 297 (20% of records)
Unique WBS in reservations: 21
Orphan WBS: 1 (C.FT003347)

Reservations with PO: 517 (35% of records)  
Unique PO Line IDs: 494
Orphan PO Line IDs: 9
  - 9000225482-1, 4584622158-1, 4584616194-1, 4584617285-1
  - 4584624063-1, 4584592615-19, 4584629370-3, 4584629369-2
  - 4581905271-1
```

### 1.6 Status Distribution

| Status | Count | % |
|--------|-------|---|
| 05. No PO Available to Peg | ~60% | No PO linked |
| 04. PO Available to Peg | ~25% | PO linked |
| 01. SOH Available to Peg | ~10% | Stock on hand |
| Others | ~5% | Various states |

---

## 2. Critical Differences from Previous Imports

### 2.1 VARCHAR FK to VARCHAR (NOT UUID!)

**This is different from po_transactions and grir_exposures!**

Previous imports:
```typescript
// po_transactions, grir_exposures - UUID FK
poLineItemId: uuid('po_line_item_id').references(() => poLineItems.id)
```

This import:
```typescript
// sap_reservations - VARCHAR FK to business key
poLineItemId: varchar('po_line_item_id').references(() => poLineItems.poLineId)
```

**Impact:**
- No UUID lookup needed for po_line_items FK
- Direct string comparison for orphan detection
- Can insert `po_line_item_id` value directly from CSV

### 2.2 Nullable FKs (Both Can Be Null)

Previous imports had required FKs (orphans were skipped entirely).

This import:
- `wbs_number` - nullable by design (~80% are null)
- `po_line_item_id` - nullable by design (~65% are null)

**Impact:**
- Don't skip records with null FKs
- Only nullify orphan FK values (FK exists in CSV but parent doesn't exist)

### 2.3 Orphan Handling Strategy

**Previous (po_transactions, grir_exposures):**
```typescript
if (!parentId) {
  orphanCount++;
  continue;  // Skip entire record
}
```

**This import (sap_reservations):**
```typescript
// For orphan WBS - set to null (don't skip record)
if (row.wbs_number && !wbsExists.has(row.wbs_number)) {
  record.wbsNumber = null;
  orphanWbsSet.add(row.wbs_number);
}

// For orphan PO - set to null (don't skip record)
if (row.po_line_item_id && !poLineExists.has(row.po_line_item_id)) {
  record.poLineItemId = null;
  orphanPoSet.add(row.po_line_item_id);
}
```

---

## 3. Learnings from Previous Imports

### 3.1 Consolidated Learnings

| Issue | Solution |
|-------|----------|
| Numeric strings with `.0` suffix | `clean_numeric_string()` |
| Slow inserts | Bulk upsert with batching |
| FK lookup at scale | Build `Set<string>` once at start |
| Composite key upserts | `target: [col1, col2]` or use unique column |
| Array columns (wbs_details) | Parse `{val1,val2}` to JS array |
| VARCHAR PK (wbs_details) | Upsert on string column works fine |

### 3.2 Performance Expectations

| Import | Records | Time |
|--------|---------|------|
| po_line_items | 57K | ~14s |
| po_transactions | 106K | ~12s |
| grir_exposures | 65 | <1s |
| wbs_details | 7,852 | ~2s expected |
| **sap_reservations** | **1,483** | **<2s expected** |

---

## 4. Design Decisions

### 4.1 Unique Key Strategy

**Decision:** Upsert on `reservation_line_id` (unique varchar column)

**Rationale:**
- `reservation_line_id` is already unique in schema
- Simpler than composite key `(reservation_number, reservation_line_number)`
- 100% unique in source data

### 4.2 FK Validation Strategy

**Decision:** Build two lookup Sets, not Maps (no UUID needed)

```typescript
// For wbs_number validation
const wbsExists: Set<string> = new Set(
  await db.select({ wbsNumber: wbsDetails.wbsNumber }).from(wbsDetails)
    .then(rows => rows.map(r => r.wbsNumber))
);

// For po_line_item_id validation
const poLineExists: Set<string> = new Set(
  await db.select({ poLineId: poLineItems.poLineId }).from(poLineItems)
    .where(eq(poLineItems.isActive, true))
    .then(rows => rows.map(r => r.poLineId))
);
```

### 4.3 Orphan Handling Strategy

**Decision:** Set FK to null, log orphan value, continue import

**Rationale:**
- Reservations are valid even without WBS/PO
- 80% don't have WBS anyway (by design)
- Better to import all data than skip records
- Orphan logging allows investigation

### 4.4 Date Handling

**Decision:** Use standard date parsing (same as other imports)

```typescript
function parseDate(val: string): string | null {
  if (val === '' || val === null || val === undefined) return null;
  return val.split(' ')[0];  // Handle datetime format
}
```

---

## 5. Implementation Checklist

### 5.1 Pre-Implementation

- [ ] Verify wbs_details import is complete
- [ ] Profile CSV: `python3 scripts/profile_data.py data/import-ready/sap_reservations.csv`
- [ ] Verify reservation_line_id uniqueness
- [ ] Confirm orphan counts match analysis

### 5.2 Schema Updates

**Status:** No changes needed - schema already correct.

File: `src/schema/sap-reservations.ts`

- [ ] Verify unique constraint on `reservation_line_id`
- [ ] Verify FK references are correct (VARCHAR to VARCHAR)
- [ ] Run `npm run type-check`

### 5.3 Pipeline Updates

**Status:** No changes needed.

File: `scripts/stage3_prepare/10_prepare_reservations.py`

The current script already:
- Maps all columns correctly
- Extracts PO info (po_number, po_line_number, po_line_item_id)
- Extracts asset info (asset_code, asset_serial_number)
- Converts plant_code to string
- Validates uniqueness

### 5.4 Import Script

File: `src/imports/sap-reservations.ts`

- [ ] Create new import script
- [ ] Build WBS existence Set (not Map - no UUID lookup needed)
- [ ] Build PO Line ID existence Set
- [ ] Transform records with orphan FK nullification
- [ ] Upsert on `reservationLineId`
- [ ] Log orphan WBS and PO values separately
- [ ] Stats logging (status distribution, plant breakdown)

### 5.5 Testing

- [ ] Run with `--dry-run` first
- [ ] Verify orphan handling (null FKs, not skipped records)
- [ ] Check that all 1,483 records import (none skipped)
- [ ] Verify FK integrity for non-null values
- [ ] Test idempotency (run twice)
- [ ] Verify totals (open_reservation_value sum)

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
import { sapReservations, wbsDetails, poLineItems } from '../schema';
import { eq, sql } from 'drizzle-orm';

const CSV_PATH = './data/import-ready/sap_reservations.csv';
const BATCH_SIZE = 500;

interface CsvRow {
  reservation_line_id: string;
  reservation_number: string;
  reservation_line_number: string;
  reservation_creation_date: string;
  reservation_requirement_date: string;
  part_number: string;
  description: string;
  open_reservation_qty: string;
  open_reservation_value: string;
  reservation_status: string;
  reservation_source: string;
  wbs_number: string;
  requester_alias: string;
  plant_code: string;
  po_number: string;
  po_line_number: string;
  po_line_item_id: string;
  asset_code: string;
  asset_serial_number: string;
}

type SapReservationInsert = typeof sapReservations.$inferInsert;
```

### 6.2 FK Existence Lookups (Not UUID Maps!)

```typescript
/**
 * Build Set of existing WBS numbers for FK validation.
 * NOTE: Set, not Map - we only need existence check, not UUID lookup.
 */
async function buildWbsExistsSet(): Promise<Set<string>> {
  console.log('Building WBS existence set...');
  
  const rows = await db
    .select({ wbsNumber: wbsDetails.wbsNumber })
    .from(wbsDetails);
  
  const wbsSet = new Set(rows.map(r => r.wbsNumber));
  console.log(`  Loaded ${wbsSet.size.toLocaleString()} WBS numbers`);
  
  return wbsSet;
}

/**
 * Build Set of existing PO Line IDs for FK validation.
 * NOTE: Using poLineId (business key), not UUID id.
 */
async function buildPoLineExistsSet(): Promise<Set<string>> {
  console.log('Building PO Line ID existence set...');
  
  const rows = await db
    .select({ poLineId: poLineItems.poLineId })
    .from(poLineItems)
    .where(eq(poLineItems.isActive, true));
  
  const poSet = new Set(rows.map(r => r.poLineId));
  console.log(`  Loaded ${poSet.size.toLocaleString()} active PO line IDs`);
  
  return poSet;
}
```

### 6.3 Transform with Orphan Handling

```typescript
interface OrphanTracking {
  orphanWbs: Set<string>;
  orphanPo: Set<string>;
}

function transformRecords(
  rows: CsvRow[],
  wbsExists: Set<string>,
  poLineExists: Set<string>
): { records: SapReservationInsert[], orphans: OrphanTracking } {
  const records: SapReservationInsert[] = [];
  const orphans: OrphanTracking = {
    orphanWbs: new Set(),
    orphanPo: new Set(),
  };
  
  for (const row of rows) {
    // Check WBS FK - nullify if orphan
    let wbsNumber: string | null = str(row.wbs_number);
    if (wbsNumber && !wbsExists.has(wbsNumber)) {
      orphans.orphanWbs.add(wbsNumber);
      wbsNumber = null;
    }
    
    // Check PO FK - nullify if orphan
    let poLineItemId: string | null = str(row.po_line_item_id);
    if (poLineItemId && !poLineExists.has(poLineItemId)) {
      orphans.orphanPo.add(poLineItemId);
      poLineItemId = null;
    }
    
    records.push({
      reservationLineId: row.reservation_line_id,
      reservationNumber: row.reservation_number,
      reservationLineNumber: parseInt(row.reservation_line_number, 10),
      reservationCreationDate: parseDate(row.reservation_creation_date),
      reservationRequirementDate: parseDate(row.reservation_requirement_date),
      partNumber: str(row.part_number),
      description: str(row.description),
      openReservationQty: parseNumeric(row.open_reservation_qty),
      openReservationValue: parseNumeric(row.open_reservation_value),
      reservationStatus: str(row.reservation_status),
      reservationSource: str(row.reservation_source),
      wbsNumber: wbsNumber,  // May be nullified
      requesterAlias: str(row.requester_alias),
      plantCode: str(row.plant_code),
      poNumber: str(row.po_number),
      poLineNumber: parseInt_(row.po_line_number),
      poLineItemId: poLineItemId,  // May be nullified
      assetCode: str(row.asset_code),
      assetSerialNumber: str(row.asset_serial_number),
      updatedAt: new Date(),
    });
  }
  
  return { records, orphans };
}
```

### 6.4 Upsert on VARCHAR Unique Column

```typescript
async function upsertBatch(records: SapReservationInsert[]): Promise<number> {
  if (records.length === 0) return 0;
  
  await db
    .insert(sapReservations)
    .values(records)
    .onConflictDoUpdate({
      target: sapReservations.reservationLineId,  // VARCHAR unique column
      set: {
        reservationNumber: sql`excluded.reservation_number`,
        reservationLineNumber: sql`excluded.reservation_line_number`,
        reservationCreationDate: sql`excluded.reservation_creation_date`,
        reservationRequirementDate: sql`excluded.reservation_requirement_date`,
        partNumber: sql`excluded.part_number`,
        description: sql`excluded.description`,
        openReservationQty: sql`excluded.open_reservation_qty`,
        openReservationValue: sql`excluded.open_reservation_value`,
        reservationStatus: sql`excluded.reservation_status`,
        reservationSource: sql`excluded.reservation_source`,
        wbsNumber: sql`excluded.wbs_number`,
        requesterAlias: sql`excluded.requester_alias`,
        plantCode: sql`excluded.plant_code`,
        poNumber: sql`excluded.po_number`,
        poLineNumber: sql`excluded.po_line_number`,
        poLineItemId: sql`excluded.po_line_item_id`,
        assetCode: sql`excluded.asset_code`,
        assetSerialNumber: sql`excluded.asset_serial_number`,
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
SELECT COUNT(*) FROM dev_v3.sap_reservations;
-- Expected: 1,483

-- Check FK integrity for WBS (non-null values only)
SELECT COUNT(*) FROM dev_v3.sap_reservations r
LEFT JOIN dev_v3.wbs_details w ON r.wbs_number = w.wbs_number
WHERE r.wbs_number IS NOT NULL AND w.wbs_number IS NULL;
-- Expected: 0 (orphans were nullified)

-- Check FK integrity for PO (non-null values only)
SELECT COUNT(*) FROM dev_v3.sap_reservations r
LEFT JOIN dev_v3.po_line_items p ON r.po_line_item_id = p.po_line_id
WHERE r.po_line_item_id IS NOT NULL AND p.po_line_id IS NULL;
-- Expected: 0 (orphans were nullified)

-- Count by status
SELECT reservation_status, COUNT(*) 
FROM dev_v3.sap_reservations 
GROUP BY reservation_status 
ORDER BY COUNT(*) DESC;

-- Total reservation value
SELECT SUM(open_reservation_value::numeric) FROM dev_v3.sap_reservations;

-- Count with WBS vs without
SELECT 
  COUNT(*) FILTER (WHERE wbs_number IS NOT NULL) as with_wbs,
  COUNT(*) FILTER (WHERE wbs_number IS NULL) as without_wbs
FROM dev_v3.sap_reservations;
-- Expected: ~297 with WBS, ~1186 without

-- Count with PO vs without
SELECT 
  COUNT(*) FILTER (WHERE po_line_item_id IS NOT NULL) as with_po,
  COUNT(*) FILTER (WHERE po_line_item_id IS NULL) as without_po
FROM dev_v3.sap_reservations;
-- Expected: ~508 with PO (517 - 9 orphans), ~975 without
```

---

## 8. Potential Pitfalls

| Pitfall | Symptom | Mitigation |
|---------|---------|------------|
| **Confusing FK pattern** | UUID lookup when not needed | Use Set<string> for existence check only |
| **Skipping valid records** | Low import count | Nullify orphan FKs, don't skip records |
| **Integer overflow** | reservation_number parsing error | Keep as varchar, not integer |
| **Date format issues** | Parse error | Use standard date parsing |
| **Null FK confusion** | All FKs become null | Only nullify if value exists AND is orphan |
| **WBS not imported yet** | All WBS become null | Ensure wbs_details import completes first |

---

## 9. Success Criteria

- [ ] All 1,483 reservations imported (none skipped)
- [ ] 1 orphan WBS nullified (`C.FT003347`)
- [ ] 9 orphan PO IDs nullified
- [ ] FK integrity verified for all non-null values
- [ ] Status distribution matches source
- [ ] Total open_reservation_value matches CSV sum
- [ ] Import completes in < 5 seconds
- [ ] Idempotent (run twice, same result)

---

## 10. Execution Order

1. **Wait for wbs_details** - Must complete first (FK dependency)
2. **Verify pre-conditions** - Confirm WBS import, profile CSV
3. **Verify schema** - No changes needed
4. **Create import script** - Based on templates above
5. **Dry run** - Test without changes
6. **Import** - Run actual import
7. **Verify** - Run validation queries
8. **Check orphan logs** - Confirm expected orphans
9. **Test idempotency** - Run import again
10. **Commit** - Save all changes

---

## Appendix A: File Locations

| Component | Path |
|-----------|------|
| Schema | `src/schema/sap-reservations.ts` |
| Import script (to create) | `src/imports/sap-reservations.ts` |
| Pipeline prepare script | `scripts/stage3_prepare/10_prepare_reservations.py` |
| Column mappings | `scripts/config/column_mappings.py` |
| Import-ready CSV | `data/import-ready/sap_reservations.csv` |

---

## Appendix B: Business Context

### What are SAP Reservations?

SAP Reservations are material requirements created in the SAP system:

- **Work Order Reservations** - Parts needed for maintenance work orders
- **Manual Reservations** - Ad-hoc material requests
- **Maximo Integration** - Reservations synced from Maximo CMMS

### Reservation Lifecycle

```
Created → Stock Check → Pegging → PO Created → GR → Issue
   │           │            │
   │           ▼            ▼
   │    01. SOH Available   04. PO Available
   │           │            ▼
   │           ▼         PO links to reservation
   │    02. SOH Partially
   │           │
   │           ▼
   └─────► 05. No PO Available ──► Procurement needed
```

### WBS Linkage

Reservations can be linked to WBS elements for:
- Cost allocation to projects/operations
- Budget tracking
- Project visibility into material needs

### PO Linkage

When a PO is created to fulfill a reservation:
- `po_line_item_id` links to the PO line
- Status changes to "04. PO Available to Peg"
- Enables tracking from need → order → receipt

---

## Appendix C: Comparison Table

| Aspect | po_transactions | grir_exposures | wbs_details | sap_reservations |
|--------|-----------------|----------------|-------------|------------------|
| Volume | 106K | 65 | 7,852 | **1,483** |
| PK Type | UUID | UUID | VARCHAR | **UUID** |
| Unique Key | transaction_id | (po_line_item_id, snapshot) | wbs_number | **reservation_line_id** |
| FK Type | UUID lookup | UUID lookup | None | **VARCHAR to VARCHAR** |
| Nullable FKs | No | No | N/A | **Yes (both)** |
| Orphan Strategy | Skip record | Skip record | N/A | **Nullify FK only** |
| Import Time | ~12s | <1s | ~2s | **<2s expected** |

---

## Appendix D: Known Orphans

### Orphan WBS (1)

| WBS Number | Reservations Affected |
|------------|----------------------|
| `C.FT003347` | Unknown (investigate if needed) |

This WBS format doesn't match standard `J.XX.XXXXXX` pattern - likely a legacy or test value.

### Orphan PO Line IDs (9)

| PO Line ID | Likely Reason |
|------------|---------------|
| `9000225482-1` | Different PO numbering system |
| `4584622158-1` | PO was deleted/cancelled |
| `4584616194-1` | PO was deleted/cancelled |
| `4584617285-1` | PO was deleted/cancelled |
| `4584624063-1` | PO was deleted/cancelled |
| `4584592615-19` | PO was deleted/cancelled |
| `4584629370-3` | PO was deleted/cancelled |
| `4584629369-2` | PO was deleted/cancelled |
| `4581905271-1` | PO was deleted/cancelled |

These are valid reservations that reference POs not in the current po_line_items export. The POs may have been:
- Cancelled after reservation was created
- From a different data extract period
- Deleted for compliance reasons

Import continues with FK set to null - reservation data is preserved.
