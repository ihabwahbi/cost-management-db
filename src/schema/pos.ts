import { uuid, varchar, numeric, date, timestamp, boolean } from 'drizzle-orm/pg-core';
import { devV2Schema } from './_schema';

export const pos = devV2Schema.table('pos', {
  id: uuid('id').primaryKey().defaultRandom(),
  poNumber: varchar('po_number').notNull(),
  vendorName: varchar('vendor_name').notNull(),
  totalValue: numeric('total_value').notNull(),
  poCreationDate: date('po_creation_date').notNull(),
  location: varchar('location').notNull(),
  fmtPo: boolean('fmt_po').notNull().default(false),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
});

export type PO = typeof pos.$inferSelect;
export type NewPO = typeof pos.$inferInsert;
