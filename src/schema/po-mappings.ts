import { uuid, numeric, text, varchar, timestamp, boolean, index, unique } from 'drizzle-orm/pg-core';
import { costBreakdown } from './cost-breakdown';
import { poLineItems } from './po-line-items';
import { prPreMappings } from './pr-pre-mappings';
import { projects } from './projects';
import { devV3Schema } from './_schema';

/**
 * PO Mappings - Links PO line items to cost breakdown categories
 * 
 * Supports two mapping levels:
 * - Full mapping: projectId + spendType + costBreakdownId (resolved via spend sub-category)
 * - Partial mapping: projectId + spendType only (costBreakdownId is NULL)
 * 
 * Mapping sources:
 * - 'manual': User created mapping directly in UI
 * - 'pre-mapping': Auto-created from PR pre-mapping match
 * - 'bulk': Created via bulk mapping tool
 * - 'inline': Created via inline table mapping
 * 
 * Confirmation workflow (for pre-mapping source):
 * 1. ETL creates mapping with requiresConfirmation = true
 * 2. User confirms/changes/rejects in inbox
 * 3. confirmedAt/confirmedBy set on confirmation
 */
export const poMappings = devV3Schema.table('po_mappings', {
  id: uuid('id').primaryKey().defaultRandom(),
  poLineItemId: uuid('po_line_item_id')
    .notNull()
    .references(() => poLineItems.id),
  costBreakdownId: uuid('cost_breakdown_id')
    .references(() => costBreakdown.id),
  mappedAmount: numeric('mapped_amount').notNull(),
  mappingNotes: text('mapping_notes'),
  mappedBy: varchar('mapped_by'),
  mappedAt: timestamp('mapped_at', { withTimezone: true }).defaultNow(),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
  
  // Direct project + spend type references (always populated on mapping)
  // Enables partial mappings without requiring a cost_breakdown record
  projectId: uuid('project_id').references(() => projects.id),
  spendType: text('spend_type'),
  
  // Source tracking - how was this mapping created?
  mappingSource: varchar('mapping_source', { length: 20 }).notNull().default('manual'),
  
  // Link to originating pre-mapping (for audit trail)
  sourcePrPreMappingId: uuid('source_pr_pre_mapping_id')
    .references(() => prPreMappings.id),
  
  // Confirmation tracking (for inbox workflow)
  requiresConfirmation: boolean('requires_confirmation').notNull().default(false),
  confirmedAt: timestamp('confirmed_at', { withTimezone: true }),
  confirmedBy: varchar('confirmed_by'),
  
  // Amortisation tracking - whether this PO's M&S spend is amortised over time
  isAmortised: boolean('is_amortised').notNull().default(false),
  amortisationSource: varchar('amortisation_source', { length: 10 }), // 'auto' | 'manual'
  amortisedBy: varchar('amortised_by'),
  amortisedAt: timestamp('amortised_at', { withTimezone: true }),
}, (table) => [
  unique('po_mappings_po_line_item_id_key').on(table.poLineItemId),
  index('po_mappings_cost_breakdown_id_idx').on(table.costBreakdownId),
  index('po_mappings_project_id_idx').on(table.projectId),
  // For inbox queries - find all pending confirmations
  index('po_mappings_requires_confirmation_idx').on(table.requiresConfirmation),
  // For pre-mapping stats - find all mappings from a specific pre-mapping
  index('po_mappings_source_pr_pre_mapping_id_idx').on(table.sourcePrPreMappingId),
  // For amortisation queries in spend timeline aggregation
  index('po_mappings_is_amortised_idx').on(table.isAmortised),
]);

export type POMapping = typeof poMappings.$inferSelect;
export type NewPOMapping = typeof poMappings.$inferInsert;
