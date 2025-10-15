/**
 * @cost-mgmt/db - Database layer with Drizzle ORM
 * 
 * Provides type-safe database access to Supabase PostgreSQL
 */

export { db, schema } from './client';
export * from './schema';

// Explicit type exports for better discoverability
// These types are inferred from Drizzle schemas and available for frontend consumption
export type {
  Project,
  NewProject,
  CostBreakdown,
  NewCostBreakdown,
  PO,
  NewPO,
  POLineItem,
  NewPOLineItem,
  POMapping,
  NewPOMapping,
  ForecastVersion,
  NewForecastVersion,
  BudgetForecast,
  NewBudgetForecast,
} from './schema';
