import { pgTable, pgSchema, uuid, text, timestamp, numeric, varchar, date, boolean, integer } from "drizzle-orm/pg-core"
import { sql } from "drizzle-orm"

export const devV2 = pgSchema("dev_v2");


export const projectsInDevV2 = devV2.table("projects", {
	id: uuid().defaultRandom().primaryKey().notNull(),
	name: text().notNull(),
	subBusinessLine: text("sub_business_line").notNull(),
	createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow(),
	updatedAt: timestamp("updated_at", { withTimezone: true, mode: 'string' }).defaultNow(),
});

export const costBreakdownInDevV2 = devV2.table("cost_breakdown", {
	id: uuid().defaultRandom().primaryKey().notNull(),
	projectId: uuid("project_id").notNull(),
	subBusinessLine: text("sub_business_line").notNull(),
	costLine: text("cost_line").notNull(),
	spendType: text("spend_type").notNull(),
	spendSubCategory: text("spend_sub_category").notNull(),
	budgetCost: numeric("budget_cost").default('0').notNull(),
	createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow(),
	updatedAt: timestamp("updated_at", { withTimezone: true, mode: 'string' }).defaultNow(),
});

export const posInDevV2 = devV2.table("pos", {
	id: uuid().defaultRandom().primaryKey().notNull(),
	poNumber: varchar("po_number").notNull(),
	vendorName: varchar("vendor_name").notNull(),
	totalValue: numeric("total_value").notNull(),
	poCreationDate: date("po_creation_date").notNull(),
	location: varchar().notNull(),
	fmtPo: boolean("fmt_po").default(false).notNull(),
	createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow(),
	updatedAt: timestamp("updated_at", { withTimezone: true, mode: 'string' }).defaultNow(),
});

export const poLineItemsInDevV2 = devV2.table("po_line_items", {
	id: uuid().defaultRandom().primaryKey().notNull(),
	poId: uuid("po_id").notNull(),
	lineItemNumber: integer("line_item_number").notNull(),
	partNumber: varchar("part_number").notNull(),
	description: text().notNull(),
	quantity: numeric().notNull(),
	uom: varchar().notNull(),
	lineValue: numeric("line_value").notNull(),
	createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow(),
	invoicedQuantity: numeric("invoiced_quantity"),
	invoicedValueUsd: numeric("invoiced_value_usd"),
	invoiceDate: date("invoice_date"),
	supplierPromiseDate: date("supplier_promise_date"),
});

export const poMappingsInDevV2 = devV2.table("po_mappings", {
	id: uuid().defaultRandom().primaryKey().notNull(),
	poLineItemId: uuid("po_line_item_id").notNull(),
	costBreakdownId: uuid("cost_breakdown_id").notNull(),
	mappedAmount: numeric("mapped_amount").notNull(),
	mappingNotes: text("mapping_notes"),
	mappedBy: varchar("mapped_by"),
	mappedAt: timestamp("mapped_at", { withTimezone: true, mode: 'string' }).defaultNow(),
	createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow(),
	updatedAt: timestamp("updated_at", { withTimezone: true, mode: 'string' }).defaultNow(),
});

export const forecastVersionsInDevV2 = devV2.table("forecast_versions", {
	id: uuid().defaultRandom().primaryKey().notNull(),
	projectId: uuid("project_id").notNull(),
	versionNumber: integer("version_number").notNull(),
	reasonForChange: text("reason_for_change").notNull(),
	createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow(),
	createdBy: text("created_by").default('system'),
});

export const budgetForecastsInDevV2 = devV2.table("budget_forecasts", {
	id: uuid().defaultRandom().primaryKey().notNull(),
	forecastVersionId: uuid("forecast_version_id").notNull(),
	costBreakdownId: uuid("cost_breakdown_id").notNull(),
	forecastedCost: numeric("forecasted_cost").default('0').notNull(),
	createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow(),
});
