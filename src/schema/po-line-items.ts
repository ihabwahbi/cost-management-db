import { uuid, integer, varchar, text, numeric, timestamp, date, index } from 'drizzle-orm/pg-core';
import { pos } from './pos';
import { wbsDetails } from './wbs-details';
import { devV3Schema } from './_schema';

export const poLineItems = devV3Schema.table('po_line_items', {
  id: uuid('id').primaryKey().defaultRandom(),
  poId: uuid('po_id')
    .notNull()
    .references(() => pos.id),
  lineItemNumber: integer('line_item_number').notNull(),
  partNumber: varchar('part_number').notNull(),
  description: text('description').notNull(),
  quantity: numeric('quantity').notNull(),
  uom: varchar('uom').notNull(),
  lineValue: numeric('line_value').notNull(),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  supplierPromiseDate: date('supplier_promise_date'),
  wbsNumber: varchar('wbs_number').references(() => wbsDetails.wbsNumber),
  nisCostLine: text('nis_cost_line'),
  poType: text('po_type'),
  purchaseRequisitionNumber: varchar('purchase_requisition_number'),
  purchaseRequisitionLine: integer('purchase_requisition_line'),
}, (table) => [
  index('po_line_items_po_id_idx').on(table.poId),
]);

export type POLineItem = typeof poLineItems.$inferSelect;
export type NewPOLineItem = typeof poLineItems.$inferInsert;
