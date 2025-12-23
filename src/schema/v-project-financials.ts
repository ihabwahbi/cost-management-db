import { sql } from 'drizzle-orm';
import { uuid, text, numeric, integer } from 'drizzle-orm/pg-core';
import { devV3Schema } from './_schema';

/**
 * View: v_project_financials
 *
 * Consolidates what getKPIMetrics, getProjectMetrics, and getPLMetrics
 * compute independently. Pre-aggregates budget, committed, and P&L impact
 * per project using the latest forecast version.
 *
 * Uses pre-computed cost_impact_pct from the ETL pipeline.
 * Falls back to 0.6 when cost_impact_pct is NULL (matches FALLBACK_INVOICE_RATIO).
 */
export const vProjectFinancials = devV3Schema.view('v_project_financials', {
  projectId: uuid('project_id'),
  projectName: text('project_name'),
  subBusinessLine: text('sub_business_line'),
  totalBudget: numeric('total_budget'),
  totalCommitted: numeric('total_committed'),
  actualPlImpact: numeric('actual_pl_impact'),
  futurePlImpact: numeric('future_pl_impact'),
  poCount: integer('po_count'),
  lineItemCount: integer('line_item_count'),
}).as(sql`
  SELECT
    p.id AS project_id,
    p.name AS project_name,
    p.sub_business_line,
    COALESCE(budget.total_budget, 0) AS total_budget,
    COALESCE(SUM(pm.mapped_amount), 0) AS total_committed,
    COALESCE(SUM(
      pm.mapped_amount * COALESCE(pli.cost_impact_pct, 0.6)
    ), 0) AS actual_pl_impact,
    COALESCE(SUM(
      pm.mapped_amount * (1 - COALESCE(pli.cost_impact_pct, 0.6))
    ), 0) AS future_pl_impact,
    COUNT(DISTINCT pli.po_number) FILTER (WHERE pli.is_active) AS po_count,
    COUNT(pli.id) FILTER (WHERE pli.is_active) AS line_item_count
  FROM dev_v3.projects p
  LEFT JOIN dev_v3.cost_breakdown cb ON cb.project_id = p.id
  LEFT JOIN dev_v3.po_mappings pm ON pm.cost_breakdown_id = cb.id
  LEFT JOIN dev_v3.po_line_items pli ON pli.id = pm.po_line_item_id
  LEFT JOIN LATERAL (
    SELECT SUM(bf.forecasted_cost) AS total_budget
    FROM dev_v3.budget_forecasts bf
    JOIN dev_v3.forecast_versions fv ON bf.forecast_version_id = fv.id
    WHERE fv.project_id = p.id
      AND fv.version_number = (
        SELECT MAX(fv2.version_number) FROM dev_v3.forecast_versions fv2
        WHERE fv2.project_id = p.id
      )
  ) budget ON true
  GROUP BY p.id, p.name, p.sub_business_line, budget.total_budget
`);

export type ProjectFinancialsView = typeof vProjectFinancials.$inferSelect;
