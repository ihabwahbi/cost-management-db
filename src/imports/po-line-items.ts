#!/usr/bin/env npx tsx
/**
 * PO Line Items Import Script
 * 
 * Imports po_line_items.csv into the database with:
 * - Upsert on po_line_id (insert new, update existing)
 * - Circuit breaker (abort if >5% would be deactivated)
 * - Soft delete (is_active=false for records not in import)
 * - PR Pre-Mapping matching (creates pending confirmations in inbox)
 * 
 * After import, automatically matches POs against active PR pre-mappings
 * and creates po_mappings with requiresConfirmation=true for user verification.
 * 
 * Usage:
 *   npx tsx src/imports/po-line-items.ts
 *   npx tsx src/imports/po-line-items.ts --force  # Skip circuit breaker
 *   npx tsx src/imports/po-line-items.ts --dry-run  # Preview without changes
 */

import 'dotenv/config';
import { createReadStream } from 'fs';
import { parse } from 'csv-parse';
import { db } from '../client';
import { poLineItems } from '../schema';
import { eq, notInArray, and, sql } from 'drizzle-orm';
import { matchPRPreMappings } from '../matching/match-pr-pre-mappings';

// Configuration
const CSV_PATH = './data/import-ready/po_line_items.csv';
const CIRCUIT_BREAKER_THRESHOLD = 0.05; // 5% - abort if more than this % would be deactivated
const BATCH_SIZE = 1000; // Insert in batches for performance

// Parse CLI args
const args = process.argv.slice(2);
const FORCE_MODE = args.includes('--force');
const DRY_RUN = args.includes('--dry-run');

interface CsvRow {
  po_line_id: string;
  po_number: string;
  po_creation_date: string;
  plant_code: string;
  location: string;
  sub_business_line: string;
  pr_number: string;
  pr_line: string;
  requester: string;
  vendor_id: string;
  vendor_name: string;
  vendor_category: string;
  ultimate_vendor_name: string;
  line_item_number: string;
  part_number: string;
  description: string;
  ordered_qty: string;
  order_unit: string;
  po_value_usd: string;
  account_assignment_category: string;
  nis_line: string;
  wbs_number: string;
  expected_delivery_date: string;
  po_approval_status: string;
  po_receipt_status: string;
  po_gts_status: string;
  open_po_qty: string;
  open_po_value: string;
  cost_impact_value: string;
  cost_impact_pct: string;
  fmt_po: string;
  wbs_validated: string;
  is_capex: string;
}

type PoLineItemInsert = typeof poLineItems.$inferInsert;

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
 * Convert CSV row to database record format
 */
function transformRow(row: CsvRow): PoLineItemInsert {
  // Helper to parse optional string fields (empty string → null)
  const str = (val: string): string | null => val === '' ? null : val;
  
  // Helper to parse optional integer fields
  const int = (val: string): number | null => {
    if (val === '' || val === null || val === undefined) return null;
    const parsed = parseInt(val, 10);
    return isNaN(parsed) ? null : parsed;
  };
  
  // Helper to parse required numeric fields
  const num = (val: string): string => {
    if (val === '' || val === null || val === undefined) return '0';
    return val;
  };
  
  // Helper to parse boolean fields
  const bool = (val: string): boolean => {
    return val.toLowerCase() === 'true';
  };
  
  // Helper to parse date fields (extract date part from datetime string)
  const date = (val: string): string | null => {
    if (val === '' || val === null || val === undefined) return null;
    // Handle "2022-12-01 00:00:00.000" format - extract just the date
    return val.split(' ')[0];
  };

  return {
    poLineId: row.po_line_id,
    poNumber: row.po_number,
    poCreationDate: date(row.po_creation_date),
    plantCode: str(row.plant_code),
    location: str(row.location),
    subBusinessLine: str(row.sub_business_line),
    prNumber: str(row.pr_number),
    prLine: int(row.pr_line),
    requester: str(row.requester),
    vendorId: str(row.vendor_id),
    vendorName: str(row.vendor_name),
    vendorCategory: str(row.vendor_category),
    ultimateVendorName: str(row.ultimate_vendor_name),
    lineItemNumber: parseInt(row.line_item_number, 10),
    partNumber: str(row.part_number),
    description: str(row.description),
    orderedQty: num(row.ordered_qty),
    orderUnit: str(row.order_unit),
    poValueUsd: num(row.po_value_usd),
    accountAssignmentCategory: str(row.account_assignment_category),
    nisLine: str(row.nis_line),
    wbsNumber: str(row.wbs_number),
    wbsValidated: bool(row.wbs_validated),
    isCapex: bool(row.is_capex),
    expectedDeliveryDate: date(row.expected_delivery_date),
    poApprovalStatus: str(row.po_approval_status),
    poReceiptStatus: str(row.po_receipt_status),
    poGtsStatus: str(row.po_gts_status),
    fmtPo: bool(row.fmt_po),
    openPoQty: str(row.open_po_qty),
    openPoValue: str(row.open_po_value),
    costImpactValue: str(row.cost_impact_value),
    costImpactPct: str(row.cost_impact_pct),
    isActive: true,  // All imported records are active
    updatedAt: new Date(),
  };
}

/**
 * Upsert records in batches using bulk insert
 */
async function upsertBatch(records: PoLineItemInsert[]): Promise<number> {
  if (records.length === 0) return 0;
  
  // Bulk upsert - Drizzle handles this efficiently
  await db
    .insert(poLineItems)
    .values(records)
    .onConflictDoUpdate({
      target: poLineItems.poLineId,
      set: {
        poNumber: sql`excluded.po_number`,
        poCreationDate: sql`excluded.po_creation_date`,
        plantCode: sql`excluded.plant_code`,
        location: sql`excluded.location`,
        subBusinessLine: sql`excluded.sub_business_line`,
        prNumber: sql`excluded.pr_number`,
        prLine: sql`excluded.pr_line`,
        requester: sql`excluded.requester`,
        vendorId: sql`excluded.vendor_id`,
        vendorName: sql`excluded.vendor_name`,
        vendorCategory: sql`excluded.vendor_category`,
        ultimateVendorName: sql`excluded.ultimate_vendor_name`,
        lineItemNumber: sql`excluded.line_item_number`,
        partNumber: sql`excluded.part_number`,
        description: sql`excluded.description`,
        orderedQty: sql`excluded.ordered_qty`,
        orderUnit: sql`excluded.order_unit`,
        poValueUsd: sql`excluded.po_value_usd`,
        accountAssignmentCategory: sql`excluded.account_assignment_category`,
        nisLine: sql`excluded.nis_line`,
        wbsNumber: sql`excluded.wbs_number`,
        wbsValidated: sql`excluded.wbs_validated`,
        isCapex: sql`excluded.is_capex`,
        expectedDeliveryDate: sql`excluded.expected_delivery_date`,
        poApprovalStatus: sql`excluded.po_approval_status`,
        poReceiptStatus: sql`excluded.po_receipt_status`,
        poGtsStatus: sql`excluded.po_gts_status`,
        fmtPo: sql`excluded.fmt_po`,
        openPoQty: sql`excluded.open_po_qty`,
        openPoValue: sql`excluded.open_po_value`,
        costImpactValue: sql`excluded.cost_impact_value`,
        costImpactPct: sql`excluded.cost_impact_pct`,
        isActive: sql`excluded.is_active`,
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
  console.log('PO Line Items Import');
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
  const invalidRows = rows.filter(r => !r.po_line_id || !r.po_number || !r.line_item_number);
  if (invalidRows.length > 0) {
    console.error(`  ERROR: ${invalidRows.length} rows missing required fields`);
    process.exit(1);
  }
  console.log('  Validation passed');
  
  // Step 3: Transform data
  console.log('\n[3/6] Transforming data...');
  const records = rows.map(transformRow);
  const poLineIds = records.map(r => r.poLineId);
  console.log(`  Transformed ${records.length.toLocaleString()} records`);
  
  // Step 4: Check circuit breaker
  console.log('\n[4/6] Checking circuit breaker...');
  
  // Get current active count
  const [{ count: activeCount }] = await db
    .select({ count: sql<number>`count(*)` })
    .from(poLineItems)
    .where(eq(poLineItems.isActive, true));
  
  // Count how many would be deactivated
  const [{ count: toDeactivateCount }] = await db
    .select({ count: sql<number>`count(*)` })
    .from(poLineItems)
    .where(
      and(
        eq(poLineItems.isActive, true),
        notInArray(poLineItems.poLineId, poLineIds)
      )
    );
  
  const deactivatePercent = activeCount > 0 ? toDeactivateCount / activeCount : 0;
  
  console.log(`  Current active records: ${Number(activeCount).toLocaleString()}`);
  console.log(`  Records to deactivate: ${Number(toDeactivateCount).toLocaleString()} (${(deactivatePercent * 100).toFixed(1)}%)`);
  
  if (deactivatePercent > CIRCUIT_BREAKER_THRESHOLD && !FORCE_MODE) {
    console.error(`\n  CIRCUIT BREAKER TRIGGERED!`);
    console.error(`  ${(deactivatePercent * 100).toFixed(1)}% exceeds ${CIRCUIT_BREAKER_THRESHOLD * 100}% threshold`);
    console.error('  This may indicate a corrupted or incomplete import file.');
    console.error('  Use --force to override if this is intentional.');
    process.exit(1);
  }
  
  if (DRY_RUN) {
    console.log('\n[5-6/6] Dry run - skipping database changes');
    console.log('\n' + '='.repeat(60));
    console.log('DRY RUN COMPLETE - No changes made');
    console.log('='.repeat(60));
    process.exit(0);
  }
  
  // Step 5: Execute import
  console.log('\n[5/6] Importing...');
  
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
  
  // Soft delete records not in import
  if (Number(toDeactivateCount) > 0) {
    console.log(`  Deactivating ${Number(toDeactivateCount).toLocaleString()} records...`);
    
    await db
      .update(poLineItems)
      .set({ 
        isActive: false, 
        updatedAt: new Date() 
      })
      .where(
        and(
          eq(poLineItems.isActive, true),
          notInArray(poLineItems.poLineId, poLineIds)
        )
      );
  }
  
  // Step 6: Match PR Pre-Mappings
  console.log('\n[6/6] Matching PR pre-mappings...');
  const matchResult = await matchPRPreMappings();
  
  if (matchResult.totalMatched > 0) {
    console.log(`  Created ${matchResult.totalMatched} pending confirmation(s)`);
    for (const match of matchResult.matches) {
      console.log(`    PR ${match.prNumber}: ${match.matchedCount} line item(s) matched`);
    }
  } else {
    console.log('  No new matches found');
  }
  
  if (matchResult.expiredCount > 0) {
    console.log(`  Expired ${matchResult.expiredCount} pre-mapping(s)`);
  }
  
  // Final stats
  const [{ count: finalActiveCount }] = await db
    .select({ count: sql<number>`count(*)` })
    .from(poLineItems)
    .where(eq(poLineItems.isActive, true));
  
  const [{ count: finalInactiveCount }] = await db
    .select({ count: sql<number>`count(*)` })
    .from(poLineItems)
    .where(eq(poLineItems.isActive, false));
  
  console.log('\n' + '='.repeat(60));
  console.log('Import Complete');
  console.log('='.repeat(60));
  console.log(`  Active records:   ${Number(finalActiveCount).toLocaleString()}`);
  console.log(`  Inactive records: ${Number(finalInactiveCount).toLocaleString()}`);
  console.log(`  Total records:    ${(Number(finalActiveCount) + Number(finalInactiveCount)).toLocaleString()}`);
  
  process.exit(0);
}

// Run
main().catch((error) => {
  console.error('Import failed:', error);
  process.exit(1);
});
