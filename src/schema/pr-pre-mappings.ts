import { uuid, varchar, integer, text, timestamp, index, unique } from 'drizzle-orm/pg-core';
import { costBreakdown } from './cost-breakdown';
import { devV3Schema } from './_schema';

/**
 * PR Pre-Mappings - Advance project allocation for Purchase Requisitions
 * 
 * Lifecycle:
 * 1. User creates pre-mapping: status = 'active'
 * 2. ETL finds matching PO: creates po_mapping with requiresConfirmation = true
 * 3. User confirms matches in inbox
 * 4. User closes pre-mapping: status = 'closed'
 * 5. Future imports: CLOSED pre-mappings are ignored
 * 
 * Status values:
 * - 'active': Pre-mapping is active and will match new POs
 * - 'closed': User marked complete, no more matching
 * - 'expired': Exceeded expiry date without closure
 * - 'cancelled': User cancelled before any matches
 */
export const prPreMappings = devV3Schema.table('pr_pre_mappings', {
  id: uuid('id').primaryKey().defaultRandom(),
  
  // PR identification
  prNumber: varchar('pr_number', { length: 20 }).notNull(),
  prLine: integer('pr_line'), // NULL = all lines, specific = single line
  
  // Target mapping
  costBreakdownId: uuid('cost_breakdown_id')
    .notNull()
    .references(() => costBreakdown.id),
  
  // Status: 'active' | 'closed' | 'expired' | 'cancelled'
  status: varchar('status', { length: 20 }).notNull().default('active'),
  
  // Tracking counts (for UI display)
  pendingConfirmationCount: integer('pending_confirmation_count').notNull().default(0),
  confirmedCount: integer('confirmed_count').notNull().default(0),
  
  // Closure tracking
  closedAt: timestamp('closed_at', { withTimezone: true }),
  closedBy: varchar('closed_by'),
  
  // User context
  notes: text('notes'),
  createdBy: varchar('created_by'),
  
  // Expiry (for cleanup of unmatched records)
  expiresAt: timestamp('expires_at', { withTimezone: true }).notNull(),
  
  // Timestamps
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
}, (table) => [
  index('pr_pre_mappings_pr_number_idx').on(table.prNumber),
  index('pr_pre_mappings_status_idx').on(table.status),
  index('pr_pre_mappings_expires_at_idx').on(table.expiresAt),
  unique('pr_pre_mappings_pr_number_line_unique').on(table.prNumber, table.prLine),
]);

export type PRPreMapping = typeof prPreMappings.$inferSelect;
export type NewPRPreMapping = typeof prPreMappings.$inferInsert;

/**
 * Default expiry period for pre-mappings (90 days)
 */
export const PR_PRE_MAPPING_EXPIRY_DAYS = 90;
