import { varchar, text, timestamp, index } from 'drizzle-orm/pg-core';
import { devV3Schema } from './_schema';

/**
 * WBS Details - Work Breakdown Structure information
 * 
 * WBS data is sourced from three FDP reports:
 * - ProjectDashboard: Projects with multiple WBS per row (comma-separated with SBL codes in brackets)
 * - OperationDashboard: Operations with single WBS but may have multiple SBL codes
 * - OperationActivityDashboard: Ops Activities with single WBS per row
 * 
 * WBS numbers are globally unique across all sources - verified that no WBS
 * appears in multiple reports. Therefore wbs_number is the natural primary key.
 * 
 * Sub Business Lines are stored as a text array since Operations can have
 * multiple SBL codes (e.g., ["SLKN", "WLPS", "WLES"]).
 */
export const wbsDetails = devV3Schema.table('wbs_details', {
  // Primary key - WBS number format: J.XX.XXXXXX (e.g., J.24.079733)
  // Globally unique across all FDP reports
  wbsNumber: varchar('wbs_number').primaryKey(),
  
  // Source of the WBS data (for tracking/audit)
  // Values: 'Project', 'Operation', 'Operation Activity'
  wbsSource: varchar('wbs_source').notNull(),
  
  // Source identifiers - which record this WBS came from
  projectNumber: varchar('project_number'),      // e.g., P.1020480
  operationNumber: varchar('operation_number'),  // e.g., O.1020480.01
  opsActivityNumber: varchar('ops_activity_number'), // e.g., A.1020480.01.05
  
  // WBS descriptive fields
  wbsName: text('wbs_name'),  // From Project Name / Operation Name / Ops Activity Name
  clientName: text('client_name'),  // Customer
  
  // Equipment and location
  rig: varchar('rig'),  // Rig name or Project Type as fallback
  opsDistrict: varchar('ops_district'),  // e.g., "Roma WL", "Moomba WL"
  location: varchar('location'),  // Mapped from ops_district (e.g., "Jandakot", "Roma")
  
  // Business classification - stored as array since Operations can have multiple SBL codes
  // Examples: ["WLPS"], ["SLKN", "WLPS", "WLES"]
  // Query with: WHERE 'WLPS' = ANY(sub_business_lines)
  subBusinessLines: text('sub_business_lines').array(),
  
  // Timestamps
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
}, (table) => [
  // Index for filtering by source
  index('wbs_details_wbs_source_idx').on(table.wbsSource),
  // Index for project lookups
  index('wbs_details_project_number_idx').on(table.projectNumber),
  // Index for location-based queries
  index('wbs_details_location_idx').on(table.location),
  // GIN index for efficient array containment queries
  // e.g., WHERE sub_business_lines @> ARRAY['WLPS']
  index('wbs_details_sub_business_lines_idx').using('gin', table.subBusinessLines),
]);

export type WbsDetail = typeof wbsDetails.$inferSelect;
export type NewWbsDetail = typeof wbsDetails.$inferInsert;
