# Import Plan: po_transactions

> **Status:** Planning  
> **Author:** AI Agent  
> **Date:** 2025-12-02  
> **Predecessor:** po_line_items import (completed)

---

## Overview

This document captures the implementation plan for importing `po_transactions` data into the database, including learnings from the `po_line_items` import.

### Why This Table Next?

| Factor | Reasoning |
|--------|-----------|
| **Dependency** | Direct child of `po_line_items` - tests FK relationship handling |
| **Volume** | 106K records - good performance validation |
| **Complexity** | Requires `po_line_id` → `po_line_item_id` (UUID) lookup |
| **Business value** | Core cost tracking data (GR/IR postings) |

---

## 1. Current State Analysis

### 1.1 Schema Definition

```typescript
// src/schema/po-transactions.ts
poTransactions = devV3Schema.table('po_transactions', {
  id: uuid('id').primaryKey().defaultRandom(),
  poLineItemId: uuid('po_line_item_id').references(() => poLineItems.id),  // FK to parent
  transactionType: varchar('transaction_type').notNull(),  // 'GR' or 'IR'
  postingDate: date('posting_date').notNull(),
  quantity: numeric('quantity').notNull(),
  amount: numeric('amount'),
  costImpactQty: numeric('cost_impact_qty'),
  costImpactAmount: numeric('cost_impact_amount'),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});
```

### 1.2 CSV Structure

File: `data/import-ready/po_transactions.csv`

```csv
po_line_id,transaction_type,posting_date,quantity,cost_impact_qty,cost_impact_amount,amount
4581850069-1,GR,2022-12-15,1.0,1.0,1489.44,1489.44
4581850069-1,IR,2022-12-20,1.0,0.0,0.0,1489.44
```

**Row count:** ~106,000 records

### 1.3 Key Challenge

The CSV contains `po_line_id` (business key like "4581850069-1") but the database requires `po_line_item_id` (UUID foreign key). This requires a lookup/resolution step during import.

---

## 2. Learnings from po_line_items Import

### 2.1 Issues Encountered & Solutions

| Issue | Root Cause | Solution Applied |
|-------|------------|------------------|
| **Numeric strings with .0 suffix** | Pandas reads nullable int columns as float | Created `clean_numeric_string()` function to strip `.0` |
| **Slow row-by-row inserts** | Individual INSERT statements | Switched to bulk upsert with `sql\`excluded.column\`` pattern |
| **Environment variables not loading** | Missing dotenv import | Added `import 'dotenv/config'` at top of script |
| **Date format mismatch** | CSV has "2022-12-01 00:00:00.000" | PostgreSQL DATE type handles this automatically |
| **Pre-commit hook failures** | Schema lock, Oracle regeneration | Run `schema_lock.py --update` and stage generated files |

### 2.2 Patterns That Worked Well

#### Bulk Upsert Pattern
```typescript
await db
  .insert(table)
  .values(batch)
  .onConflictDoUpdate({
    target: table.uniqueKey,
    set: {
      column1: sql`excluded.column1`,
      column2: sql`excluded.column2`,
      updatedAt: new Date(),
    },
  });
```

#### Circuit Breaker Pattern
```typescript
const deactivatePercent = toDeactivateCount / activeCount;
if (deactivatePercent > THRESHOLD && !FORCE_MODE) {
  console.error('CIRCUIT BREAKER TRIGGERED!');
  process.exit(1);
}
```

#### Batch Processing Pattern
```typescript
const BATCH_SIZE = 1000;
for (let i = 0; i < records.length; i += BATCH_SIZE) {
  const batch = records.slice(i, i + BATCH_SIZE);
  await processBatch(batch);
}
```

### 2.3 Performance Benchmarks

| Metric | po_line_items |
|--------|---------------|
| Records | 57,163 |
| Import time | ~14 seconds |
| Batch size | 1,000 |
| Records/second | ~4,000 |

**Expectation for po_transactions:** 106K records should take ~26 seconds.

---

## 3. Design Decisions

### 3.1 Unique Key Strategy

**Problem:** Transactions don't have a natural unique ID in the CSV.

**Options Considered:**

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Composite key (po_line_id + type + date + qty) | No schema change | Risk of duplicates if same PO has identical GRs on same date |
| B | Generate transaction_id in pipeline | Clean, deterministic | Requires pipeline script update |
| C | Hash-based ID (SHA256 of row) | Handles duplicates | Harder to debug |

**Decision:** Option B - Generate `transaction_id` in stage3 prepare script.

Format: `{po_line_id}-{type}-{date}-{sequence}`  
Example: `4581850069-1-GR-2022-12-15-001`

### 3.2 Foreign Key Resolution

```typescript
// Load lookup map once at import start
async function buildPoLineIdLookup(): Promise<Map<string, string>> {
  const rows = await db
    .select({ poLineId: poLineItems.poLineId, id: poLineItems.id })
    .from(poLineItems)
    .where(eq(poLineItems.isActive, true));  // Only active parents
  
  return new Map(rows.map(r => [r.poLineId, r.id]));
}
```

### 3.3 Orphan Transaction Handling

Transactions referencing non-existent `po_line_id`:

| Option | Approach | Risk |
|--------|----------|------|
| A | Skip and log | Data loss, but maintains FK integrity |
| B | Create ghost parent record | Pollutes parent table |
| C | Store in quarantine table | Complex, requires new table |

**Decision:** Option A - Skip orphans with detailed logging.

```typescript
if (orphans.length > 0) {
  console.log(`  Warning: ${orphans.length} orphan transactions skipped`);
  console.log(`  Sample orphan po_line_ids: ${orphans.slice(0, 5).join(', ')}`);
}
```

### 3.4 Soft Delete Strategy

**Question:** Should transactions have `is_active` column?

**Analysis:**
- Transactions are historical facts (GR/IR events that occurred)
- They shouldn't "disappear" from source exports
- Parent PO deactivation shouldn't affect transaction history
- If transactions disappear, it indicates upstream data issue

**Decision:** No soft delete for transactions.
- Use circuit breaker with **lower threshold (1%)** instead of 5%
- If >1% transactions would be deleted, abort and investigate

### 3.5 Handling Parent Deactivation

When a `po_line_item` is soft-deleted (`is_active = false`):
- Its transactions remain in the database (historical record)
- FK still valid (parent row exists, just inactive)
- Queries should filter: `WHERE po_line_items.is_active = true`

---

## 4. Implementation Checklist

### 4.1 Pre-Implementation

- [ ] Read current `src/schema/po-transactions.ts`
- [ ] Analyze CSV with `python scripts/profile_data.py data/import-ready/po_transactions.csv`
- [ ] Verify no duplicate rows in CSV
- [ ] Check for orphan po_line_ids (not in po_line_items)

### 4.2 Schema Updates

- [ ] Add `transaction_id` varchar column (unique business key)
- [ ] Add `is_active` boolean if decided (currently: NO)
- [ ] Add index on `po_line_item_id` for FK lookups
- [ ] Add index on `transaction_id` for upserts
- [ ] Run `npm run type-check`
- [ ] Run `npm run db:push`

### 4.3 Pipeline Updates

File: `scripts/stage3_prepare/07_prepare_po_transactions.py`

- [ ] Generate `transaction_id` column
- [ ] Clean numeric string columns if needed
- [ ] Validate with Pandera contract
- [ ] Verify output CSV structure

### 4.4 Import Script

File: `src/imports/po-transactions.ts`

- [ ] Copy structure from `po-line-items.ts`
- [ ] Add FK lookup function (`buildPoLineIdLookup`)
- [ ] Transform records (resolve po_line_id → UUID)
- [ ] Handle orphan transactions (skip + log)
- [ ] Bulk upsert with ON CONFLICT on transaction_id
- [ ] Circuit breaker at 1% threshold
- [ ] Detailed stats logging

### 4.5 Testing

- [ ] Run with `--dry-run` flag first
- [ ] Test with small subset (first 1000 rows)
- [ ] Verify FK relationships in database
- [ ] Check orphan handling works
- [ ] Performance test full dataset
- [ ] Verify idempotency (run twice, same result)

### 4.6 Post-Implementation

- [ ] Add npm scripts to package.json
- [ ] Update AGENTS.md if needed
- [ ] Commit with descriptive message
- [ ] Push to remote

---

## 5. Code Templates

### 5.1 FK Lookup Function

```typescript
async function buildPoLineIdLookup(): Promise<Map<string, string>> {
  console.log('Building po_line_id → UUID lookup...');
  
  const rows = await db
    .select({ 
      poLineId: poLineItems.poLineId, 
      id: poLineItems.id 
    })
    .from(poLineItems)
    .where(eq(poLineItems.isActive, true));
  
  const lookup = new Map(rows.map(r => [r.poLineId, r.id]));
  console.log(`  Loaded ${lookup.size.toLocaleString()} active PO line items`);
  
  return lookup;
}
```

### 5.2 Orphan Detection

```typescript
function resolveParentIds(
  records: CsvRow[], 
  lookup: Map<string, string>
): { resolved: TransactionRecord[], orphans: string[] } {
  const resolved: TransactionRecord[] = [];
  const orphans: string[] = [];
  const orphanSet = new Set<string>();
  
  for (const record of records) {
    const parentId = lookup.get(record.po_line_id);
    
    if (!parentId) {
      if (!orphanSet.has(record.po_line_id)) {
        orphans.push(record.po_line_id);
        orphanSet.add(record.po_line_id);
      }
      continue;
    }
    
    resolved.push({
      ...transformRecord(record),
      poLineItemId: parentId,
    });
  }
  
  return { resolved, orphans };
}
```

### 5.3 Transaction ID Generation (Pipeline)

```python
def generate_transaction_id(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate unique transaction_id for each row.
    Format: {po_line_id}-{type}-{date}-{seq}
    """
    # Sort to ensure consistent ordering
    df = df.sort_values(['PO Line ID', 'Posting Type', 'Posting Date'])
    
    # Group and add sequence number
    df['seq'] = df.groupby(['PO Line ID', 'Posting Type', 'Posting Date']).cumcount() + 1
    
    # Format date for ID
    df['date_str'] = pd.to_datetime(df['Posting Date']).dt.strftime('%Y%m%d')
    
    # Generate ID
    df['transaction_id'] = (
        df['PO Line ID'] + '-' + 
        df['Posting Type'] + '-' + 
        df['date_str'] + '-' + 
        df['seq'].astype(str).str.zfill(3)
    )
    
    # Cleanup temp columns
    df = df.drop(columns=['seq', 'date_str'])
    
    return df
```

---

## 6. Potential Pitfalls

| Pitfall | Symptom | Mitigation |
|---------|---------|------------|
| **UUID lookup too slow** | Import takes minutes | Load all mappings into Map once at start |
| **Memory exhaustion** | Process crashes at 80K records | Process in batches, don't load all at once |
| **Orphan cascade** | Many transactions fail FK | Run po_line_items import first, verify success |
| **Duplicate transaction_id** | Unique constraint violation | Ensure generation logic handles edge cases |
| **Date parsing errors** | Invalid date format | Test with sample data, handle edge cases |
| **Inactive parent lookup** | Transactions link to wrong parent | Filter lookup to `is_active = true` only |

---

## 7. Rollback Plan

If import fails or produces bad data:

1. **Identify scope:** Check `updated_at` timestamps to find affected records
2. **Delete new records:** `DELETE FROM po_transactions WHERE updated_at > '{import_start_time}'`
3. **Re-run previous import:** Use last known good CSV
4. **Investigate:** Check logs for root cause before retrying

---

## 8. Success Criteria

- [ ] All ~106K transactions imported
- [ ] < 1% orphan transactions (ideally 0)
- [ ] All FK relationships valid
- [ ] Import completes in < 60 seconds
- [ ] Re-running import produces same result (idempotent)
- [ ] Circuit breaker tested and working

---

## 9. Execution Order

1. **Profile data** - Understand current CSV structure
2. **Update schema** - Add transaction_id column
3. **Update pipeline** - Generate transaction_id in stage3
4. **Re-run pipeline** - Generate updated CSV
5. **Create import script** - Based on po-line-items template
6. **Dry run** - Test without DB changes
7. **Import** - Run actual import
8. **Verify** - Check data integrity
9. **Commit** - Save all changes

---

## Appendix: File Locations

| Component | Path |
|-----------|------|
| Schema | `src/schema/po-transactions.ts` |
| Import script (to create) | `src/imports/po-transactions.ts` |
| Pipeline prepare script | `scripts/stage3_prepare/07_prepare_po_transactions.py` |
| Column mappings | `scripts/config/column_mappings.py` |
| Import-ready CSV | `data/import-ready/po_transactions.csv` |
| Pandera contract | `scripts/contracts/po_transactions_schema.py` |
