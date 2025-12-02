#!/usr/bin/env npx tsx
/**
 * PO Transactions Import Script
 * 
 * Imports po_transactions.csv into the database with:
 * - FK lookup (po_line_id → po_line_item_id UUID)
 * - Upsert on transaction_id (insert new, update existing)
 * - Orphan handling (skip transactions with missing parent)
 * - Circuit breaker (abort if >1% would be deleted)
 * 
 * Note: Unlike po_line_items, transactions are NOT soft-deleted.
 * They are historical facts that shouldn't disappear.
 * 
 * Usage:
 *   npx tsx src/imports/po-transactions.ts
 *   npx tsx src/imports/po-transactions.ts --force  # Skip circuit breaker
 *   npx tsx src/imports/po-transactions.ts --dry-run  # Preview without changes
 */

import 'dotenv/config';
import { createReadStream } from 'fs';
import { parse } from 'csv-parse';
import { db } from '../client';
import { poTransactions, poLineItems } from '../schema';
import { eq, sql } from 'drizzle-orm';

// Configuration
const CSV_PATH = './data/import-ready/po_transactions.csv';
const CIRCUIT_BREAKER_THRESHOLD = 0.01; // 1% - stricter for transactions
const BATCH_SIZE = 1000;

// Parse CLI args
const args = process.argv.slice(2);
const FORCE_MODE = args.includes('--force');
const DRY_RUN = args.includes('--dry-run');

interface CsvRow {
  transaction_id: string;
  po_line_id: string;
  transaction_type: string;
  posting_date: string;
  quantity: string;
  amount: string;
  cost_impact_qty: string;
  cost_impact_amount: string;
}

type POTransactionInsert = typeof poTransactions.$inferInsert;

/**
 * Parse CSV file and return rows
 */
async function loadCsv(filePath: string): Promise<CsvRow[]> {
  return new Promise((resolve, reject) => {
    const rows: CsvRow[] = [];
    
    createReadStream(filePath)
      .pipe(parse({ 
        columns: true,
        skip_empty_lines: true,
        trim: true
      }))
      .on('data', (row: CsvRow) => rows.push(row))
      .on('end', () => resolve(rows))
      .on('error', reject);
  });
}

/**
 * Build lookup map from po_line_id → UUID
 * Only includes active po_line_items
 */
async function buildPoLineIdLookup(): Promise<Map<string, string>> {
  console.log('Building po_line_id -> UUID lookup...');
  
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

/**
 * Helper to parse date fields (extract date part from datetime string)
 * postingDate is required, so we return a fallback date if missing (should never happen)
 */
function parseDate(val: string): string {
  if (val === '' || val === null || val === undefined) {
    console.warn('  Warning: Empty date value found, using fallback');
    return '1900-01-01';
  }
  // Handle "2022-12-01 00:00:00.000" format - extract just the date
  return val.split(' ')[0];
}

/**
 * Helper to parse numeric string to proper format
 */
function parseNumeric(val: string): string {
  if (val === '' || val === null || val === undefined) return '0';
  return val;
}

/**
 * Resolve parent IDs and separate orphans
 */
function resolveParentIds(
  rows: CsvRow[], 
  lookup: Map<string, string>
): { resolved: POTransactionInsert[], orphanPoLineIds: string[] } {
  const resolved: POTransactionInsert[] = [];
  const orphanSet = new Set<string>();
  
  for (const row of rows) {
    const parentId = lookup.get(row.po_line_id);
    
    if (!parentId) {
      orphanSet.add(row.po_line_id);
      continue;
    }
    
    resolved.push({
      transactionId: row.transaction_id,
      poLineItemId: parentId,
      transactionType: row.transaction_type,
      postingDate: parseDate(row.posting_date),
      quantity: parseNumeric(row.quantity),
      amount: parseNumeric(row.amount),
      costImpactQty: parseNumeric(row.cost_impact_qty),
      costImpactAmount: parseNumeric(row.cost_impact_amount),
      updatedAt: new Date(),
    });
  }
  
  return { 
    resolved, 
    orphanPoLineIds: Array.from(orphanSet) 
  };
}

/**
 * Upsert records in batches
 */
async function upsertBatch(records: POTransactionInsert[]): Promise<number> {
  if (records.length === 0) return 0;
  
  await db
    .insert(poTransactions)
    .values(records)
    .onConflictDoUpdate({
      target: poTransactions.transactionId,
      set: {
        poLineItemId: sql`excluded.po_line_item_id`,
        transactionType: sql`excluded.transaction_type`,
        postingDate: sql`excluded.posting_date`,
        quantity: sql`excluded.quantity`,
        amount: sql`excluded.amount`,
        costImpactQty: sql`excluded.cost_impact_qty`,
        costImpactAmount: sql`excluded.cost_impact_amount`,
        updatedAt: new Date(),
      },
    });
  
  return records.length;
}

/**
 * Main import function
 */
async function main() {
  console.log('='.repeat(60));
  console.log('PO Transactions Import');
  console.log('='.repeat(60));
  
  if (DRY_RUN) {
    console.log('*** DRY RUN MODE - No changes will be made ***\n');
  }
  if (FORCE_MODE) {
    console.log('*** FORCE MODE - Circuit breaker disabled ***\n');
  }

  // Step 1: Load CSV
  console.log('\n[1/6] Loading CSV...');
  const rows = await loadCsv(CSV_PATH);
  console.log(`  Loaded ${rows.length.toLocaleString()} rows from CSV`);
  
  // Step 2: Basic validation
  console.log('\n[2/6] Validating...');
  if (rows.length < 1000) {
    console.error(`  ERROR: Only ${rows.length} rows in file - suspiciously low!`);
    console.error('  Aborting to prevent data loss. Use --force to override.');
    if (!FORCE_MODE) {
      process.exit(1);
    }
  }
  
  // Check for required fields
  const invalidRows = rows.filter(r => !r.transaction_id || !r.po_line_id || !r.transaction_type);
  if (invalidRows.length > 0) {
    console.error(`  ERROR: ${invalidRows.length} rows missing required fields`);
    process.exit(1);
  }
  
  // Check transaction types
  const validTypes = new Set(['GR', 'IR']);
  const invalidTypeRows = rows.filter(r => !validTypes.has(r.transaction_type));
  if (invalidTypeRows.length > 0) {
    console.error(`  ERROR: ${invalidTypeRows.length} rows with invalid transaction_type`);
    console.error(`  Sample invalid types: ${[...new Set(invalidTypeRows.map(r => r.transaction_type))].slice(0, 5).join(', ')}`);
    process.exit(1);
  }
  console.log('  Validation passed');
  
  // Step 3: Build FK lookup
  console.log('\n[3/6] Building FK lookup...');
  const lookup = await buildPoLineIdLookup();
  
  // Step 4: Resolve parent IDs
  console.log('\n[4/6] Resolving parent IDs...');
  const { resolved, orphanPoLineIds } = resolveParentIds(rows, lookup);
  
  console.log(`  Resolved: ${resolved.length.toLocaleString()} transactions`);
  if (orphanPoLineIds.length > 0) {
    console.log(`  Orphans: ${orphanPoLineIds.length.toLocaleString()} unique po_line_ids not found`);
    console.log(`  Sample orphan po_line_ids: ${orphanPoLineIds.slice(0, 5).join(', ')}`);
    
    // Calculate orphan rows (not just unique po_line_ids)
    const orphanRowCount = rows.filter(r => orphanPoLineIds.includes(r.po_line_id)).length;
    console.log(`  Total orphan rows skipped: ${orphanRowCount.toLocaleString()}`);
  }
  
  // Step 5: Check circuit breaker
  console.log('\n[5/6] Checking circuit breaker...');
  
  // Count existing records
  const [{ count: existingCount }] = await db
    .select({ count: sql<number>`count(*)` })
    .from(poTransactions);
  
  const existingTotal = Number(existingCount);
  const newTotal = resolved.length;
  
  console.log(`  Current records: ${existingTotal.toLocaleString()}`);
  console.log(`  Records to import: ${newTotal.toLocaleString()}`);
  
  // Simple circuit breaker: if import size is much smaller than existing, warn
  // Transactions are historical facts - we do upserts, not deletes
  // So we just check if import file seems suspiciously small
  if (existingTotal > 0) {
    const changeRatio = newTotal / existingTotal;
    if (changeRatio < 0.5 && !FORCE_MODE) {
      console.error(`\n  CIRCUIT BREAKER TRIGGERED!`);
      console.error(`  Import file has ${(changeRatio * 100).toFixed(0)}% of current records`);
      console.error('  This may indicate a truncated or corrupted file.');
      console.error('  Use --force to override if this is intentional.');
      process.exit(1);
    }
  }
  
  console.log('  Circuit breaker check passed');
  
  if (DRY_RUN) {
    console.log('\n[6/6] Dry run - skipping database changes');
    console.log('\n' + '='.repeat(60));
    console.log('DRY RUN COMPLETE - No changes made');
    console.log('='.repeat(60));
    process.exit(0);
  }
  
  // Step 6: Execute import
  console.log('\n[6/6] Importing...');
  
  let totalProcessed = 0;
  const startTime = Date.now();
  
  // Process in batches
  for (let i = 0; i < resolved.length; i += BATCH_SIZE) {
    const batch = resolved.slice(i, i + BATCH_SIZE);
    const processed = await upsertBatch(batch);
    totalProcessed += processed;
    
    // Progress update every batch
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    const rate = Math.round(totalProcessed / (Date.now() - startTime) * 1000);
    console.log(`  Processed ${totalProcessed.toLocaleString()} / ${resolved.length.toLocaleString()} (${elapsed}s, ${rate}/s)`);
  }
  console.log(`  Upserted ${totalProcessed.toLocaleString()} records`);
  
  // Note: We intentionally do NOT delete transactions that aren't in the import.
  // Transactions are historical facts - if they're not in the new file, they
  // remain in the database. This is safer than cascading deletes.
  
  // Final stats
  const [{ count: finalCount }] = await db
    .select({ count: sql<number>`count(*)` })
    .from(poTransactions);
  
  // Get breakdown by type
  const typeCounts = await db
    .select({
      type: poTransactions.transactionType,
      count: sql<number>`count(*)`
    })
    .from(poTransactions)
    .groupBy(poTransactions.transactionType);
  
  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
  
  console.log('\n' + '='.repeat(60));
  console.log('Import Complete');
  console.log('='.repeat(60));
  console.log(`  Total records: ${Number(finalCount).toLocaleString()}`);
  for (const tc of typeCounts) {
    console.log(`    ${tc.type}: ${Number(tc.count).toLocaleString()}`);
  }
  console.log(`  Time: ${elapsed}s`);
  console.log(`  Rate: ${Math.round(totalProcessed / Number(elapsed))}/s`);
  
  if (orphanPoLineIds.length > 0) {
    console.log(`\n  Note: ${orphanPoLineIds.length.toLocaleString()} orphan po_line_ids were skipped`);
  }
  
  process.exit(0);
}

// Run
main().catch((error) => {
  console.error('Import failed:', error);
  process.exit(1);
});
