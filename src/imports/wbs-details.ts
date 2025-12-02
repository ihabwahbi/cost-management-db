#!/usr/bin/env npx tsx
/**
 * WBS Details Import Script
 * 
 * Imports wbs_details.csv into the database with:
 * - VARCHAR primary key (wbs_number - not UUID)
 * - PostgreSQL text[] array for sub_business_lines
 * - Upsert on wbs_number
 * - Stats logging (source distribution, location breakdown)
 * 
 * WBS = Work Breakdown Structure - project hierarchy context for POs
 * 
 * Key differences from other imports:
 * - No FK lookup needed (this is a root/parent table)
 * - VARCHAR PK instead of UUID
 * - Array column handling (PostgreSQL literal format)
 * 
 * Usage:
 *   npx tsx src/imports/wbs-details.ts
 *   npx tsx src/imports/wbs-details.ts --force    # Skip size validation
 *   npx tsx src/imports/wbs-details.ts --dry-run  # Preview without changes
 */

import 'dotenv/config';
import { createReadStream } from 'fs';
import { parse } from 'csv-parse';
import { db } from '../client';
import { wbsDetails } from '../schema';
import { sql } from 'drizzle-orm';

// Configuration
const CSV_PATH = './data/import-ready/wbs_details.csv';
const BATCH_SIZE = 1000;

// Parse CLI args
const args = process.argv.slice(2);
const FORCE_MODE = args.includes('--force');
const DRY_RUN = args.includes('--dry-run');

// Valid WBS source values
const VALID_WBS_SOURCES = new Set([
  'Project',
  'Operation',
  'Operation Activity',
]);

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
  sub_business_lines: string;  // '{WLPS,SLKN}' PostgreSQL array format
}

type WbsDetailsInsert = typeof wbsDetails.$inferInsert;

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

/**
 * Convert CSV row to database record format
 */
function transformRow(row: CsvRow): WbsDetailsInsert {
  // Helper to parse optional string fields (empty string -> null)
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

/**
 * Upsert records in batches using VARCHAR primary key
 */
async function upsertBatch(records: WbsDetailsInsert[]): Promise<number> {
  if (records.length === 0) return 0;
  
  await db
    .insert(wbsDetails)
    .values(records)
    .onConflictDoUpdate({
      target: wbsDetails.wbsNumber,  // VARCHAR PK (not UUID!)
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

/**
 * Main import function
 */
async function main() {
  console.log('='.repeat(60));
  console.log('WBS Details Import');
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
    !r.wbs_number || 
    !r.wbs_source ||
    r.wbs_number.trim() === ''
  );
  if (invalidRows.length > 0) {
    console.error(`  ERROR: ${invalidRows.length} rows missing required fields`);
    process.exit(1);
  }
  
  // Check WBS source values
  const invalidSources = rows.filter(r => !VALID_WBS_SOURCES.has(r.wbs_source));
  if (invalidSources.length > 0) {
    console.error(`  ERROR: ${invalidSources.length} rows with invalid wbs_source`);
    console.error(`  Invalid values: ${[...new Set(invalidSources.map(r => r.wbs_source))].join(', ')}`);
    process.exit(1);
  }
  
  // Check for duplicates (wbs_number should be unique)
  const wbsNumbers = rows.map(r => r.wbs_number);
  const duplicates = wbsNumbers.filter((item, index) => wbsNumbers.indexOf(item) !== index);
  if (duplicates.length > 0) {
    console.error(`  ERROR: ${duplicates.length} duplicate wbs_numbers found`);
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
  
  // Step 3: Transform data
  console.log('\n[3/5] Transforming data...');
  const records = rows.map(transformRow);
  console.log(`  Transformed ${records.length.toLocaleString()} records`);
  
  // Compute stats from CSV
  const sourceCounts: Record<string, number> = {};
  const locationCounts: Record<string, number> = {};
  const sblCounts: Record<string, number> = {};
  
  for (const r of rows) {
    // Source distribution
    sourceCounts[r.wbs_source] = (sourceCounts[r.wbs_source] || 0) + 1;
    
    // Location distribution
    const loc = r.location || '(null)';
    locationCounts[loc] = (locationCounts[loc] || 0) + 1;
    
    // Sub business line distribution (flatten arrays)
    const sbls = parseArrayLiteral(r.sub_business_lines) || [];
    for (const sbl of sbls) {
      sblCounts[sbl] = (sblCounts[sbl] || 0) + 1;
    }
  }
  
  // Step 4: Check existing records
  console.log('\n[4/5] Checking existing records...');
  
  const [{ count: existingCount }] = await db
    .select({ count: sql<number>`count(*)` })
    .from(wbsDetails);
  
  console.log(`  Current records: ${Number(existingCount).toLocaleString()}`);
  console.log(`  Records to import: ${records.length.toLocaleString()}`);
  
  // Display source distribution
  console.log('\nSource Distribution:');
  for (const [source, count] of Object.entries(sourceCounts).sort((a, b) => b[1] - a[1])) {
    const pct = ((count / rows.length) * 100).toFixed(1);
    console.log(`  ${source.padEnd(20)}: ${count.toString().padStart(5)} (${pct}%)`);
  }
  
  if (DRY_RUN) {
    console.log('\n[5/5] Dry run - skipping database changes');
    
    // Show more stats in dry run mode
    console.log('\nLocation Distribution:');
    for (const [loc, count] of Object.entries(locationCounts).sort((a, b) => b[1] - a[1])) {
      console.log(`  ${loc.padEnd(15)}: ${count.toString().padStart(5)}`);
    }
    
    console.log('\nTop Sub Business Lines:');
    const sortedSbls = Object.entries(sblCounts).sort((a, b) => b[1] - a[1]).slice(0, 10);
    for (const [sbl, count] of sortedSbls) {
      console.log(`  ${sbl.padEnd(10)}: ${count.toString().padStart(5)}`);
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
    .from(wbsDetails);
  
  // Get source distribution from database
  const dbSourceCounts = await db
    .select({
      source: wbsDetails.wbsSource,
      count: sql<number>`count(*)`
    })
    .from(wbsDetails)
    .groupBy(wbsDetails.wbsSource);
  
  // Get location distribution from database
  const dbLocationCounts = await db
    .select({
      location: wbsDetails.location,
      count: sql<number>`count(*)`
    })
    .from(wbsDetails)
    .groupBy(wbsDetails.location);
  
  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
  
  console.log('\n' + '='.repeat(60));
  console.log('Import Complete');
  console.log('='.repeat(60));
  console.log(`  Total records: ${Number(finalCount).toLocaleString()}`);
  console.log(`  Time: ${elapsed}s`);
  
  console.log('\nSource Distribution (from DB):');
  for (const tc of dbSourceCounts.sort((a, b) => Number(b.count) - Number(a.count))) {
    console.log(`  ${(tc.source ?? '').padEnd(20)}: ${Number(tc.count).toString().padStart(5)}`);
  }
  
  console.log('\nLocation Distribution (from DB):');
  for (const tc of dbLocationCounts.sort((a, b) => Number(b.count) - Number(a.count))) {
    console.log(`  ${(tc.location ?? '(null)').padEnd(15)}: ${Number(tc.count).toString().padStart(5)}`);
  }
  
  process.exit(0);
}

// Run
main().catch((error) => {
  console.error('Import failed:', error);
  process.exit(1);
});
