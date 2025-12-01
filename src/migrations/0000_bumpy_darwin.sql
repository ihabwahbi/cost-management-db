CREATE SCHEMA "dev_v3";
--> statement-breakpoint
CREATE TABLE "dev_v3"."projects" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" text NOT NULL,
	"sub_business_line" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "dev_v3"."wbs_details" (
	"wbs_number" varchar PRIMARY KEY NOT NULL,
	"wbs_source" varchar NOT NULL,
	"project_number" varchar,
	"operation_number" varchar,
	"ops_activity_number" varchar,
	"wbs_name" text,
	"client_name" text,
	"rig" varchar,
	"ops_district" varchar,
	"location" varchar,
	"sub_business_line" varchar,
	"created_at" timestamp with time zone DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "dev_v3"."cost_breakdown" (
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
CREATE TABLE "dev_v3"."po_line_items" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"po_line_id" varchar NOT NULL,
	"po_number" varchar NOT NULL,
	"po_creation_date" date,
	"plant_code" varchar,
	"location" varchar,
	"sub_business_line" varchar,
	"pr_number" varchar,
	"pr_line" integer,
	"requester" varchar,
	"vendor_id" varchar,
	"vendor_name" varchar,
	"vendor_category" varchar,
	"ultimate_vendor_name" varchar,
	"line_item_number" integer NOT NULL,
	"part_number" varchar,
	"description" text,
	"ordered_qty" numeric NOT NULL,
	"order_unit" varchar,
	"po_value_usd" numeric NOT NULL,
	"account_assignment_category" varchar,
	"nis_line" varchar,
	"wbs_number" varchar,
	"asset_code" varchar,
	"expected_delivery_date" date,
	"po_approval_status" varchar,
	"po_receipt_status" varchar,
	"po_gts_status" varchar,
	"fmt_po" boolean DEFAULT false NOT NULL,
	"open_po_qty" numeric,
	"open_po_value" numeric,
	"created_at" timestamp with time zone DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT now(),
	CONSTRAINT "po_line_items_po_line_id_unique" UNIQUE("po_line_id")
);
--> statement-breakpoint
CREATE TABLE "dev_v3"."po_mappings" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"po_line_item_id" uuid NOT NULL,
	"cost_breakdown_id" uuid NOT NULL,
	"mapped_amount" numeric NOT NULL,
	"mapping_notes" text,
	"mapped_by" varchar,
	"mapped_at" timestamp with time zone DEFAULT now(),
	"created_at" timestamp with time zone DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT now(),
	CONSTRAINT "po_mappings_po_line_item_id_key" UNIQUE("po_line_item_id")
);
--> statement-breakpoint
CREATE TABLE "dev_v3"."po_operations" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"po_line_item_id" uuid NOT NULL,
	"operation_type" varchar NOT NULL,
	"status" varchar DEFAULT 'pending' NOT NULL,
	"requested_by" varchar NOT NULL,
	"requested_at" timestamp with time zone DEFAULT now() NOT NULL,
	"approved_by" varchar,
	"approved_at" timestamp with time zone,
	"completed_at" timestamp with time zone,
	"reason" text NOT NULL,
	"old_value" jsonb,
	"new_value" jsonb,
	"notes" text,
	"created_at" timestamp with time zone DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "dev_v3"."po_transactions" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"po_line_item_id" uuid NOT NULL,
	"transaction_type" varchar NOT NULL,
	"posting_date" date NOT NULL,
	"quantity" numeric DEFAULT '0' NOT NULL,
	"amount" numeric DEFAULT '0' NOT NULL,
	"cost_impact_qty" numeric DEFAULT '0' NOT NULL,
	"cost_impact_amount" numeric DEFAULT '0' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "dev_v3"."grir_exposures" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"po_line_item_id" uuid NOT NULL,
	"grir_qty" numeric DEFAULT '0' NOT NULL,
	"grir_value" numeric DEFAULT '0' NOT NULL,
	"first_exposure_date" date,
	"days_open" integer DEFAULT 0,
	"time_bucket" varchar(20),
	"snapshot_date" date NOT NULL,
	"created_at" timestamp with time zone DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "dev_v3"."sap_reservations" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"reservation_number" varchar NOT NULL,
	"reservation_line_number" varchar NOT NULL,
	"reservation_requirement_date" date,
	"part_number" varchar,
	"description" text,
	"reservation_qty" numeric,
	"reservation_value" numeric,
	"reservation_status" varchar,
	"po_number" varchar,
	"po_line_number" integer,
	"wbs_number" varchar,
	"asset_code" varchar,
	"asset_serial_number" varchar,
	"requester" varchar,
	"created_at" timestamp with time zone DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT now(),
	"po_line_item_id" uuid,
	CONSTRAINT "sap_reservations_unique_line" UNIQUE("reservation_number","reservation_line_number")
);
--> statement-breakpoint
CREATE TABLE "dev_v3"."forecast_versions" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"project_id" uuid NOT NULL,
	"version_number" integer NOT NULL,
	"reason_for_change" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now(),
	"created_by" text DEFAULT 'system'
);
--> statement-breakpoint
CREATE TABLE "dev_v3"."budget_forecasts" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"forecast_version_id" uuid NOT NULL,
	"cost_breakdown_id" uuid NOT NULL,
	"forecasted_cost" numeric DEFAULT '0' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
ALTER TABLE "dev_v3"."cost_breakdown" ADD CONSTRAINT "cost_breakdown_project_id_projects_id_fk" FOREIGN KEY ("project_id") REFERENCES "dev_v3"."projects"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "dev_v3"."po_mappings" ADD CONSTRAINT "po_mappings_po_line_item_id_po_line_items_id_fk" FOREIGN KEY ("po_line_item_id") REFERENCES "dev_v3"."po_line_items"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "dev_v3"."po_mappings" ADD CONSTRAINT "po_mappings_cost_breakdown_id_cost_breakdown_id_fk" FOREIGN KEY ("cost_breakdown_id") REFERENCES "dev_v3"."cost_breakdown"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "dev_v3"."po_operations" ADD CONSTRAINT "po_operations_po_line_item_id_po_line_items_id_fk" FOREIGN KEY ("po_line_item_id") REFERENCES "dev_v3"."po_line_items"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "dev_v3"."po_transactions" ADD CONSTRAINT "po_transactions_po_line_item_id_po_line_items_id_fk" FOREIGN KEY ("po_line_item_id") REFERENCES "dev_v3"."po_line_items"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "dev_v3"."grir_exposures" ADD CONSTRAINT "grir_exposures_po_line_item_id_po_line_items_id_fk" FOREIGN KEY ("po_line_item_id") REFERENCES "dev_v3"."po_line_items"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "dev_v3"."sap_reservations" ADD CONSTRAINT "sap_reservations_po_line_item_id_po_line_items_id_fk" FOREIGN KEY ("po_line_item_id") REFERENCES "dev_v3"."po_line_items"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "dev_v3"."forecast_versions" ADD CONSTRAINT "forecast_versions_project_id_projects_id_fk" FOREIGN KEY ("project_id") REFERENCES "dev_v3"."projects"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "dev_v3"."budget_forecasts" ADD CONSTRAINT "budget_forecasts_forecast_version_id_forecast_versions_id_fk" FOREIGN KEY ("forecast_version_id") REFERENCES "dev_v3"."forecast_versions"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "dev_v3"."budget_forecasts" ADD CONSTRAINT "budget_forecasts_cost_breakdown_id_cost_breakdown_id_fk" FOREIGN KEY ("cost_breakdown_id") REFERENCES "dev_v3"."cost_breakdown"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "wbs_details_wbs_source_idx" ON "dev_v3"."wbs_details" USING btree ("wbs_source");--> statement-breakpoint
CREATE INDEX "wbs_details_project_number_idx" ON "dev_v3"."wbs_details" USING btree ("project_number");--> statement-breakpoint
CREATE INDEX "wbs_details_location_idx" ON "dev_v3"."wbs_details" USING btree ("location");--> statement-breakpoint
CREATE INDEX "cost_breakdown_project_id_idx" ON "dev_v3"."cost_breakdown" USING btree ("project_id");--> statement-breakpoint
CREATE INDEX "po_line_items_po_number_idx" ON "dev_v3"."po_line_items" USING btree ("po_number");--> statement-breakpoint
CREATE INDEX "po_line_items_po_line_id_idx" ON "dev_v3"."po_line_items" USING btree ("po_line_id");--> statement-breakpoint
CREATE INDEX "po_line_items_vendor_category_idx" ON "dev_v3"."po_line_items" USING btree ("vendor_category");--> statement-breakpoint
CREATE INDEX "po_mappings_cost_breakdown_id_idx" ON "dev_v3"."po_mappings" USING btree ("cost_breakdown_id");--> statement-breakpoint
CREATE INDEX "po_operations_po_line_item_id_idx" ON "dev_v3"."po_operations" USING btree ("po_line_item_id");--> statement-breakpoint
CREATE INDEX "po_operations_operation_type_idx" ON "dev_v3"."po_operations" USING btree ("operation_type");--> statement-breakpoint
CREATE INDEX "po_operations_status_idx" ON "dev_v3"."po_operations" USING btree ("status");--> statement-breakpoint
CREATE INDEX "po_operations_requested_at_idx" ON "dev_v3"."po_operations" USING btree ("requested_at");--> statement-breakpoint
CREATE INDEX "po_operations_po_line_item_id_status_idx" ON "dev_v3"."po_operations" USING btree ("po_line_item_id","status");--> statement-breakpoint
CREATE INDEX "po_transactions_po_line_item_id_idx" ON "dev_v3"."po_transactions" USING btree ("po_line_item_id");--> statement-breakpoint
CREATE INDEX "po_transactions_posting_date_idx" ON "dev_v3"."po_transactions" USING btree ("posting_date");--> statement-breakpoint
CREATE INDEX "po_transactions_type_idx" ON "dev_v3"."po_transactions" USING btree ("transaction_type");--> statement-breakpoint
CREATE INDEX "grir_exposures_po_line_item_id_idx" ON "dev_v3"."grir_exposures" USING btree ("po_line_item_id");--> statement-breakpoint
CREATE INDEX "grir_exposures_time_bucket_idx" ON "dev_v3"."grir_exposures" USING btree ("time_bucket");--> statement-breakpoint
CREATE INDEX "grir_exposures_snapshot_date_idx" ON "dev_v3"."grir_exposures" USING btree ("snapshot_date");--> statement-breakpoint
CREATE INDEX "grir_exposures_days_open_idx" ON "dev_v3"."grir_exposures" USING btree ("days_open");--> statement-breakpoint
CREATE INDEX "forecast_versions_project_id_idx" ON "dev_v3"."forecast_versions" USING btree ("project_id");--> statement-breakpoint
CREATE INDEX "budget_forecasts_forecast_version_id_idx" ON "dev_v3"."budget_forecasts" USING btree ("forecast_version_id");--> statement-breakpoint
CREATE INDEX "budget_forecasts_cost_breakdown_id_idx" ON "dev_v3"."budget_forecasts" USING btree ("cost_breakdown_id");