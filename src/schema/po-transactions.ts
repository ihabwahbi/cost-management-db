import { uuid, varchar, numeric, date, timestamp, index } from 'drizzle-orm/pg-core';
import { poLineItems } from './po-line-items';
import { devV3Schema } from './_schema';

/**
 * PO Transactions - GR (Goods Receipt) and IR (Invoice Receipt) postings
 * 
 * Tracks all transaction postings against PO line items, including
 * calculated cost impact for financial reporting.
 */
export const poTransactions = devV3Schema.table('po_transactions', {
  // Primary key
  id: uuid('id').primaryKey().defaultRandom(),
  
  // Reference to PO Line Item
  poLineItemId: uuid('po_line_item_id')
    .notNull()
    .references(() => poLineItems.id),
  
  // Transaction details
  transactionType: varchar('transaction_type').notNull(), // 'GR' or 'IR'
  postingDate: date('posting_date').notNull(),
  
  // Posting quantities and amounts
  quantity: numeric('quantity').notNull().default('0'),
  amount: numeric('amount').notNull().default('0'),
  
  // Cost impact (calculated based on GR/IR logic)
  costImpactQty: numeric('cost_impact_qty').notNull().default('0'),
  costImpactAmount: numeric('cost_impact_amount').notNull().default('0'),
  
  // Timestamps
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
}, (table) => [
  index('po_transactions_po_line_item_id_idx').on(table.poLineItemId),
  index('po_transactions_posting_date_idx').on(table.postingDate),
  index('po_transactions_type_idx').on(table.transactionType),
]);

export type POTransaction = typeof poTransactions.$inferSelect;
export type NewPOTransaction = typeof poTransactions.$inferInsert;
