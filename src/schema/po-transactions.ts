import { uuid, varchar, numeric, date, timestamp, boolean } from 'drizzle-orm/pg-core';
import { poLineItems } from './po-line-items';
import { devV3Schema } from './_schema';

export const poTransactions = devV3Schema.table('po_transactions', {
  id: uuid('id').primaryKey().defaultRandom(),
  poLineItemId: uuid('po_line_item_id')
    .notNull()
    .references(() => poLineItems.id),
  transactionType: varchar('transaction_type').notNull(),
  postingDate: date('posting_date').notNull(),
  quantity: numeric('quantity').notNull().default('0'),
  amount: numeric('amount').notNull().default('0'),
  costRecognizedQty: numeric('cost_recognized_qty').notNull().default('0'),
  isCostRecognized: boolean('is_cost_recognized').notNull().default(false),
  referenceNumber: varchar('reference_number'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
});

export type POTransaction = typeof poTransactions.$inferSelect;
export type NewPOTransaction = typeof poTransactions.$inferInsert;
