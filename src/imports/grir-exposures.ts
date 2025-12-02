#!/usr/bin/env npx tsx
/**
 * GRIR Exposures Import Script
 * 
 * Imports grir_exposures.csv into the database with:
 * - FK lookup (po_line_id → po_line_item_id UUID)
 * - Upsert on (po_line_item_id, snapshot_date) composite key
 * - Orphan handling (skip exposures with missing parent PO)
 * - Stats logging (total exposure value, time bucket breakdown)
 * 
 * GRIR = Goods Receipt/Invoice Receipt exposure (when IR > GR)
 * This tracks financial exposure where invoices exceed goods received.
 * 
 * Usage:
 *   npx tsx src/imports/grir-exposures.ts
 *   npx tsx src/imports/grir-exposures.ts --force    # Skip size validation
 *   npx tsx src/imports/grir-exposures.ts --dry-run  # Preview without changes
 */

import 'dotenv/config';
import { createReadStream } from 'fs';
import { parse } from 'csv-parse';
import { db } from '../client';
import { grirExposures, poLineItems } from '../schema';
import { eq, sql } from 'drizzle-orm';

// Configuration
const CSV_PATH = './data/import-ready/grir_exposures.csv';
const BATCH_SIZE = 100; // Small batches for small dataset

// Valid time bucket values from GRIR contract
const VALID_TIME_BUCKETS = new Set([
  '<1 month',
  '1-3 months',
  '3-6 months',
  '6-12 months',
  '>1 year',
]);

// Parse CLI args
const args = process.argv.slice(2);
const FORCE_MODE = args.includes('--force');
const DRY_RUN = args.includes('--dry-run');

interface CsvRow {
  po_line_id: string;
  grir_qty: string;
  grir_value: string;
  first_exposure_date: string;
  days_open: string;
  time_bucket: string;
  snapshot_date: string;
}

type GRIRExposureInsert = typeof grirExposures.$inferInsert;

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
 * Parse date string (extract date part if needed)
 */
function parseDate(val: string): string | null {
  if (val === '' || val === null || val === undefined) return null;
  // Handle "2022-12-01 00:00:00.000" format - extract just the date
  return val.split(' ')[0];
}

/**
 * Parse numeric string to proper format
 */
function parseNumeric(val: string): string {
  if (val === '' || val === null || val === undefined) return '0';
  return val;
}

/**
 * Parse integer string
 */
function parseInt_(val: string): number {
  if (val === '' || val === null || val === undefined) return 0;
  return parseInt(val, 10);
}

/**
 * Resolve parent IDs and separate orphans
 */
function resolveParentIds(
  rows: CsvRow[], 
  lookup: Map<string, string>
): { resolved: GRIRExposureInsert[], orphanPoLineIds: string[] } {
  const resolved: GRIRExposureInsert[] = [];
  const orphanSet = new Set<string>();
  
  for (const row of rows) {
    const parentId = lookup.get(row.po_line_id);
    
    if (!parentId) {
      orphanSet.add(row.po_line_id);
      continue;
    }
    
    resolved.push({
      poLineItemId: parentId,
      grirQty: parseNumeric(row.grir_qty),
      grirValue: parseNumeric(row.grir_value),
      firstExposureDate: parseDate(row.first_exposure_date),
      daysOpen: parseInt_(row.days_open),
      timeBucket: row.time_bucket,
      snapshotDate: parseDate(row.snapshot_date) || new Date().toISOString().split('T')[0],
      updatedAt: new Date(),
    });
  }
  
  return { 
    resolved, 
    orphanPoLineIds: Array.from(orphanSet) 
  };
}

/**
 * Upsert records in batches using composite key
 */
async function upsertBatch(records: GRIRExposureInsert[]): Promise<number> {
  if (records.length === 0) return 0;
  
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
  
  return records.length;
}

/**
 * Main import function
 */
async function main() {
  console.log('='.repeat(60));
  console.log('GRIR Exposures Import');
  console.log('='.repeat(60));
  
  if (DRY_RUN) {
    console.log('*** DRY RUN MODE - No changes will be made ***\n');
  }
  if (FORCE_MODE) {
    console.log('*** FORCE MODE - Size validation disabled ***\n');
  }

  // Step 1: Load CSV
  console.log('\n[1/6] Loading CSV...');
  const rows = await loadCsv(CSV_PATH);
  console.log(`  Loaded ${rows.length.toLocaleString()} rows from CSV`);
  
  // Step 2: Basic validation
  console.log('\n[2/6] Validating...');
  
  // Check for required fields
  const invalidRows = rows.filter(r => 
    !r.po_line_id || 
    !r.snapshot_date || 
    r.grir_qty === '' ||
    r.grir_value === ''
  );
  if (invalidRows.length > 0) {
    console.error(`  ERROR: ${invalidRows.length} rows missing required fields`);
    process.exit(1);
  }
  
  // Check time bucket values
  const invalidTimeBuckets = rows.filter(r => !VALID_TIME_BUCKETS.has(r.time_bucket));
  if (invalidTimeBuckets.length > 0) {
    console.error(`  ERROR: ${invalidTimeBuckets.length} rows with invalid time_bucket`);
    console.error(`  Invalid values: ${[...new Set(invalidTimeBuckets.map(r => r.time_bucket))].join(', ')}`);
    process.exit(1);
  }
  
  // Warn if file seems too small (but continue unless --force not used)
  if (rows.length === 0) {
    console.error(`  ERROR: Empty CSV file!`);
    process.exit(1);
  }
  
  console.log('  Validation passed');
  
  // Step 3: Build FK lookup
  console.log('\n[3/6] Building FK lookup...');
  const lookup = await buildPoLineIdLookup();
  
  // Step 4: Resolve parent IDs
  console.log('\n[4/6] Resolving parent IDs...');
  const { resolved, orphanPoLineIds } = resolveParentIds(rows, lookup);
  
  console.log(`  Resolved: ${resolved.length.toLocaleString()} exposures`);
  if (orphanPoLineIds.length > 0) {
    console.warn(`  WARNING: ${orphanPoLineIds.length} orphan po_line_ids not found`);
    console.warn(`  Orphan IDs: ${orphanPoLineIds.join(', ')}`);
  }
  
  // Step 5: Check existing records
  console.log('\n[5/6] Checking existing records...');
  
  const [{ count: existingCount }] = await db
    .select({ count: sql<number>`count(*)` })
    .from(grirExposures);
  
  console.log(`  Current records: ${Number(existingCount).toLocaleString()}`);
  console.log(`  Records to import: ${resolved.length.toLocaleString()}`);
  
  // Compute stats from CSV before import
  const totalValue = rows.reduce((sum, r) => sum + parseFloat(r.grir_value || '0'), 0);
  const totalQty = rows.reduce((sum, r) => sum + parseFloat(r.grir_qty || '0'), 0);
  
  // Time bucket breakdown
  const bucketCounts: Record<string, { count: number; value: number }> = {};
  for (const r of rows) {
    if (!bucketCounts[r.time_bucket]) {
      bucketCounts[r.time_bucket] = { count: 0, value: 0 };
    }
    bucketCounts[r.time_bucket].count++;
    bucketCounts[r.time_bucket].value += parseFloat(r.grir_value || '0');
  }
  
  console.log(`  Total GRIR Value: $${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2 })}`);
  console.log(`  Total GRIR Qty: ${totalQty.toLocaleString()}`);
  
  if (DRY_RUN) {
    console.log('\n[6/6] Dry run - skipping database changes');
    console.log('\nTime Bucket Breakdown:');
    for (const [bucket, stats] of Object.entries(bucketCounts).sort()) {
      console.log(`  ${bucket.padEnd(15)}: ${stats.count.toString().padStart(4)} records, $${stats.value.toLocaleString('en-US', { minimumFractionDigits: 2 })}`);
    }
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
    console.log(`  Processed ${totalProcessed.toLocaleString()} / ${resolved.length.toLocaleString()} (${elapsed}s)`);
  }
  console.log(`  Upserted ${totalProcessed.toLocaleString()} records`);
  
  // Final stats from database
  const [{ count: finalCount }] = await db
    .select({ count: sql<number>`count(*)` })
    .from(grirExposures);
  
  // Get time bucket breakdown from database
  const dbBucketCounts = await db
    .select({
      bucket: grirExposures.timeBucket,
      count: sql<number>`count(*)`,
      totalValue: sql<number>`sum(${grirExposures.grirValue}::numeric)`
    })
    .from(grirExposures)
    .groupBy(grirExposures.timeBucket);
  
  // Get total exposure value from database
  const [{ totalDbValue }] = await db
    .select({
      totalDbValue: sql<number>`sum(${grirExposures.grirValue}::numeric)`
    })
    .from(grirExposures);
  
  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
  
  console.log('\n' + '='.repeat(60));
  console.log('Import Complete');
  console.log('='.repeat(60));
  console.log(`  Total records: ${Number(finalCount).toLocaleString()}`);
  console.log(`  Total exposure: $${Number(totalDbValue).toLocaleString('en-US', { minimumFractionDigits: 2 })}`);
  console.log(`  Time: ${elapsed}s`);
  
  console.log('\nTime Bucket Breakdown:');
  for (const tc of dbBucketCounts.sort((a, b) => (a.bucket ?? '').localeCompare(b.bucket ?? ''))) {
    console.log(`  ${(tc.bucket ?? '').padEnd(15)}: ${Number(tc.count).toString().padStart(4)} records, $${Number(tc.totalValue).toLocaleString('en-US', { minimumFractionDigits: 2 })}`);
  }
  
  if (orphanPoLineIds.length > 0) {
    console.log(`\n  Note: ${orphanPoLineIds.length} orphan po_line_ids were skipped`);
  }
  
  process.exit(0);
}

// Run
main().catch((error) => {
  console.error('Import failed:', error);
  process.exit(1);
});
