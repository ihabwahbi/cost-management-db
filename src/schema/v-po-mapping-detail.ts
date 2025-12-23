import { sql } from 'drizzle-orm';
import { uuid, text, numeric, timestamp, boolean } from 'drizzle-orm/pg-core';
import { devV3Schema } from './_schema';

/**
 * View: v_po_mapping_detail
 *
 * Pre-joins the 4-table pattern (po_mappings → cost_breakdown → projects,
 * po_mappings → po_line_items) used by 6+ procedures.
 *
 * Includes pre-computed cost_impact_value and cost_impact_pct from ETL.
 */
export const vPoMappingDetail = devV3Schema.view('v_po_mapping_detail', {
  mappingId: uuid('mapping_id'),
  mappedAmount: numeric('mapped_amount'),
  mappingSource: text('mapping_source'),
  requiresConfirmation: boolean('requires_confirmation'),
  confirmedAt: timestamp('confirmed_at', { withTimezone: true }),
  mappingCreatedAt: timestamp('mapping_created_at', { withTimezone: true }),
  costBreakdownId: uuid('cost_breakdown_id'),
  costLine: text('cost_line'),
  spendType: text('spend_type'),
  spendSubCategory: text('spend_sub_category'),
  budgetCost: numeric('budget_cost'),
  projectId: uuid('project_id'),
  projectName: text('project_name'),
  poLineItemId: uuid('po_line_item_id'),
  poLineId: text('po_line_id'),
  poNumber: text('po_number'),
  vendorName: text('vendor_name'),
  poValueUsd: numeric('po_value_usd'),
  openPoValue: numeric('open_po_value'),
  costImpactValue: numeric('cost_impact_value'),
  costImpactPct: numeric('cost_impact_pct'),
  expectedDeliveryDate: timestamp('expected_delivery_date', { withTimezone: true }),
  poReceiptStatus: text('po_receipt_status'),
  location: text('location'),
  nisLine: text('nis_line'),
  isActive: boolean('is_active'),
  poCreatedAt: timestamp('po_created_at', { withTimezone: true }),
}).as(sql`
  SELECT
    pm.id AS mapping_id,
    pm.mapped_amount,
    pm.mapping_source,
    pm.requires_confirmation,
    pm.confirmed_at,
    pm.created_at AS mapping_created_at,
    cb.id AS cost_breakdown_id,
    cb.cost_line,
    cb.spend_type,
    cb.spend_sub_category,
    cb.budget_cost,
    p.id AS project_id,
    p.name AS project_name,
    pli.id AS po_line_item_id,
    pli.po_line_id,
    pli.po_number,
    pli.vendor_name,
    pli.po_value_usd,
    pli.open_po_value,
    pli.cost_impact_value,
    pli.cost_impact_pct,
    pli.expected_delivery_date,
    pli.po_receipt_status,
    pli.location,
    pli.nis_line,
    pli.is_active,
    pli.created_at AS po_created_at
  FROM dev_v3.po_mappings pm
  JOIN dev_v3.cost_breakdown cb ON cb.id = pm.cost_breakdown_id
  JOIN dev_v3.projects p ON p.id = cb.project_id
  LEFT JOIN dev_v3.po_line_items pli ON pli.id = pm.po_line_item_id
`);

export type PoMappingDetailView = typeof vPoMappingDetail.$inferSelect;
