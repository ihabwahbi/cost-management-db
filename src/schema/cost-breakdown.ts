import { uuid, text, numeric, timestamp, index } from 'drizzle-orm/pg-core';
import { projects } from './projects';
import { devV3Schema } from './_schema';

export const costBreakdown = devV3Schema.table('cost_breakdown', {
  id: uuid('id').primaryKey().defaultRandom(),
  projectId: uuid('project_id')
    .notNull()
    .references(() => projects.id),
  costLine: text('cost_line').notNull(),
  spendType: text('spend_type').notNull(),
  spendSubCategory: text('spend_sub_category').notNull(),
  budgetCost: numeric('budget_cost').notNull().default('0'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
}, (table) => [
  index('cost_breakdown_project_id_idx').on(table.projectId),
]);

export type CostBreakdown = typeof costBreakdown.$inferSelect;
export type NewCostBreakdown = typeof costBreakdown.$inferInsert;
