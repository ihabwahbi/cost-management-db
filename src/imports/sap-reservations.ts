#!/usr/bin/env npx tsx
/**
 * SAP Reservations Import Script
 * 
 * Imports sap_reservations.csv into the database with:
 * - All original values preserved (no FK validation/nullification)
 * - Upsert on reservation_line_id
 * - Stats logging (status distribution, FK linkage breakdown)
 * - Orphan reporting for investigation (after import)
 * 
 * SAP Reservations track material requirements for operations.
 * 
 * NOTE: FK constraints removed from schema to allow storing orphan WBS/PO values
 * for investigation. Use queries to find orphans after import.
 * 
 * Usage:
 *   npx tsx src/imports/sap-reservations.ts
 *   npx tsx src/imports/sap-reservations.ts --force    # Skip size validation
 *   npx tsx src/imports/sap-reservations.ts --dry-run  # Preview without changes
 */

import 'dotenv/config';
import { createReadStream } from 'fs';
import { parse } from 'csv-parse';
import { db } from '../client';
import { sapReservations } from '../schema';
import { sql } from 'drizzle-orm';

// Configuration
const CSV_PATH = './data/import-ready/sap_reservations.csv';
const BATCH_SIZE = 500;

// Parse CLI args
const args = process.argv.slice(2);
const FORCE_MODE = args.includes('--force');
const DRY_RUN = args.includes('--dry-run');

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
 * Helper: Parse optional string fields (empty string -> null)
 */
function str(val: string): string | null {
  return val === '' ? null : val;
}

/**
 * Helper: Parse date string (extract date part if needed)
 */
function parseDate(val: string): string | null {
  if (val === '' || val === null || val === undefined) return null;
  // Handle "2022-12-01 00:00:00.000" format - extract just the date
  return val.split(' ')[0];
}

/**
 * Helper: Parse numeric string to proper format
 */
function parseNumeric(val: string): string | null {
  if (val === '' || val === null || val === undefined) return null;
  return val;
}

/**
 * Helper: Parse integer string (nullable)
 */
function parseInt_(val: string): number | null {
  if (val === '' || val === null || val === undefined) return null;
  const parsed = parseInt(val, 10);
  return isNaN(parsed) ? null : parsed;
}

/**
 * Transform CSV row to database record.
 * All original values preserved - no FK validation.
 */
function transformRow(row: CsvRow): SapReservationInsert {
  return {
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
    wbsNumber: str(row.wbs_number),           // Original value preserved
    requesterAlias: str(row.requester_alias),
    plantCode: str(row.plant_code),
    poNumber: str(row.po_number),
    poLineNumber: parseInt_(row.po_line_number),
    poLineItemId: str(row.po_line_item_id),   // Original value preserved
    assetCode: str(row.asset_code),
    assetSerialNumber: str(row.asset_serial_number),
    updatedAt: new Date(),
  };
}

/**
 * Upsert records in batches using reservation_line_id as unique key
 */
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

/**
 * Main import function
 */
async function main() {
  console.log('='.repeat(60));
  console.log('SAP Reservations Import');
  console.log('='.repeat(60));
  
  if (DRY_RUN) {
    console.log('*** DRY RUN MODE - No changes will be made ***\n');
  }
  if (FORCE_MODE) {
    console.log('*** FORCE MODE - Size validation disabled ***\n');
  }

  // Step 1: Load CSV
  console.log('\n[1/5] Loading CSV...');
  const rows = await loadCsv(CSV_PATH);
  console.log(`  Loaded ${rows.length.toLocaleString()} rows from CSV`);
  
  // Step 2: Basic validation
  console.log('\n[2/5] Validating...');
  
  // Check for required fields
  const invalidRows = rows.filter(r => 
    !r.reservation_line_id || 
    !r.reservation_number ||
    !r.reservation_line_number ||
    r.reservation_line_id.trim() === ''
  );
  if (invalidRows.length > 0) {
    console.error(`  ERROR: ${invalidRows.length} rows missing required fields`);
    process.exit(1);
  }
  
  // Check for duplicates (reservation_line_id should be unique)
  const lineIds = rows.map(r => r.reservation_line_id);
  const duplicates = lineIds.filter((item, index) => lineIds.indexOf(item) !== index);
  if (duplicates.length > 0) {
    console.error(`  ERROR: ${duplicates.length} duplicate reservation_line_ids found`);
    console.error(`  Duplicates: ${[...new Set(duplicates)].slice(0, 10).join(', ')}${duplicates.length > 10 ? '...' : ''}`);
    process.exit(1);
  }
  
  // Warn if file seems too small
  if (rows.length < 100 && !FORCE_MODE) {
    console.error(`  ERROR: Only ${rows.length} rows in file - suspiciously low!`);
    console.error('  Aborting to prevent data loss. Use --force to override.');
    process.exit(1);
  }
  
  console.log('  Validation passed');
  
  // Step 3: Transform data (no FK validation - keep original values)
  console.log('\n[3/5] Transforming data...');
  const records = rows.map(transformRow);
  console.log(`  Transformed ${records.length.toLocaleString()} records`);
  
  // Compute stats from CSV
  const statusCounts: Record<string, number> = {};
  const sourceCounts: Record<string, number> = {};
  let withWbs = 0, withPo = 0;
  let totalValue = 0;
  
  for (const r of rows) {
    // Status distribution
    statusCounts[r.reservation_status] = (statusCounts[r.reservation_status] || 0) + 1;
    
    // Source distribution
    sourceCounts[r.reservation_source] = (sourceCounts[r.reservation_source] || 0) + 1;
    
    // FK linkage
    if (r.wbs_number && r.wbs_number.trim() !== '') withWbs++;
    if (r.po_line_item_id && r.po_line_item_id.trim() !== '') withPo++;
    
    // Total value
    totalValue += parseFloat(r.open_reservation_value || '0');
  }
  
  // Step 4: Check existing records
  console.log('\n[4/5] Checking existing records...');
  
  const [{ count: existingCount }] = await db
    .select({ count: sql<number>`count(*)` })
    .from(sapReservations);
  
  console.log(`  Current records: ${Number(existingCount).toLocaleString()}`);
  console.log(`  Records to import: ${records.length.toLocaleString()}`);
  
  console.log('\nStatus Distribution:');
  for (const [status, count] of Object.entries(statusCounts).sort((a, b) => b[1] - a[1])) {
    const pct = ((count / rows.length) * 100).toFixed(1);
    console.log(`  ${status.substring(0, 50).padEnd(52)}: ${count.toString().padStart(5)} (${pct}%)`);
  }
  
  console.log('\nFK Linkage (from CSV):');
  console.log(`  With WBS:     ${withWbs.toString().padStart(5)} (${((withWbs / rows.length) * 100).toFixed(1)}%)`);
  console.log(`  With PO:      ${withPo.toString().padStart(5)} (${((withPo / rows.length) * 100).toFixed(1)}%)`);
  console.log(`  Total Value:  $${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2 })}`);
  
  if (DRY_RUN) {
    console.log('\n[5/5] Dry run - skipping database changes');
    
    console.log('\nSource Distribution:');
    for (const [source, count] of Object.entries(sourceCounts).sort((a, b) => b[1] - a[1])) {
      console.log(`  ${source.padEnd(30)}: ${count.toString().padStart(5)}`);
    }
    
    console.log('\n' + '='.repeat(60));
    console.log('DRY RUN COMPLETE - No changes made');
    console.log('='.repeat(60));
    process.exit(0);
  }
  
  // Step 5: Execute import
  console.log('\n[5/5] Importing...');
  
  let totalProcessed = 0;
  const startTime = Date.now();
  
  // Process in batches
  for (let i = 0; i < records.length; i += BATCH_SIZE) {
    const batch = records.slice(i, i + BATCH_SIZE);
    const processed = await upsertBatch(batch);
    totalProcessed += processed;
    
    // Progress update every batch
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`  Processed ${totalProcessed.toLocaleString()} / ${records.length.toLocaleString()} (${elapsed}s)`);
  }
  console.log(`  Upserted ${totalProcessed.toLocaleString()} records`);
  
  // Final stats from database
  const [{ count: finalCount }] = await db
    .select({ count: sql<number>`count(*)` })
    .from(sapReservations);
  
  // Get FK linkage from database
  const [fkStats] = await db
    .select({
      withWbs: sql<number>`count(*) filter (where wbs_number is not null)`,
      withPo: sql<number>`count(*) filter (where po_line_item_id is not null)`,
      totalValue: sql<number>`sum(open_reservation_value::numeric)`
    })
    .from(sapReservations);
  
  // Get status distribution from database
  const dbStatusCounts = await db
    .select({
      status: sapReservations.reservationStatus,
      count: sql<number>`count(*)`
    })
    .from(sapReservations)
    .groupBy(sapReservations.reservationStatus);
  
  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
  
  console.log('\n' + '='.repeat(60));
  console.log('Import Complete');
  console.log('='.repeat(60));
  console.log(`  Total records: ${Number(finalCount).toLocaleString()}`);
  console.log(`  Time: ${elapsed}s`);
  
  console.log('\nFK Linkage (from DB):');
  console.log(`  With WBS:     ${Number(fkStats.withWbs).toString().padStart(5)}`);
  console.log(`  With PO:      ${Number(fkStats.withPo).toString().padStart(5)}`);
  console.log(`  Total Value:  $${Number(fkStats.totalValue).toLocaleString('en-US', { minimumFractionDigits: 2 })}`);
  
  console.log('\nStatus Distribution (from DB):');
  for (const sc of dbStatusCounts.sort((a, b) => Number(b.count) - Number(a.count))) {
    console.log(`  ${(sc.status ?? '').substring(0, 50).padEnd(52)}: ${Number(sc.count).toString().padStart(5)}`);
  }
  
  // Check for orphans (for investigation)
  console.log('\n--- Orphan Analysis (for investigation) ---');
  
  // Find orphan WBS
  const orphanWbs = await db.execute<{ wbs_number: string }>(sql`
    SELECT DISTINCT r.wbs_number 
    FROM dev_v3.sap_reservations r
    LEFT JOIN dev_v3.wbs_details w ON r.wbs_number = w.wbs_number
    WHERE r.wbs_number IS NOT NULL AND w.wbs_number IS NULL
  `);
  
  // Find orphan PO Line IDs
  const orphanPo = await db.execute<{ po_line_item_id: string }>(sql`
    SELECT DISTINCT r.po_line_item_id 
    FROM dev_v3.sap_reservations r
    LEFT JOIN dev_v3.po_line_items p ON r.po_line_item_id = p.po_line_id
    WHERE r.po_line_item_id IS NOT NULL AND p.po_line_id IS NULL
  `);
  
  const orphanWbsList = [...orphanWbs] as { wbs_number: string }[];
  const orphanPoList = [...orphanPo] as { po_line_item_id: string }[];
  
  if (orphanWbsList.length > 0) {
    console.log(`\nOrphan WBS values (${orphanWbsList.length} not in wbs_details):`);
    for (const row of orphanWbsList) {
      console.log(`  - ${row.wbs_number}`);
    }
  } else {
    console.log('\nNo orphan WBS values found.');
  }
  
  if (orphanPoList.length > 0) {
    console.log(`\nOrphan PO Line IDs (${orphanPoList.length} not in po_line_items):`);
    for (const row of orphanPoList) {
      console.log(`  - ${row.po_line_item_id}`);
    }
  } else {
    console.log('No orphan PO Line IDs found.');
  }
  
  console.log('\nTo investigate orphans, use these queries:');
  console.log('  -- WBS orphans:');
  console.log('  SELECT * FROM dev_v3.sap_reservations r');
  console.log('  LEFT JOIN dev_v3.wbs_details w ON r.wbs_number = w.wbs_number');
  console.log('  WHERE r.wbs_number IS NOT NULL AND w.wbs_number IS NULL;');
  console.log('');
  console.log('  -- PO orphans:');
  console.log('  SELECT * FROM dev_v3.sap_reservations r');
  console.log('  LEFT JOIN dev_v3.po_line_items p ON r.po_line_item_id = p.po_line_id');
  console.log('  WHERE r.po_line_item_id IS NOT NULL AND p.po_line_id IS NULL;');
  
  process.exit(0);
}

// Run
main().catch((error) => {
  console.error('Import failed:', error);
  process.exit(1);
});
