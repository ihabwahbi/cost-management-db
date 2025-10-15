import { uuid, numeric, timestamp } from 'drizzle-orm/pg-core';
import { forecastVersions } from './forecast-versions';
import { costBreakdown } from './cost-breakdown';
import { devV2Schema } from './_schema';

export const budgetForecasts = devV2Schema.table('budget_forecasts', {
  id: uuid('id').primaryKey().defaultRandom(),
  forecastVersionId: uuid('forecast_version_id')
    .notNull()
    .references(() => forecastVersions.id),
  costBreakdownId: uuid('cost_breakdown_id')
    .notNull()
    .references(() => costBreakdown.id),
  forecastedCost: numeric('forecasted_cost').notNull().default('0'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
});

export type BudgetForecast = typeof budgetForecasts.$inferSelect;
export type NewBudgetForecast = typeof budgetForecasts.$inferInsert;
