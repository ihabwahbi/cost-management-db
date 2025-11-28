import { uuid, integer, varchar, text, numeric, timestamp, date, index, boolean } from 'drizzle-orm/pg-core';
import { wbsDetails } from './wbs-details';
import { devV3Schema } from './_schema';

/**
 * PO Line Items - Combined PO header and line item data
 * 
 * This denormalized table contains both PO-level and line-level information,
 * optimized for cost management reporting and analysis.
 */
export const poLineItems = devV3Schema.table('po_line_items', {
  // Primary key
  id: uuid('id').primaryKey().defaultRandom(),
  
  // Business key - matches source system (e.g., "4581848878-1")
  poLineId: varchar('po_line_id').notNull().unique(),
  
  // PO Header fields (from pos table)
  poNumber: varchar('po_number').notNull(),
  poCreationDate: date('po_creation_date'),
  plantCode: varchar('plant_code'),
  subBusinessLine: varchar('sub_business_line'),
  
  // Vendor information
  vendorId: varchar('vendor_id'),
  vendorName: varchar('vendor_name'),
  vendorCategory: varchar('vendor_category'),
  
  // Line item fields
  lineItemNumber: integer('line_item_number').notNull(),
  partNumber: varchar('part_number'),
  description: text('description'),
  quantity: numeric('quantity').notNull(),
  lineValue: numeric('line_value').notNull(),
  
  // Cost classification
  accountAssignmentCategory: varchar('account_assignment_category'),
  nisLine: varchar('nis_line'),
  wbsNumber: varchar('wbs_number').references(() => wbsDetails.wbsNumber),
  
  // Dates
  expectedDeliveryDate: date('expected_delivery_date'),
  
  // Status flags
  fmtPo: boolean('fmt_po').notNull().default(false),
  
  // Timestamps
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
}, (table) => [
  index('po_line_items_po_number_idx').on(table.poNumber),
  index('po_line_items_po_line_id_idx').on(table.poLineId),
  index('po_line_items_vendor_category_idx').on(table.vendorCategory),
]);

export type POLineItem = typeof poLineItems.$inferSelect;
export type NewPOLineItem = typeof poLineItems.$inferInsert;
