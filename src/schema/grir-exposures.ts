import { uuid, varchar, numeric, date, integer, timestamp, index } from 'drizzle-orm/pg-core';
import { poLineItems } from './po-line-items';
import { devV3Schema } from './_schema';

/**
 * GRIR Exposures - Goods Receipt/Invoice Receipt variance tracking
 * 
 * Tracks exposure for "Simple" POs (GLD vendor + K/P/S/V account assignment)
 * where IR has exceeded GR. This represents value invoiced but not yet
 * goods-received, sitting on balance sheet as potential NIS impact.
 * 
 * Time buckets help identify aging exposures that need attention:
 * - <1 month: Normal, within same period
 * - 1-3 months: Monitor
 * - 3-6 months: Investigate
 * - 6-12 months: Escalate
 * - >1 year: Critical exposure
 */
export const grirExposures = devV3Schema.table('grir_exposures', {
  // Primary key
  id: uuid('id').primaryKey().defaultRandom(),
  
  // Reference to PO Line Item
  poLineItemId: uuid('po_line_item_id')
    .notNull()
    .references(() => poLineItems.id),
  
  // GRIR quantities and values (IR - GR)
  grirQty: numeric('grir_qty').notNull().default('0'),
  grirValue: numeric('grir_value').notNull().default('0'),
  
  // Exposure timing
  firstExposureDate: date('first_exposure_date'), // When IR first exceeded GR
  daysOpen: integer('days_open').default(0),      // Duration of exposure
  
  // Time bucket for aging analysis
  // Values: '<1 month', '1-3 months', '3-6 months', '6-12 months', '>1 year'
  timeBucket: varchar('time_bucket', { length: 20 }),
  
  // Snapshot tracking
  snapshotDate: date('snapshot_date').notNull(), // When this was calculated
  
  // Timestamps
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
}, (table) => [
  index('grir_exposures_po_line_item_id_idx').on(table.poLineItemId),
  index('grir_exposures_time_bucket_idx').on(table.timeBucket),
  index('grir_exposures_snapshot_date_idx').on(table.snapshotDate),
  index('grir_exposures_days_open_idx').on(table.daysOpen),
]);

export type GRIRExposure = typeof grirExposures.$inferSelect;
export type NewGRIRExposure = typeof grirExposures.$inferInsert;
