# Pipeline Map

Generated: 2025-12-07T07:44:53.069053+00:00

## Data Flow Diagram

```mermaid
flowchart TD
    subgraph RAW["Raw Data"]
        raw_0["po details report.xlsx"]
        raw_1["invoice table.csv"]
        raw_2["po line items.csv"]
        raw_3["gr table.csv"]
    end

    subgraph STAGE1["Stage 1: Clean"]
        01_po_line_items["01_po_line_items"]
        02_gr_postings["02_gr_postings"]
        03_ir_postings["03_ir_postings"]
        10_wbs_from_projects["10_wbs_from_projects"]
        11_wbs_from_operations["11_wbs_from_operations"]
        12_wbs_from_ops_activities["12_wbs_from_ops_activities"]
        13_reservations["13_reservations"]
    end

    subgraph INTERMEDIATE["Intermediate Data"]
        int_0["gr_postings.csv"]
        int_1["reservations.csv"]
        int_2["unmatched_reservation_pos.csv"]
        int_3["grir_exposures.csv"]
        int_4["wbs_from_operations.csv"]
        int_5["ir_postings.csv"]
        int_6["wbs_from_projects.csv"]
        int_7["po_details_enrichment.csv"]
        int_8["wbs_from_ops_activities.csv"]
        int_9["cost_impact.csv"]
        int_10["wbs_processed.csv"]
        int_11["po_line_items.csv"]
    end

    subgraph STAGE2["Stage 2: Transform"]
        04_enrich_po_line_items["04_enrich_po_line_items"]
        05_calculate_cost_impact["05_calculate_cost_impact"]
        06_calculate_grir["06_calculate_grir"]
        07_process_wbs["07_process_wbs"]
    end

    subgraph STAGE3["Stage 3: Prepare"]
        06_prepare_po_line_items["06_prepare_po_line_items"]
        07_prepare_po_transactions["07_prepare_po_transactions"]
        08_prepare_grir_exposures["08_prepare_grir_exposures"]
        09_prepare_wbs_details["09_prepare_wbs_details"]
        10_prepare_reservations["10_prepare_reservations"]
    end

    subgraph IMPORTREADY["Import-Ready Data"]
        ready_0["po_transactions.csv"]
        ready_1["grir_exposures.csv"]
        ready_2["wbs_details.csv"]
        ready_3["sap_reservations.csv"]
        ready_4["po_line_items.csv"]
    end

    subgraph DB["Database Tables"]
        db_budget_forecasts[("budget_forecasts")]
        db_cost_breakdown[("cost_breakdown")]
        db_forecast_versions[("forecast_versions")]
        db_grir_exposures[("grir_exposures")]
        db_po_line_items[("po_line_items")]
        db_po_mappings[("po_mappings")]
        db_po_operations[("po_operations")]
        db_po_transactions[("po_transactions")]
        db_pr_pre_mappings[("pr_pre_mappings")]
        db_projects[("projects")]
        db_sap_reservations[("sap_reservations")]
        db_wbs_details[("wbs_details")]
    end

    %% Data Flow Connections
    RAW --> STAGE1
    STAGE1 --> INTERMEDIATE
    INTERMEDIATE --> STAGE2
    STAGE2 --> INTERMEDIATE
    INTERMEDIATE --> STAGE3
    STAGE3 --> IMPORTREADY
    IMPORTREADY --> DB
```

## Script Details

| # | Script | Stage | Purpose | Inputs | Outputs |
|---|--------|-------|---------|--------|---------|
| 1 | `01_po_line_items` | stage1_clean | Stage 1: Clean PO Line Items | po line items.csv, po_line_items.csv | po_line_items.csv |
| 2 | `02_gr_postings` | stage1_clean | Stage 1: Clean GR (Goods Receipt) Postings | gr table.csv, po_line_items.csv, gr_postings.csv | po_line_items.csv, gr_postings.csv |
| 3 | `03_ir_postings` | stage1_clean | Stage 1: Clean IR (Invoice Receipt) Postings | invoice table.csv, po_line_items.csv, ir_postings.csv | po_line_items.csv, ir_postings.csv |
| 4 | `10_wbs_from_projects` | stage1_clean | Stage 1: Extract WBS Data from Projects Report | fdp, wbs_from_projects.csv | wbs_from_projects.csv |
| 5 | `11_wbs_from_operations` | stage1_clean | Stage 1: Extract WBS Data from Operations Report | fdp, wbs_from_operations.csv | wbs_from_operations.csv |
| 6 | `12_wbs_from_ops_activities` | stage1_clean | Stage 1: Extract WBS Data from Operation Activitie | fdp, wbs_from_ops_activities.csv | wbs_from_ops_activities.csv |
| 7 | `13_reservations` | stage1_clean | Stage 1: Clean Reservations | reservations, reservations.csv | reservations.csv |
| 8 | `04_enrich_po_line_items` | stage2_transform | Stage 2: Enrich PO Line Items | po details report.xlsx, po_line_items.csv, po_details_enrichment.csv | po_line_items.csv, po_details_enrichment.csv |
| 9 | `05_calculate_cost_impact` | stage2_transform | Stage 2: Calculate Cost Impact | po_line_items.csv, gr_postings.csv, ir_postings.csv, cost_impact.csv | po_line_items.csv, gr_postings.csv, ir_postings.csv, cost_impact.csv |
| 10 | `06_calculate_grir` | stage2_transform | Stage 2: Calculate GRIR Exposures | po_line_items.csv, gr_postings.csv, ir_postings.csv, grir_exposures.csv | po_line_items.csv, gr_postings.csv, ir_postings.csv, grir_exposures.csv |
| 11 | `07_process_wbs` | stage2_transform | Stage 2: Process WBS Data - Split, Parse, and Map  | - | - |
| 12 | `06_prepare_po_line_items` | stage3_prepare | Stage 3: Prepare PO Line Items for Import | po_line_items.csv, cost_impact.csv | po_line_items.csv, cost_impact.csv |
| 13 | `07_prepare_po_transactions` | stage3_prepare | Stage 3: Prepare PO Transactions for Import | cost_impact.csv | cost_impact.csv |
| 14 | `08_prepare_grir_exposures` | stage3_prepare | Stage 3: Prepare GRIR Exposures for Import | grir_exposures.csv | grir_exposures.csv |
| 15 | `09_prepare_wbs_details` | stage3_prepare | Stage 3: Prepare WBS Details for Import | wbs_processed.csv | wbs_processed.csv |
| 16 | `10_prepare_reservations` | stage3_prepare | Stage 3: Prepare SAP Reservations for Import | reservations.csv | reservations.csv |
| 17 | `pipeline` | scripts | Data Pipeline Orchestrator | - | - |

## Script Dependencies

```mermaid
flowchart LR
    06_prepare_po_line_items --> 01_po_line_items
    06_prepare_po_line_items --> 02_gr_postings
    06_calculate_grir --> 02_gr_postings
    06_prepare_po_line_items --> 03_ir_postings
    06_calculate_grir --> 03_ir_postings
    10_prepare_reservations --> 13_reservations
    06_prepare_po_line_items --> 04_enrich_po_line_items
    06_prepare_po_line_items --> 05_calculate_cost_impact
    06_calculate_grir --> 05_calculate_cost_impact
    07_prepare_po_transactions --> 05_calculate_cost_impact
    06_prepare_po_line_items --> 06_calculate_grir
    08_prepare_grir_exposures --> 06_calculate_grir
    07_prepare_po_transactions --> 06_prepare_po_line_items
```

## Column Mappings

### PO Line Items (CSV → DB)

| CSV Column | DB Column |
|------------|-----------|
| PO Line ID | `po_line_id` |
| PO Number | `po_number` |
| PO Document Date | `po_creation_date` |
| Plant Code | `plant_code` |
| Location | `location` |
| SL Sub-Business Line Code (BV Lvl 3) | `sub_business_line` |
| PR Number | `pr_number` |
| PR Line | `pr_line` |
| Requester | `requester` |
| Main Vendor ID | `vendor_id` |

*...and 20 more*

## Database Schema

### `budget_forecasts`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | uuid | PK |
| `forecastVersionId` | uuid | NOT NULL, FK → forecastVersions.id |
| `costBreakdownId` | uuid | NOT NULL, FK → costBreakdown.id |
| `forecastedCost` | numeric | NOT NULL, DEFAULT |
| `createdAt` | timestamp | - |

### `cost_breakdown`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | uuid | PK |
| `projectId` | uuid | NOT NULL, FK → projects.id |
| `subBusinessLine` | text | NOT NULL |
| `costLine` | text | NOT NULL |
| `spendType` | text | NOT NULL |
| `spendSubCategory` | text | NOT NULL |
| `budgetCost` | numeric | NOT NULL, DEFAULT |
| `createdAt` | timestamp | - |
| `updatedAt` | timestamp | - |

### `forecast_versions`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | uuid | PK |
| `projectId` | uuid | NOT NULL, FK → projects.id |
| `versionNumber` | integer | NOT NULL |
| `reasonForChange` | text | NOT NULL |
| `createdAt` | timestamp | - |
| `createdBy` | text | DEFAULT |

### `grir_exposures`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | uuid | PK |
| `poLineItemId` | uuid | NOT NULL, FK → poLineItems.id |
| `grirQty` | numeric | NOT NULL, DEFAULT |
| `grirValue` | numeric | NOT NULL, DEFAULT |
| `firstExposureDate` | date | - |
| `daysOpen` | integer | DEFAULT |
| `timeBucket` | varchar | - |
| `snapshotDate` | date | NOT NULL |
| `createdAt` | timestamp | - |
| `updatedAt` | timestamp | - |

### `po_line_items`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | uuid | PK |
| `poLineId` | varchar | NOT NULL |
| `poNumber` | varchar | NOT NULL |
| `poCreationDate` | date | - |
| `plantCode` | varchar | - |
| `location` | varchar | - |
| `subBusinessLine` | varchar | - |
| `prNumber` | varchar | - |
| `prLine` | integer | - |
| `requester` | varchar | - |
| `vendorId` | varchar | - |
| `vendorName` | varchar | - |
| `vendorCategory` | varchar | - |
| `ultimateVendorName` | varchar | - |
| `lineItemNumber` | integer | NOT NULL |
| *...* | *21 more* | |

### `po_mappings`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | uuid | PK |
| `poLineItemId` | uuid | NOT NULL, FK → poLineItems.id |
| `costBreakdownId` | uuid | NOT NULL, FK → costBreakdown.id |
| `mappedAmount` | numeric | NOT NULL |
| `mappingNotes` | text | - |
| `mappedBy` | varchar | - |
| `mappedAt` | timestamp | - |
| `createdAt` | timestamp | - |
| `updatedAt` | timestamp | - |
| `mappingSource` | varchar | NOT NULL, DEFAULT |
| `sourcePrPreMappingId` | uuid | FK → prPreMappings.id |
| `requiresConfirmation` | boolean | NOT NULL, DEFAULT |
| `confirmedAt` | timestamp | - |
| `confirmedBy` | varchar | - |

### `po_operations`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | uuid | PK |
| `poLineItemId` | uuid | NOT NULL, FK → poLineItems.id |
| `operationType` | varchar | NOT NULL |
| `status` | varchar | NOT NULL, DEFAULT |
| `requestedBy` | varchar | NOT NULL |
| `requestedAt` | timestamp | NOT NULL |
| `approvedBy` | varchar | - |
| `approvedAt` | timestamp | - |
| `completedAt` | timestamp | - |
| `reason` | text | NOT NULL |
| `oldValue` | jsonb | - |
| `newValue` | jsonb | - |
| `notes` | text | - |
| `createdAt` | timestamp | - |
| `updatedAt` | timestamp | - |

### `po_transactions`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | uuid | PK |
| `transactionId` | varchar | NOT NULL |
| `poLineItemId` | uuid | NOT NULL, FK → poLineItems.id |
| `transactionType` | varchar | NOT NULL |
| `postingDate` | date | NOT NULL |
| `quantity` | numeric | NOT NULL, DEFAULT |
| `amount` | numeric | NOT NULL, DEFAULT |
| `costImpactQty` | numeric | NOT NULL, DEFAULT |
| `costImpactAmount` | numeric | NOT NULL, DEFAULT |
| `createdAt` | timestamp | - |
| `updatedAt` | timestamp | - |

### `pr_pre_mappings`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | uuid | PK |
| `prNumber` | varchar | NOT NULL |
| `prLine` | integer | - |
| `costBreakdownId` | uuid | NOT NULL, FK → costBreakdown.id |
| `status` | varchar | NOT NULL, DEFAULT |
| `pendingConfirmationCount` | integer | NOT NULL, DEFAULT |
| `confirmedCount` | integer | NOT NULL, DEFAULT |
| `closedAt` | timestamp | - |
| `closedBy` | varchar | - |
| `notes` | text | - |
| `createdBy` | varchar | - |
| `expiresAt` | timestamp | NOT NULL |
| `createdAt` | timestamp | - |
| `updatedAt` | timestamp | - |

### `projects`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | uuid | PK |
| `name` | text | NOT NULL |
| `subBusinessLine` | text | NOT NULL |
| `createdAt` | timestamp | - |
| `updatedAt` | timestamp | - |

### `sap_reservations`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | uuid | PK |
| `reservationLineId` | varchar | NOT NULL |
| `reservationNumber` | varchar | NOT NULL |
| `reservationLineNumber` | integer | NOT NULL |
| `reservationRequirementDate` | date | - |
| `reservationCreationDate` | date | - |
| `partNumber` | varchar | - |
| `description` | text | - |
| `openReservationQty` | numeric | - |
| `openReservationValue` | numeric | - |
| `reservationStatus` | varchar | - |
| `reservationSource` | varchar | - |
| `poNumber` | varchar | - |
| `poLineNumber` | integer | - |
| `wbsNumber` | varchar | - |
| *...* | *7 more* | |

### `wbs_details`

| Column | Type | Constraints |
|--------|------|-------------|
| `wbsNumber` | varchar | PK |
| `wbsSource` | varchar | NOT NULL |
| `projectNumber` | varchar | - |
| `operationNumber` | varchar | - |
| `opsActivityNumber` | varchar | - |
| `wbsName` | text | - |
| `clientName` | text | - |
| `rig` | varchar | - |
| `opsDistrict` | varchar | - |
| `location` | varchar | - |
| `subBusinessLines` | text | - |
| `createdAt` | timestamp | - |
| `updatedAt` | timestamp | - |

## Data Profiles

Sample data and types for each CSV file:

### `invoice table.csv`

- **Path**: `data/raw/invoice table.csv`
- **Rows**: 65245

| Column | Type |
|--------|------|
| `PO Line ID` | object |
| `Invoice Posting Date` | object |
| `IR Effective Quantity` | float64 |

### `po line items.csv`

- **Path**: `data/raw/po line items.csv`
- **Rows**: 62486

| Column | Type |
|--------|------|
| `PO Document Date` | object |
| `PO Initial Output Date` | object |
| `SL Sub-Business Line Code (BV Lvl 3)` | object |
| `Plant Code` | int64 |
| `PO Approval Status` | object |
| `PO Account Assignment Category` | object |
| `PO Account Assignment Category Desc` | object |
| `PO WBS Element` | object |
| `PO Number` | int64 |
| `PO Line` | int64 |
| *...* | *21 more* |

**Columns with nulls:**
- `PO Initial Output Date`: 128 nulls
- `PO Account Assignment Category`: 10826 nulls
- `PO Account Assignment Category Desc`: 10826 nulls
- `PO WBS Element`: 38616 nulls
- `PO Material Number`: 48541 nulls
- `PO Valuation Class`: 48541 nulls
- `PO Valuation Class Desc`: 48541 nulls
- `NIS Level 0 Desc`: 12261 nulls
- `PO GTS Status`: 102 nulls
- `PO Current Supplier Promised Date`: 33916 nulls

### `gr table.csv`

- **Path**: `data/raw/gr table.csv`
- **Rows**: 77276

| Column | Type |
|--------|------|
| `PO Line ID` | object |
| `GR Posting Date` | object |
| `GR Effective Quantity` | float64 |

### `gr_postings.csv`

- **Path**: `data/intermediate/gr_postings.csv`
- **Rows**: 54243

| Column | Type |
|--------|------|
| `PO Line ID` | object |
| `GR Posting Date` | object |
| `GR Effective Quantity` | float64 |
| `GR Amount` | float64 |

### `reservations.csv`

- **Path**: `data/intermediate/reservations.csv`
- **Rows**: 1485

| Column | Type |
|--------|------|
| `Index` | object |
| `Material-Plant` | object |
| `Plant` | float64 |
| `Geo-Unit` | object |
| `GEO UNIT (Profit Center)` | object |
| `Material` | object |
| `Reservation -Line` | object |
| `Requirements Date` | object |
| `Creation Date` | object |
| `Stock On Hand - DDSC` | float64 |
| *...* | *50 more* |

**Columns with nulls:**
- `Index`: 1 nulls
- `Material-Plant`: 2 nulls
- `Plant`: 2 nulls
- `Geo-Unit`: 2 nulls
- `GEO UNIT (Profit Center)`: 2 nulls
- `Material`: 2 nulls
- `Reservation -Line`: 2 nulls
- `Requirements Date`: 2 nulls
- `Creation Date`: 2 nulls
- `Stock On Hand - DDSC`: 712 nulls
- `Stock On Hand - HDSC`: 901 nulls
- `Last 3 Month Consumption`: 2 nulls
- `Last 6 Month Consumption`: 2 nulls
- `Last 12 Month Consumption`: 2 nulls
- `Material Stratification (Last 6 Month Consumption)`: 2 nulls
- `Material Stratification (Last 12 Month Consumption)`: 2 nulls
- `Open Qty - Reservation`: 2 nulls
- `Open Reservation Value`: 2 nulls
- `Material/Plant-SOH - Total`: 1028 nulls
- `Primary Pegged PO-LN - Open Qty`: 1044 nulls
- `Combined SOH & PO Pegging`: 2 nulls
- `Main - PO Line to Peg to Reservation`: 968 nulls
- `Main - PO to Peg to Reservation`: 968 nulls
- `Additional PO - Line to Peg`: 1466 nulls
- `Primary Pegged PO-LN - Order Qty`: 1044 nulls
- `Primary Pegged PO-LN - Approval Status`: 1044 nulls
- `Primary Pegged PO-LN - RDD Date`: 1044 nulls
- `Pegged Main PO GR Status`: 968 nulls
- `Pegged Main PO Invoice Status`: 968 nulls
- `Primary Pegged PO-LN - Invoice Qty`: 1440 nulls
- `Post Pegging SOH Qty`: 2 nulls
- `Post Pegging PO Qty`: 35 nulls
- `Material Description`: 2 nulls
- `MRP Parameters - MRP Controller`: 2 nulls
- `MRP Parameters - Profit Center`: 2 nulls
- `MRP Parameters - Planned Delivery Time`: 2 nulls
- `MRP Parameters - Prime Status`: 2 nulls
- `MRP Parameters - Safety Stock`: 2 nulls
- `MRP Parameters - Standard Price`: 2 nulls
- `Business Line - By Cost Center`: 299 nulls
- `Sub - Business Line - By Cost Center`: 299 nulls
- `Business Line by Profit Center`: 2 nulls
- `Material/Plant-Open PO Qty - Total`: 2 nulls
- `Purchase Requisition - Status`: 2 nulls
- `Purchase Requisitions`: 1480 nulls
- `Planned Order - Status`: 2 nulls
- `Planned Orders`: 1013 nulls
- `Maximo Asset ID`: 812 nulls
- `Maximo Asset Num`: 812 nulls
- `Maximo Serial No`: 812 nulls
- `Reservation Creation type`: 2 nulls
- `WO Number`: 503 nulls
- `User Name`: 2 nulls
- `Goods recipient`: 16 nulls
- `Maximo - WO STATUS and Part Status`: 2 nulls
- `WBS Element`: 1188 nulls
- `Cost Center`: 299 nulls
- `reservation_line_id`: 2 nulls
- `reservation_number`: 2 nulls
- `reservation_line_number`: 2 nulls

### `unmatched_reservation_pos.csv`

- **Path**: `data/intermediate/unmatched_reservation_pos.csv`
- **Rows**: 30

| Column | Type |
|--------|------|
| `reservation_line_id` | object |
| `reservation_number` | int64 |
| `reservation_line_number` | int64 |
| `reservation_creation_date` | object |
| `reservation_requirement_date` | object |
| `part_number` | object |
| `description` | object |
| `open_reservation_qty` | float64 |
| `open_reservation_value` | float64 |
| `reservation_status` | object |
| *...* | *9 more* |

**Columns with nulls:**
- `wbs_number`: 19 nulls
- `asset_code`: 28 nulls
- `asset_serial_number`: 28 nulls

### `grir_exposures.csv`

- **Path**: `data/import-ready/grir_exposures.csv`
- **Rows**: 65

| Column | Type |
|--------|------|
| `po_line_id` | object |
| `grir_qty` | float64 |
| `grir_value` | float64 |
| `first_exposure_date` | object |
| `days_open` | int64 |
| `time_bucket` | object |
| `snapshot_date` | object |

### `wbs_from_operations.csv`

- **Path**: `data/intermediate/wbs_from_operations.csv`
- **Rows**: 144

| Column | Type |
|--------|------|
| `sap_wbs_raw` | object |
| `wbs_source` | object |
| `project_number` | object |
| `operation_number` | object |
| `ops_activity_number` | float64 |
| `wbs_name` | object |
| `client_name` | object |
| `rig` | object |
| `ops_district` | object |
| `location` | float64 |
| *...* | *1 more* |

**Columns with nulls:**
- `ops_activity_number`: 144 nulls
- `rig`: 10 nulls
- `location`: 144 nulls

### `ir_postings.csv`

- **Path**: `data/intermediate/ir_postings.csv`
- **Rows**: 54036

| Column | Type |
|--------|------|
| `PO Line ID` | object |
| `Invoice Posting Date` | object |
| `IR Effective Quantity` | float64 |
| `Invoice Amount` | float64 |

### `wbs_from_projects.csv`

- **Path**: `data/intermediate/wbs_from_projects.csv`
- **Rows**: 369

| Column | Type |
|--------|------|
| `sap_wbs_raw` | object |
| `wbs_source` | object |
| `project_number` | object |
| `operation_number` | float64 |
| `ops_activity_number` | float64 |
| `wbs_name` | object |
| `client_name` | object |
| `rig` | object |
| `ops_district` | object |
| `location` | object |

**Columns with nulls:**
- `operation_number`: 369 nulls
- `ops_activity_number`: 369 nulls

### `po_details_enrichment.csv`

- **Path**: `data/intermediate/po_details_enrichment.csv`
- **Rows**: 21961

| Column | Type |
|--------|------|
| `PO Line ID` | object |
| `Requester` | object |
| `PR Number` | object |
| `PR Line` | float64 |

**Columns with nulls:**
- `Requester`: 2428 nulls
- `PR Number`: 440 nulls
- `PR Line`: 2 nulls

### `wbs_from_ops_activities.csv`

- **Path**: `data/intermediate/wbs_from_ops_activities.csv`
- **Rows**: 7182

| Column | Type |
|--------|------|
| `sap_wbs_raw` | object |
| `wbs_source` | object |
| `project_number` | object |
| `operation_number` | object |
| `ops_activity_number` | object |
| `wbs_name` | object |
| `client_name` | object |
| `rig` | object |
| `ops_district` | object |
| `location` | float64 |
| *...* | *1 more* |

**Columns with nulls:**
- `rig`: 222 nulls
- `location`: 7182 nulls

### `cost_impact.csv`

- **Path**: `data/intermediate/cost_impact.csv`
- **Rows**: 106563

| Column | Type |
|--------|------|
| `PO Line ID` | object |
| `Posting Date` | object |
| `Posting Type` | object |
| `Posting Qty` | float64 |
| `Cost Impact Qty` | float64 |
| `Cost Impact Amount` | float64 |

### `wbs_processed.csv`

- **Path**: `data/intermediate/wbs_processed.csv`
- **Rows**: 7852

| Column | Type |
|--------|------|
| `wbs_number` | object |
| `wbs_source` | object |
| `project_number` | object |
| `operation_number` | object |
| `ops_activity_number` | object |
| `wbs_name` | object |
| `client_name` | object |
| `rig` | object |
| `ops_district` | object |
| `location` | object |
| *...* | *1 more* |

**Columns with nulls:**
- `operation_number`: 526 nulls
- `ops_activity_number`: 670 nulls
- `rig`: 232 nulls

### `po_line_items.csv`

- **Path**: `data/import-ready/po_line_items.csv`
- **Rows**: 55803

| Column | Type |
|--------|------|
| `po_line_id` | object |
| `po_number` | int64 |
| `po_creation_date` | object |
| `plant_code` | int64 |
| `location` | object |
| `sub_business_line` | object |
| `pr_number` | float64 |
| `pr_line` | float64 |
| `requester` | object |
| `vendor_id` | object |
| *...* | *21 more* |

**Columns with nulls:**
- `pr_number`: 36483 nulls
- `pr_line`: 36070 nulls
- `requester`: 35988 nulls
- `part_number`: 46544 nulls
- `account_assignment_category`: 8774 nulls
- `wbs_number`: 31989 nulls
- `po_gts_status`: 60 nulls

### `po_transactions.csv`

- **Path**: `data/import-ready/po_transactions.csv`
- **Rows**: 106563

| Column | Type |
|--------|------|
| `po_line_id` | object |
| `transaction_type` | object |
| `posting_date` | object |
| `quantity` | float64 |
| `cost_impact_qty` | float64 |
| `cost_impact_amount` | float64 |
| `amount` | float64 |
| `transaction_id` | object |

### `wbs_details.csv`

- **Path**: `data/import-ready/wbs_details.csv`
- **Rows**: 7852

| Column | Type |
|--------|------|
| `wbs_number` | object |
| `wbs_source` | object |
| `project_number` | object |
| `operation_number` | object |
| `ops_activity_number` | object |
| `wbs_name` | object |
| `client_name` | object |
| `rig` | object |
| `ops_district` | object |
| `location` | object |
| *...* | *1 more* |

**Columns with nulls:**
- `operation_number`: 526 nulls
- `ops_activity_number`: 670 nulls
- `rig`: 232 nulls

### `sap_reservations.csv`

- **Path**: `data/import-ready/sap_reservations.csv`
- **Rows**: 1483

| Column | Type |
|--------|------|
| `reservation_line_id` | object |
| `reservation_number` | int64 |
| `reservation_line_number` | int64 |
| `reservation_creation_date` | object |
| `reservation_requirement_date` | object |
| `part_number` | object |
| `description` | object |
| `open_reservation_qty` | float64 |
| `open_reservation_value` | float64 |
| `reservation_status` | object |
| *...* | *9 more* |

**Columns with nulls:**
- `wbs_number`: 1186 nulls
- `requester_alias`: 14 nulls
- `po_number`: 966 nulls
- `po_line_number`: 966 nulls
- `po_line_item_id`: 966 nulls
- `asset_code`: 810 nulls
- `asset_serial_number`: 839 nulls

## Common Errors & Solutions

### KeyError

**Causes:**
- Column doesn't exist in DataFrame
- Previous script in pipeline didn't run
- Column name has different casing or spacing

**Solutions:**
- Check column_mappings.py for correct column names
- Run full pipeline: python3 scripts/pipeline.py
- Use df.columns.tolist() to see actual column names

### MergeError

**Causes:**
- Join columns have different dtypes (int vs str)
- One side has NaN values causing type inference issues

**Solutions:**
- Ensure both join columns are same type: df['col'] = df['col'].astype(str)
- Check for nulls before merge: df['col'].isnull().sum()

### FileNotFoundError

**Causes:**
- Previous pipeline stage didn't run
- Raw data files missing

**Solutions:**
- Run earlier stages first: python3 scripts/pipeline.py --stage1
- Check data/raw/ for source files

### ValueError_date

**Causes:**
- Date column has inconsistent formats
- Non-date values in date column

**Solutions:**
- Use pd.to_datetime with errors='coerce'
- Check for non-date values: df[pd.to_datetime(df['col'], errors='coerce').isna()]

### SchemaValidationError

**Causes:**
- Database schema changed but CSV mapping not updated
- Column dropped in earlier transformation

**Solutions:**
- Compare column_mappings.py with src/schema/*.ts
- Run npm run type-check after schema changes

## Transformation Operations

Key pandas operations used in each script:

### `01_po_line_items`

| Line | Operation | Details |
|------|-----------|---------|
| 103 | column_assign | column: `Location` |
| 114 | column_assign | column: `Expected Delivery Date` |
| 81 | rename | Renames columns |
| 89 | map | Maps values using dictionary or function |
| 94 | map | Maps values using dictionary or function |
| 102 | astype | Converts column types |
| 103 | map | Maps values using dictionary or function |
| 120 | drop | Removes columns or rows |
| 129 | sort_values | Sorts by column values |

### `02_gr_postings`

| Line | Operation | Details |
|------|-----------|---------|
| 53 | column_assign | column: `Unit Price` |
| 64 | column_assign | column: `GR Amount` |
| 59 | merge | on: `PO Line ID` |

### `03_ir_postings`

| Line | Operation | Details |
|------|-----------|---------|
| 44 | column_assign | column: `Unit Price` |
| 55 | column_assign | column: `Invoice Amount` |
| 50 | merge | on: `PO Line ID` |

### `10_wbs_from_projects`

| Line | Operation | Details |
|------|-----------|---------|
| 118 | column_assign | column: `location` |
| 134 | column_assign | column: `rig` |
| 149 | column_assign | column: `wbs_source` |
| 150 | column_assign | column: `operation_number` |
| 151 | column_assign | column: `ops_activity_number` |
| 173 | boolean_filter | Filters rows based on boolean condition |
| 111 | rename | Renames columns |
| 118 | map | Maps values using dictionary or function |
| 89 | astype | Converts column types |
| 139 | astype | Converts column types |

### `11_wbs_from_operations`

| Line | Operation | Details |
|------|-----------|---------|
| 118 | column_assign | column: `wbs_source` |
| 119 | column_assign | column: `ops_activity_number` |
| 122 | column_assign | column: `location` |
| 146 | boolean_filter | Filters rows based on boolean condition |
| 111 | rename | Renames columns |
| 89 | astype | Converts column types |

### `12_wbs_from_ops_activities`

| Line | Operation | Details |
|------|-----------|---------|
| 120 | column_assign | column: `wbs_source` |
| 123 | column_assign | column: `location` |
| 147 | boolean_filter | Filters rows based on boolean condition |
| 113 | rename | Renames columns |
| 90 | astype | Converts column types |

### `13_reservations`

| Line | Operation | Details |
|------|-----------|---------|
| 67 | column_assign | column: `reservation_line_id` |
| 80 | column_assign | column: `reservation_number` |
| 83 | column_assign | column: `reservation_line_number` |
| 67 | astype | Converts column types |
| 79 | apply | Applies function to data |
| 80 | astype | Converts column types |
| 83 | astype | Converts column types |
| 141 | apply | Applies function to data |
| 147 | apply | Applies function to data |
| 80 | apply | Applies function to data |

### `04_enrich_po_line_items`

| Line | Operation | Details |
|------|-----------|---------|
| 64 | column_assign | column: `PO Line Item` |
| 65 | column_assign | column: `PO Line ID` |
| 83 | column_assign | column: `PO Line ID` |
| 86 | column_assign | column: `Requester` |
| 96 | column_assign | column: `PR Number` |
| 100 | column_assign | column: `PR Line` |
| 64 | astype | Converts column types |
| 93 | apply | Applies function to data |
| 94 | apply | Applies function to data |
| 100 | astype | Converts column types |

### `05_calculate_cost_impact`

| Line | Operation | Details |
|------|-----------|---------|
| 102 | column_assign | column: `Posting Type` |
| 110 | column_assign | column: `Posting Type` |
| 114 | column_assign | column: `Posting Date` |
| 118 | column_assign | column: `Unit Price` |
| 97 | rename | Renames columns |
| 105 | rename | Renames columns |
| 114 | to_datetime | Converts to datetime |
| 115 | sort_values | Sorts by column values |
| 124 | groupby | by: `PO Line ID` |
| 195 | sort_values | Sorts by column values |

### `06_calculate_grir`

| Line | Operation | Details |
|------|-----------|---------|
| 81 | column_assign | column: `Unit Price` |
| 124 | column_assign | column: `Posting Type` |
| 132 | column_assign | column: `Posting Type` |
| 137 | column_assign | column: `Posting Date` |
| 120 | rename | Renames columns |
| 128 | rename | Renames columns |
| 137 | to_datetime | Converts to datetime |
| 138 | sort_values | Sorts by column values |
| 143 | groupby | by: `PO Line ID` |

### `07_process_wbs`

| Line | Operation | Details |
|------|-----------|---------|
| 156 | column_assign | column: `wbs_number` |
| 197 | column_assign | column: `wbs_number` |
| 198 | column_assign | column: `sub_business_line_from_wbs` |
| 244 | column_assign | column: `location` |
| 313 | boolean_filter | Filters rows based on boolean condition |
| 155 | apply | Applies function to data |
| 166 | column_assign | column: `sub_business_lines` |
| 172 | column_assign | column: `sub_business_lines` |
| 196 | apply | Applies function to data |
| 202 | column_assign | column: `sub_business_line_mapped` |

### `06_prepare_po_line_items`

| Line | Operation | Details |
|------|-----------|---------|
| 80 | column_assign | column: `Total Cost Impact Qty` |
| 81 | column_assign | column: `Total Cost Impact Amount` |
| 181 | column_assign | column: `wbs_validated` |
| 206 | column_assign | column: `is_capex` |
| 77 | merge | on: `PO Line ID` |
| 80 | fillna | Fills null values |
| 81 | fillna | Fills null values |
| 105 | drop | cols: `Total Cost Impact Qty, Total Cost Impact Amount` |
| 115 | apply | Applies function to data |
| 141 | column_assign | column: `open_po_qty` |

### `07_prepare_po_transactions`

| Line | Operation | Details |
|------|-----------|---------|
| 60 | column_assign | column: `_date_str` |
| 65 | column_assign | column: `_seq` |
| 70 | column_assign | column: `transaction_id` |
| 119 | column_assign | column: `amount` |
| 81 | drop | cols: `_date_str, _seq` |
| 111 | column_assign | column: `cost_impact_qty` |
| 113 | column_assign | column: `cost_impact_amount` |
| 115 | column_assign | column: `quantity` |
| 105 | boolean_filter | Filters rows based on boolean condition |
| 56 | sort_values | Sorts by column values |

### `08_prepare_grir_exposures`

| Line | Operation | Details |
|------|-----------|---------|
| 65 | column_assign | column: `grir_qty` |
| 68 | column_assign | column: `grir_value` |
| 58 | boolean_filter | Filters rows based on boolean condition |
| 126 | boolean_filter | Filters rows based on boolean condition |

### `09_prepare_wbs_details`

| Line | Operation | Details |
|------|-----------|---------|
| 110 | column_assign | column: `sub_business_lines` |
| 102 | boolean_filter | Filters rows based on boolean condition |
| 110 | apply | Applies function to data |

### `10_prepare_reservations`

| Line | Operation | Details |
|------|-----------|---------|
| 93 | column_assign | column: `po_number` |
| 94 | column_assign | column: `po_line_number` |
| 99 | column_assign | column: `po_line_item_id` |
| 140 | column_assign | column: `asset_code` |
| 141 | column_assign | column: `asset_serial_number` |
| 70 | column_assign | column: `po_number` |
| 71 | column_assign | column: `po_line_number` |
| 72 | column_assign | column: `po_line_item_id` |
| 92 | apply | Applies function to data |
| 93 | apply | Applies function to data |
