import { uuid, integer, varchar, text, numeric, timestamp, date, index, boolean } from 'drizzle-orm/pg-core';
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
  location: varchar('location'),
  subBusinessLine: varchar('sub_business_line'),
  
  // Purchase Requisition (source of PO)
  prNumber: varchar('pr_number'),
  prLine: integer('pr_line'),
  requester: varchar('requester'),  // Person who submitted the requisition
  
  // Vendor information
  vendorId: varchar('vendor_id'),
  vendorName: varchar('vendor_name'),
  vendorCategory: varchar('vendor_category'),
  ultimateVendorName: varchar('ultimate_vendor_name'),
  
  // Line item fields
  lineItemNumber: integer('line_item_number').notNull(),
  partNumber: varchar('part_number'),
  description: text('description'),
  orderedQty: numeric('ordered_qty').notNull(),
  orderUnit: varchar('order_unit'),
  poValueUsd: numeric('po_value_usd').notNull(),
  
  // Cost classification
  accountAssignmentCategory: varchar('account_assignment_category'),
  nisLine: varchar('nis_line'),
  // WBS reference (no FK - wbsNumber is not PK anymore, use for lookups)
  wbsNumber: varchar('wbs_number'),
  
  // Asset reference (for maintenance POs)
  assetCode: varchar('asset_code'),
  
  // Dates
  expectedDeliveryDate: date('expected_delivery_date'),
  
  // Status flags
  poApprovalStatus: varchar('po_approval_status'),
  poReceiptStatus: varchar('po_receipt_status'),  // Open = future cost impact possible, Closed = no further impact
  poGtsStatus: varchar('po_gts_status'),
  fmtPo: boolean('fmt_po').notNull().default(false),
  
  // Open PO values (calculated: total - cost impact recognized, forced to 0 for closed POs)
  openPoQty: numeric('open_po_qty'),      // orderedQty - SUM(cost_impact_qty)
  openPoValue: numeric('open_po_value'),  // poValueUsd - SUM(cost_impact_amount)
  
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
