import { uuid, varchar, text, numeric, date, integer, timestamp, unique, index } from 'drizzle-orm/pg-core';
import { devV3Schema } from './_schema';

// NOTE: FK constraints removed to allow storing values even when parent records
// don't exist. This enables investigation of orphan WBS/PO references.
// The columns still store the same values, just without database-level enforcement.

export const sapReservations = devV3Schema.table('sap_reservations', {
  id: uuid('id').primaryKey().defaultRandom(),
  
  // Business key - matches source system format (e.g., "6086214878-1")
  reservationLineId: varchar('reservation_line_id').notNull().unique(),
  
  // Split components for grouping and sorting
  reservationNumber: varchar('reservation_number').notNull(),
  reservationLineNumber: integer('reservation_line_number').notNull(),
  reservationRequirementDate: date('reservation_requirement_date'),
  reservationCreationDate: date('reservation_creation_date'),
  
  partNumber: varchar('part_number'),
  description: text('description'),
  
  // Renamed: reservation_qty → open_reservation_qty, reservation_value → open_reservation_value
  openReservationQty: numeric('open_reservation_qty'),
  openReservationValue: numeric('open_reservation_value'),
  
  reservationStatus: varchar('reservation_status'),
  reservationSource: varchar('reservation_source'),
  
  poNumber: varchar('po_number'),
  poLineNumber: integer('po_line_number'),
  
  // WBS reference - stores wbs_number value (no FK constraint for investigation)
  // Can query orphans with: LEFT JOIN wbs_details WHERE wbs_details.wbs_number IS NULL
  wbsNumber: varchar('wbs_number'),
  
  assetCode: varchar('asset_code'),
  assetSerialNumber: varchar('asset_serial_number'),
  plantCode: varchar('plant_code'),
  
  // Renamed: requester → requester_alias
  requesterAlias: varchar('requester_alias'),
  
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
  
  // PO Line reference - stores po_line_id value (no FK constraint for investigation)
  // Can query orphans with: LEFT JOIN po_line_items WHERE po_line_items.po_line_id IS NULL
  poLineItemId: varchar('po_line_item_id'),
}, (table) => [
  unique('sap_reservations_unique_line').on(table.reservationNumber, table.reservationLineNumber),
  // Index for efficient lookups on the PO line relationship
  index('sap_reservations_po_line_item_id_idx').on(table.poLineItemId),
]);

export type SapReservation = typeof sapReservations.$inferSelect;
export type NewSapReservation = typeof sapReservations.$inferInsert;
