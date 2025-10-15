import { pgSchema, uuid, integer, varchar, text, numeric, timestamp, date } from 'drizzle-orm/pg-core';
import { pos } from './pos';

const devV2Schema = pgSchema('dev_v2');

export const poLineItems = devV2Schema.table('po_line_items', {
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
  invoicedQuantity: numeric('invoiced_quantity'),
  invoicedValueUsd: numeric('invoiced_value_usd'),
  invoiceDate: date('invoice_date'),
  supplierPromiseDate: date('supplier_promise_date'),
});

export type POLineItem = typeof poLineItems.$inferSelect;
export type NewPOLineItem = typeof poLineItems.$inferInsert;
