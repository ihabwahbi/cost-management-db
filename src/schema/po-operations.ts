import { uuid, varchar, text, timestamp, jsonb, index } from 'drizzle-orm/pg-core';
import { pos } from './pos';
import { poLineItems } from './po-line-items';
import { devV3Schema } from './_schema';

export const poOperations = devV3Schema.table('po_operations', {
  id: uuid('id').primaryKey().defaultRandom(),
  poId: uuid('po_id')
    .notNull()
    .references(() => pos.id),
  poLineItemId: uuid('po_line_item_id')
    .references(() => poLineItems.id),
  operationType: varchar('operation_type').notNull(),
  status: varchar('status').notNull().default('pending'),
  requestedBy: varchar('requested_by').notNull(),
  requestedAt: timestamp('requested_at', { withTimezone: true }).notNull().defaultNow(),
  approvedBy: varchar('approved_by'),
  approvedAt: timestamp('approved_at', { withTimezone: true }),
  completedAt: timestamp('completed_at', { withTimezone: true }),
  reason: text('reason').notNull(),
  oldValue: jsonb('old_value'),
  newValue: jsonb('new_value'),
  notes: text('notes'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
}, (table) => [
  index('po_operations_po_id_idx').on(table.poId),
  index('po_operations_po_line_item_id_idx').on(table.poLineItemId),
  index('po_operations_operation_type_idx').on(table.operationType),
  index('po_operations_status_idx').on(table.status),
  index('po_operations_requested_at_idx').on(table.requestedAt),
  index('po_operations_po_line_item_id_status_idx').on(table.poLineItemId, table.status),
]);

export type POOperation = typeof poOperations.$inferSelect;
export type NewPOOperation = typeof poOperations.$inferInsert;
