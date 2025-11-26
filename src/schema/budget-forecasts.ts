import { uuid, numeric, timestamp, index } from 'drizzle-orm/pg-core';
import { forecastVersions } from './forecast-versions';
import { costBreakdown } from './cost-breakdown';
import { devV3Schema } from './_schema';

export const budgetForecasts = devV3Schema.table('budget_forecasts', {
  id: uuid('id').primaryKey().defaultRandom(),
  forecastVersionId: uuid('forecast_version_id')
    .notNull()
    .references(() => forecastVersions.id),
  costBreakdownId: uuid('cost_breakdown_id')
    .notNull()
    .references(() => costBreakdown.id),
  forecastedCost: numeric('forecasted_cost').notNull().default('0'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
}, (table) => [
  index('budget_forecasts_forecast_version_id_idx').on(table.forecastVersionId),
  index('budget_forecasts_cost_breakdown_id_idx').on(table.costBreakdownId),
]);

export type BudgetForecast = typeof budgetForecasts.$inferSelect;
export type NewBudgetForecast = typeof budgetForecasts.$inferInsert;
