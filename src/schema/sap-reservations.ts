import { uuid, varchar, text, numeric, date, integer, timestamp, unique } from 'drizzle-orm/pg-core';
import { wbsDetails } from './wbs-details';
import { poLineItems } from './po-line-items';
import { devV3Schema } from './_schema';

export const sapReservations = devV3Schema.table('sap_reservations', {
  id: uuid('id').primaryKey().defaultRandom(),
  reservationNumber: varchar('reservation_number').notNull(),
  reservationLineNumber: varchar('reservation_line_number').notNull(),
  reservationRequirementDate: date('reservation_requirement_date'),
  partNumber: varchar('part_number'),
  description: text('description'),
  reservationQty: numeric('reservation_qty'),
  reservationValue: numeric('reservation_value'),
  reservationStatus: varchar('reservation_status'),
  poNumber: varchar('po_number'),
  poLineNumber: integer('po_line_number'),
  wbsNumber: varchar('wbs_number').references(() => wbsDetails.wbsNumber),
  assetCode: varchar('asset_code'),
  assetSerialNumber: varchar('asset_serial_number'),
  requester: varchar('requester'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
  poLineItemId: uuid('po_line_item_id').references(() => poLineItems.id),
}, (table) => [
  unique('sap_reservations_unique_line').on(table.reservationNumber, table.reservationLineNumber),
]);

export type SapReservation = typeof sapReservations.$inferSelect;
export type NewSapReservation = typeof sapReservations.$inferInsert;
