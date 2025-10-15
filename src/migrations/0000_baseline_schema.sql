CREATE TABLE "projects" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" text NOT NULL,
	"sub_business_line" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "cost_breakdown" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"project_id" uuid NOT NULL,
	"sub_business_line" text NOT NULL,
	"cost_line" text NOT NULL,
	"spend_type" text NOT NULL,
	"spend_sub_category" text NOT NULL,
	"budget_cost" numeric DEFAULT '0' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "pos" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"po_number" varchar NOT NULL,
	"vendor_name" varchar NOT NULL,
	"total_value" numeric NOT NULL,
	"po_creation_date" date NOT NULL,
	"location" varchar NOT NULL,
	"fmt_po" boolean DEFAULT false NOT NULL,
	"created_at" timestamp with time zone DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "po_line_items" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"po_id" uuid NOT NULL,
	"line_item_number" integer NOT NULL,
	"part_number" varchar NOT NULL,
	"description" text NOT NULL,
	"quantity" numeric NOT NULL,
	"uom" varchar NOT NULL,
	"line_value" numeric NOT NULL,
	"created_at" timestamp with time zone DEFAULT now(),
	"invoiced_quantity" numeric,
	"invoiced_value_usd" numeric,
	"invoice_date" date,
	"supplier_promise_date" date
);
--> statement-breakpoint
CREATE TABLE "po_mappings" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"po_line_item_id" uuid NOT NULL,
	"cost_breakdown_id" uuid NOT NULL,
	"mapped_amount" numeric NOT NULL,
	"mapping_notes" text,
	"mapped_by" varchar,
	"mapped_at" timestamp with time zone DEFAULT now(),
	"created_at" timestamp with time zone DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "forecast_versions" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"project_id" uuid NOT NULL,
	"version_number" integer NOT NULL,
	"reason_for_change" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now(),
	"created_by" text DEFAULT 'system'
);
--> statement-breakpoint
CREATE TABLE "budget_forecasts" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"forecast_version_id" uuid NOT NULL,
	"cost_breakdown_id" uuid NOT NULL,
	"forecasted_cost" numeric DEFAULT '0' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
ALTER TABLE "cost_breakdown" ADD CONSTRAINT "cost_breakdown_project_id_projects_id_fk" FOREIGN KEY ("project_id") REFERENCES "public"."projects"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "po_line_items" ADD CONSTRAINT "po_line_items_po_id_pos_id_fk" FOREIGN KEY ("po_id") REFERENCES "public"."pos"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "po_mappings" ADD CONSTRAINT "po_mappings_po_line_item_id_po_line_items_id_fk" FOREIGN KEY ("po_line_item_id") REFERENCES "public"."po_line_items"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "po_mappings" ADD CONSTRAINT "po_mappings_cost_breakdown_id_cost_breakdown_id_fk" FOREIGN KEY ("cost_breakdown_id") REFERENCES "public"."cost_breakdown"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "forecast_versions" ADD CONSTRAINT "forecast_versions_project_id_projects_id_fk" FOREIGN KEY ("project_id") REFERENCES "public"."projects"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "budget_forecasts" ADD CONSTRAINT "budget_forecasts_forecast_version_id_forecast_versions_id_fk" FOREIGN KEY ("forecast_version_id") REFERENCES "public"."forecast_versions"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "budget_forecasts" ADD CONSTRAINT "budget_forecasts_cost_breakdown_id_cost_breakdown_id_fk" FOREIGN KEY ("cost_breakdown_id") REFERENCES "public"."cost_breakdown"("id") ON DELETE no action ON UPDATE no action;