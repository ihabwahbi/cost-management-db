import { varchar, integer, serial, unique } from 'drizzle-orm/pg-core';
import { devV3Schema } from './_schema';
import { relations } from 'drizzle-orm';

/**
 * Business Units — Reference table
 * 
 * Defines the organizational business units used for filtering PO line items.
 * Each business unit is a virtual grouping of sub_business_line codes + locations.
 * 
 * This is NOT SAP-derived data — it's an internal organizational concept.
 * Managed directly in the database (no ETL pipeline involvement).
 * 
 * Examples: "WL Offshore", "WL Land", "TCPF", "DHT & LABR"
 */
export const businessUnits = devV3Schema.table('business_units', {
  id: serial('id').primaryKey(),
  /** Stable key used in API/filters (e.g., 'wl_offshore', 'tcpf') */
  key: varchar('key', { length: 50 }).notNull().unique(),
  /** Display label (e.g., 'WL Offshore', 'TCPF') */
  label: varchar('label', { length: 100 }).notNull(),
  /** Display order in dropdowns (lower = first) */
  sortOrder: integer('sort_order').notNull().default(0),
});

/**
 * Business Unit Rules — Filter mapping rules
 * 
 * Each row defines one (sub_business_line, location) pair that belongs to a business unit.
 * 
 * How filtering works:
 * - A PO line item matches a business unit if its sub_business_line matches ANY rule for that BU
 *   AND (the rule's location is NULL OR the PO's location matches the rule's location).
 * 
 * Location semantics:
 * - NULL location = this SBL belongs to this BU regardless of location
 *   (e.g., TCPF is always "TCPF" no matter where)
 * - Non-NULL location = this SBL only belongs to this BU at this specific location
 *   (e.g., WLES at Perth = "WL Offshore", WLES at Roma = "WL Land")
 */
export const businessUnitRules = devV3Schema.table('business_unit_rules', {
  id: serial('id').primaryKey(),
  /** References business_units.key */
  businessUnitKey: varchar('business_unit_key', { length: 50 }).notNull(),
  /** Sub-business line code (e.g., 'WLES', 'TCPF') */
  subBusinessLine: varchar('sub_business_line', { length: 20 }).notNull(),
  /** Location filter — NULL means "any location" */
  location: varchar('location', { length: 100 }),
}, (table) => [
  unique('bur_unique_rule').on(table.businessUnitKey, table.subBusinessLine, table.location),
]);

// Relations
export const businessUnitsRelations = relations(businessUnits, ({ many }) => ({
  rules: many(businessUnitRules),
}));

export const businessUnitRulesRelations = relations(businessUnitRules, ({ one }) => ({
  businessUnit: one(businessUnits, {
    fields: [businessUnitRules.businessUnitKey],
    references: [businessUnits.key],
  }),
}));

export type BusinessUnit = typeof businessUnits.$inferSelect;
export type NewBusinessUnit = typeof businessUnits.$inferInsert;
export type BusinessUnitRule = typeof businessUnitRules.$inferSelect;
export type NewBusinessUnitRule = typeof businessUnitRules.$inferInsert;
