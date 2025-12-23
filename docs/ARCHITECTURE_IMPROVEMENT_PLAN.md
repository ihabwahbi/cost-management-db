# Architecture Improvement Plan: Schema Unification & Data Layer Cleanup

> **Status**: Planning  
> **Created**: 2026-02-16  
> **Scope**: `cost-management-db` (ETL) + `cost-management` (Web App)  
> **Goal**: Eliminate schema duplication, move derivations to ETL, simplify app-layer calculations

---

## Table of Contents

- [1. Current Architecture Overview](#1-current-architecture-overview)
- [2. Problem Statement](#2-problem-statement)
- [3. Phase 0: Schema Unification via Symlinks](#3-phase-0-schema-unification-via-symlinks)
- [4. Phase 1: Add Pre-Computed Fields to ETL](#4-phase-1-add-pre-computed-fields-to-etl)
- [5. Phase 2: Simplify App-Layer P&L Calculations](#5-phase-2-simplify-app-layer-pl-calculations)
- [6. Phase 3: Create Database Views](#6-phase-3-create-database-views)
- [7. Phase 4: Eliminate Client-Side Data Transformation Duplication](#7-phase-4-eliminate-client-side-data-transformation-duplication)
- [8. Phase 5: Address Hardcoded Values](#8-phase-5-address-hardcoded-values)
- [9. Phase 6: ETL Pipeline Scheduling](#9-phase-6-etl-pipeline-scheduling)
- [10. Execution Order & Dependencies](#10-execution-order--dependencies)
- [11. Appendix A: Complete File Inventory](#11-appendix-a-complete-file-inventory)
- [12. Appendix B: All App-Layer Calculations Inventory](#12-appendix-b-all-app-layer-calculations-inventory)
- [13. Appendix C: ETL Pipeline Data Flow](#13-appendix-c-etl-pipeline-data-flow)
- [14. Appendix D: Schema Comparison](#14-appendix-d-schema-comparison)

---

## 1. Current Architecture Overview

### Two Separate Git Repositories

Both projects live side-by-side under `/workspace/projects/`:

```
/workspace/projects/
├── cost-management-db/          ← Standalone git repo (Python ETL + TypeScript imports)
│   ├── src/schema/              ← SOURCE OF TRUTH for 12 data table schemas
│   ├── src/imports/             ← 5 TypeScript import scripts (CSV → PostgreSQL)
│   ├── src/client.ts            ← Drizzle ORM client
│   ├── scripts/                 ← 16 Python pipeline scripts + config + validators
│   ├── data/raw/                ← Source CSV/Excel files (SAP exports)
│   ├── data/intermediate/       ← Cleaned/transformed data
│   ├── data/import-ready/       ← Final CSVs matching DB schema
│   ├── package.json             ← npm, name: @cost-mgmt/db
│   └── drizzle.config.ts        ← Points to dev_v3 schema
│
├── cost-management/             ← Separate git repo (pnpm monorepo)
│   ├── apps/web/                ← Next.js 14 frontend (TrueSpend)
│   ├── packages/api/            ← tRPC API + AI agent system
│   ├── packages/db/             ← Drizzle ORM database layer
│   │   ├── src/schema/          ← COPY of 12 data schemas + 7 webapp-only schemas
│   │   ├── src/client.ts        ← Drizzle client (with build-time fallback)
│   │   └── src/index.ts         ← Barrel export (re-exports all + drizzle-orm operators)
│   ├── pnpm-workspace.yaml      ← apps/*, packages/*, tools/*
│   └── package.json             ← Root: turbo + pnpm@10.16.1
```

### Database: PostgreSQL `dev_v3` Schema

Both projects point at the **same database** and **same schema** (`dev_v3`). 21 tables total:

| Table | Written By | Read By |
|-------|-----------|---------|
| `po_line_items` | ETL (upsert) | App (queries) |
| `po_transactions` | ETL (upsert) | App (queries) |
| `grir_exposures` | ETL (upsert) | App (queries) |
| `wbs_details` | ETL (upsert) | App (queries) |
| `sap_reservations` | ETL (upsert) | App (queries) |
| `po_mappings` | **Both** — ETL creates pre-mapping matches; App handles user CRUD | App |
| `pr_pre_mappings` | **Both** — ETL expires old; App handles user CRUD | App |
| `projects` | App only | App |
| `cost_breakdown` | App only | App |
| `forecast_versions` | App only | App |
| `budget_forecasts` | App only | App |
| `po_operations` | App only | App |
| `users` | App only | App |
| `pending_invites` | App only | App |
| `registration_attempts` | App only | App |
| `registration_audit_log` | App only | App |
| `webauthn_credentials` | App only | App |
| `webauthn_challenges` | App only | App |
| `agent_memories` | App only | App |
| `agent_memory_history` | App only | App |

### Current Schema Sync Mechanism

A Python script copies `.ts` schema files from `cost-management-db/src/schema/` to `cost-management/packages/db/src/schema/`:

- **[DELETED]** `scripts/validators/cross_project_schema.py` — replaced by bidirectional symlinks
- **Symlinks**: Each project owns some tables; the other gets symlinks. Both `index.ts` files export all tables.
- **Validation**: `bash scripts/check-schema-symlinks.sh` (in webapp project) auto-detects missing symlinks or index.ts exports
- **Webapp index.ts**: Manually maintained — exports all data schemas + webapp-only schemas

### ETL Pipeline (16 Scripts, 3 Stages)

```
data/raw/ → [Stage 1: Clean] → data/intermediate/ → [Stage 2: Transform] → data/intermediate/
→ [Stage 3: Prepare] → data/import-ready/ → [TypeScript Imports] → PostgreSQL (dev_v3)
```

**Stage 1 — Clean** (7 scripts): Filters, standardizes, maps vendor names/locations, consolidates dates
**Stage 2 — Transform** (4 scripts): Enriches PO data, calculates cost impact (Type 1/2 algorithm), calculates GRIR exposures, processes WBS
**Stage 3 — Prepare** (5 scripts): Maps columns to DB schema, calculates open PO values, generates transaction IDs, validates output

### What the ETL Pre-Computes and Stores

| Computed Field | Table | Formula | Computed In |
|---------------|-------|---------|-------------|
| `open_po_qty` | `po_line_items` | `ordered_qty - SUM(cost_impact_qty)`, 0 for CLOSED POs | `stage3_prepare/06_prepare_po_line_items.py:92-94` |
| `open_po_value` | `po_line_items` | `po_value_usd - SUM(cost_impact_amount)`, 0 for CLOSED POs | `stage3_prepare/06_prepare_po_line_items.py:96-98` |
| `fmt_po` | `po_line_items` | `True` when `vendor_category == "OPS"` | `stage3_prepare/06_prepare_po_line_items.py:148` |
| `wbs_validated` | `po_line_items` | `True` if `wbs_number` exists in `wbs_details` | `stage3_prepare/06_prepare_po_line_items.py:181` |
| `is_capex` | `po_line_items` | `True` if `wbs_number` starts with `"C."` | `stage3_prepare/06_prepare_po_line_items.py:206` |
| `cost_impact_qty` | `po_transactions` | Per-transaction cost impact (Type 1/2 algorithm) | `stage2_transform/05_calculate_cost_impact.py` |
| `cost_impact_amount` | `po_transactions` | Per-transaction cost impact amount | `stage2_transform/05_calculate_cost_impact.py` |
| `transaction_id` | `po_transactions` | `{po_line_id}-{type}-{YYYYMMDD}-{seq}` | `stage3_prepare/07_prepare_po_transactions.py:46-81` |
| `grir_qty` | `grir_exposures` | `cumulative_ir - cumulative_gr` | `stage2_transform/06_calculate_grir.py:168` |
| `grir_value` | `grir_exposures` | `grir_qty × unit_price` | `stage2_transform/06_calculate_grir.py:173` |
| `days_open` | `grir_exposures` | `snapshot_date - first_exposure_date` | `stage2_transform/06_calculate_grir.py:177` |
| `time_bucket` | `grir_exposures` | Categorized from `days_open` | `stage2_transform/06_calculate_grir.py:181` |
| `location` (PO) | `po_line_items` | Mapped from `plant_code` via `PLANT_CODE_TO_LOCATION` | `stage1_clean/01_po_line_items.py:103` |
| `location` (WBS) | `wbs_details` | Mapped from `ops_district` via `OPS_DISTRICT_TO_LOCATION` | `stage2_transform/07_process_wbs.py:244` |

---

## 2. Problem Statement

### 2.1 Schema Duplication

12 data schema files are **copied** from `cost-management-db` to `cost-management` via a Python script. This creates:
- Two copies of every schema file that can drift
- A pre-commit hook that only catches drift in the ETL project
- Manual `--sync` runs required after every schema change
- An auto-generated `index.ts` that must be regenerated

### 2.2 Reverse-Derivation of Cost Impact

The ETL stores `open_po_value = po_value_usd - SUM(cost_impact_amount)`. The app then **reverses** this to get the cost impact:

```typescript
// pl-calculations.ts:39 — reverse-engineers what the ETL already knew
const costImpactValue = Math.max(poValue - openValue, 0);
```

This `costImpactValue` derivation appears in **4 separate locations**:

| Location | File | Line |
|----------|------|------|
| `splitMappedAmount()` | `packages/api/src/utils/pl-calculations.ts` | 39 |
| `normalizeLineItem()` | `packages/api/src/utils/pl-calculations.ts` | 96 |
| Raw SQL | `packages/api/src/procedures/dashboard/get-timeline-budget.procedure.ts` | 74 |
| Raw SQL filter | `packages/api/src/procedures/dashboard/get-timeline-budget.procedure.ts` | 83 |

### 2.3 Inconsistent Fallback Logic

`splitMappedAmount()` is called from 5 procedures. Three of them have **inline pre-checks** that duplicate the function's internal fallback:

| Procedure | File | Pre-check? | Fallback mechanism |
|-----------|------|-----------|-------------------|
| `getPLMetrics` | `get-pl-metrics.procedure.ts:82-86` | **Yes** — checks `!mapping.poValueUsd` | Inline `FALLBACK_INVOICE_RATIO` multiplication before calling `splitMappedAmount` |
| `getPLTimeline` | `get-pl-timeline.procedure.ts:69-73` | **Yes** — checks `!mapping.poValueUsd` | Inline `FALLBACK_INVOICE_RATIO` multiplication before calling `splitMappedAmount` |
| `getProjectMetrics` | `get-project-metrics.procedure.ts:124-129,142-144` | **Yes** — two separate paths | Inline `FALLBACK_INVOICE_RATIO` multiplication before calling `splitMappedAmount` |
| `getFinancialControlMetrics` | `get-financial-control-metrics.procedure.ts:121` | **No** | Relies on `splitMappedAmount`'s internal fallback |
| `getPromiseDates` | `get-promise-dates.procedure.ts:54` | **No** (INNER JOIN) | Never triggers — only processes rows with data |

This means the same business question ("what's actual vs. future P&L?") gets **slightly different treatment** depending on which dashboard widget asks.

### 2.4 The FALLBACK_INVOICE_RATIO Magic Number

```typescript
// pl-calculations.ts:16
export const FALLBACK_INVOICE_RATIO = 0.6
```

A hardcoded constant assuming 60% actual / 40% future P&L split when no transaction data is available. Not configurable, not auditable, not documented as a business rule.

### 2.5 Duplicated Client-Side Data Transformation

Flat row construction (Project → PO → LineItem hierarchy) is implemented in **two separate places**:

- **Server-side**: `packages/api/src/procedures/operations/helpers/transform-to-flat-rows.ts`
- **Client-side**: `apps/web/components/cells/operations-table-cell/utils/data-transform.ts`

The `getMajorityValue()` function is also duplicated:
- Server: `packages/api/src/procedures/po-mapping/helpers/transform-to-wbs-flat-rows.ts:112-132`
- Client: `apps/web/components/cells/operations-table-cell/utils/data-transform.ts:86-107`

### 2.6 No Database Views or Pre-Aggregations

There are **zero** materialized views, database views, database functions, triggers, or stored procedures. Every aggregation is computed at query time — either in SQL via Drizzle or in TypeScript post-query. Multiple procedures perform the same 4-table join pattern:

```
po_line_items → po_mappings → cost_breakdown → projects
```

### 2.7 Other Issues

- **Burn rate hardcoded start date**: `get-project-metrics.procedure.ts:151` uses `new Date(2024, 0, 1)`
- **No ETL scheduling**: Pipeline is fully manual — run when new SAP exports arrive
- **Numeric strings**: Drizzle returns `numeric` columns as strings. Parsing happens inconsistently (sometimes in procedures, sometimes in client components)

---

## 3. Phase 0: Schema Unification via Symlinks

### 3.0 Why Symlinks Work Here

After analyzing all import patterns in both projects:

1. **Every schema file imports `_schema.ts` via relative sibling import** (`'./_schema'`)
2. **Cross-table FK references use relative sibling imports** (`'./po-line-items'`, `'./cost-breakdown'`, etc.)
3. **No schema file imports from outside its directory** — only `'drizzle-orm/pg-core'` for column types
4. **Both projects have identical `drizzle-orm@0.44.6`** and identical `tsconfig.json` (`moduleResolution: "bundler"`)
5. **The webapp has 7 additional schema files** (auth/agent) that don't exist in the ETL project — these stay as real files
6. **Each project's `index.ts` barrel is different by design** — ETL exports 12 data schemas, webapp exports 12 + 7 webapp-only

Symlinks resolve correctly because TypeScript/Node follows the symlink to the real file, then resolves relative imports from the real file's directory. Since all sibling files are also symlinked to the same source directory, the imports resolve identically.

### 3.1 Files to Symlink

Replace these 13 files in `cost-management/packages/db/src/schema/` with symlinks:

```
_schema.ts
budget-forecasts.ts
cost-breakdown.ts
forecast-versions.ts
grir-exposures.ts
po-line-items.ts
po-mappings.ts
po-operations.ts
po-transactions.ts
pr-pre-mappings.ts
projects.ts
sap-reservations.ts
wbs-details.ts
```

### 3.2 Files That Stay as Real Files in the Webapp

These are webapp-only and must NOT be symlinked:

```
index.ts              ← Different in each project (webapp includes auth/agent exports)
agent-memories.ts     ← Webapp-only
pending-invites.ts    ← Webapp-only
registration-attempts.ts    ← Webapp-only
registration-audit-log.ts  ← Webapp-only
users.ts              ← Webapp-only
webauthn-credentials.ts     ← Webapp-only
webauthn-challenges.ts      ← Webapp-only
```

### 3.3 Implementation Steps

#### Step 0.3.1: Create the symlinks

From `cost-management/packages/db/src/schema/`:

```bash
cd /workspace/projects/cost-management/packages/db/src/schema

# Remove the copied files
rm _schema.ts budget-forecasts.ts cost-breakdown.ts forecast-versions.ts \
   grir-exposures.ts po-line-items.ts po-mappings.ts po-operations.ts \
   po-transactions.ts pr-pre-mappings.ts projects.ts sap-reservations.ts \
   wbs-details.ts

# Create symlinks (relative path from webapp schema dir to ETL schema dir)
for f in _schema.ts budget-forecasts.ts cost-breakdown.ts forecast-versions.ts \
         grir-exposures.ts po-line-items.ts po-mappings.ts po-operations.ts \
         po-transactions.ts pr-pre-mappings.ts projects.ts sap-reservations.ts \
         wbs-details.ts; do
  ln -s "../../../../../../cost-management-db/src/schema/$f" "$f"
done
```

The relative path `../../../../../../cost-management-db/src/schema/` traverses:
```
schema/ → src/ → db/ → packages/ → cost-management/ → projects/ → cost-management-db/src/schema/
```

#### Step 0.3.2: Update the webapp's `index.ts`

Replace the auto-generated comment. The file at `cost-management/packages/db/src/schema/index.ts` becomes manually maintained:

```typescript
/**
 * Database schema definitions for dev_v3 schema
 *
 * Data schemas are symlinked from cost-management-db/src/schema/
 * Webapp-only schemas are owned by this project.
 */

export * from './_schema';

// Data schemas (symlinked from cost-management-db)
export * from './budget-forecasts';
export * from './cost-breakdown';
export * from './forecast-versions';
export * from './grir-exposures';
export * from './po-line-items';
export * from './po-mappings';
export * from './po-operations';
export * from './po-transactions';
export * from './pr-pre-mappings';
export * from './projects';
export * from './sap-reservations';
export * from './wbs-details';

// Webapp-only schemas (owned by this project)
export * from './agent-memories';
export * from './pending-invites';
export * from './registration-attempts';
export * from './registration-audit-log';
export * from './users';
export * from './webauthn-credentials';
export * from './webauthn-challenges';
```

#### Step 0.3.3: Remove the sync infrastructure from `cost-management-db`

1. **[DONE]** `scripts/validators/cross_project_schema.py` has been deleted
2. **[DONE]** The `cross-project-schema` pre-commit hook has been removed from `.pre-commit-config.yaml`
3. **[DONE]** `AGENTS.md` references updated — symlink validation is now via `bash scripts/check-schema-symlinks.sh` (in webapp project)

#### Step 0.3.4: Add a symlink validation check (optional)

Create a simple script in the webapp project to verify symlinks are valid:

```bash
#!/bin/bash
# cost-management/scripts/check-schema-symlinks.sh
SCHEMA_DIR="packages/db/src/schema"
EXPECTED_SYMLINKS=(
  _schema.ts budget-forecasts.ts cost-breakdown.ts forecast-versions.ts
  grir-exposures.ts po-line-items.ts po-mappings.ts po-operations.ts
  po-transactions.ts pr-pre-mappings.ts projects.ts sap-reservations.ts
  wbs-details.ts
)

for f in "${EXPECTED_SYMLINKS[@]}"; do
  if [ ! -L "$SCHEMA_DIR/$f" ]; then
    echo "ERROR: $SCHEMA_DIR/$f is not a symlink"
    exit 1
  fi
  if [ ! -e "$SCHEMA_DIR/$f" ]; then
    echo "ERROR: $SCHEMA_DIR/$f symlink is broken (target does not exist)"
    exit 1
  fi
done
echo "All schema symlinks are valid"
```

#### Step 0.3.5: Verify both projects build correctly

```bash
# In cost-management-db — verify import scripts resolve schema
npx tsx src/imports/po-line-items.ts --dry-run

# In cost-management — verify TypeScript compilation
pnpm run type-check
pnpm run build
```

### 3.4 Workflow After Symlinks

**Adding a new data schema table:**
1. Create the `.ts` file in `cost-management-db/src/schema/`
2. Export from `cost-management-db/src/schema/index.ts`
3. Create a symlink in `cost-management/packages/db/src/schema/`
4. Add the export to `cost-management/packages/db/src/schema/index.ts`
5. Detect drift: `npm run db:drift` (shows SQL needed, never applies)
6. Apply manually: `npm run db:drift:sql | psql "$DATABASE_URL"`

**Modifying an existing data schema:**
1. Edit the file in `cost-management-db/src/schema/` — the symlink means the webapp sees the change immediately
2. Detect drift: `npm run db:drift` (shows SQL needed, never applies)
3. Apply manually: `npm run db:drift:sql | psql "$DATABASE_URL"`

---

## 4. Phase 1: Add Pre-Computed Fields to ETL

### 4.1 New Columns on `po_line_items`

Add two columns to `cost-management-db/src/schema/po-line-items.ts` (which is the single source via symlink):

```typescript
// After line 69 (openPoValue):

// Total cost impact recognized (SUM of cost_impact_amount from transactions)
// Formula: po_value_usd - open_po_value (or 0 for CLOSED POs where both are forced to 0/full)
costImpactValue: numeric('cost_impact_value'),

// Proportion of PO value that has been received/invoiced [0.0 - 1.0]
// Formula: cost_impact_value / po_value_usd, NULL when po_value_usd = 0
costImpactPct: numeric('cost_impact_pct'),
```

### 4.2 Compute in ETL: `stage3_prepare/06_prepare_po_line_items.py`

Add computation in the `calculate_open_values()` function (after line 99):

```python
# After calculating open_po_qty and open_po_value...

# Calculate cost_impact_value = total cost impact recognized
# For closed POs: cost_impact_value = po_value_usd (fully received)
# For open POs: cost_impact_value = Total Cost Impact Amount
po_df.loc[already_closed, "cost_impact_value"] = po_df.loc[already_closed, "Purchase Value USD"]
po_df.loc[not_closed, "cost_impact_value"] = po_df.loc[not_closed, "Total Cost Impact Qty"].where(
    lambda x: False  # placeholder
)
# Actually use Total Cost Impact Amount (not Qty)
po_df.loc[not_closed, "cost_impact_value"] = po_df.loc[not_closed, "Total Cost Impact Amount"]

# Calculate cost_impact_pct = cost_impact_value / po_value_usd, clamped [0, 1]
has_po_value = po_df["Purchase Value USD"] > 0
po_df.loc[has_po_value, "cost_impact_pct"] = (
    po_df.loc[has_po_value, "cost_impact_value"]
    / po_df.loc[has_po_value, "Purchase Value USD"]
).clip(0, 1).round(6)
po_df.loc[~has_po_value, "cost_impact_pct"] = None

# For closed POs: always 1.0
po_df.loc[already_closed, "cost_impact_pct"] = 1.0
```

**Important**: The correct implementation should use the same `Total Cost Impact Amount` that's already computed from the `cost_agg` merge at line 65-77. The values are already in `po_df` after the merge.

### 4.3 Update `map_columns()` in the same file

In the `map_columns()` function, add after the existing `open_po_value` block (around line 143):

```python
# Add cost impact calculated columns
if "cost_impact_value" in po_df.columns:
    output_df["cost_impact_value"] = po_df["cost_impact_value"].round(2)
if "cost_impact_pct" in po_df.columns:
    output_df["cost_impact_pct"] = po_df["cost_impact_pct"].round(6)
```

### 4.4 Update `column_mappings.py`

In `scripts/config/column_mappings.py`, add to `PO_LINE_ITEMS_CALCULATED` (line 59-65):

```python
PO_LINE_ITEMS_CALCULATED = [
    "open_po_qty",
    "open_po_value",
    "fmt_po",
    "wbs_validated",
    "is_capex",
    "cost_impact_value",   # NEW: po_value_usd - open_po_value (total cost impact recognized)
    "cost_impact_pct",     # NEW: cost_impact_value / po_value_usd [0,1], NULL when po_value=0
]
```

### 4.5 Update the TypeScript import script

In `cost-management-db/src/imports/po-line-items.ts`, add to the `CsvRow` interface and the upsert column mapping:

```typescript
// In CsvRow interface:
cost_impact_value: string;
cost_impact_pct: string;

// In the upsert values mapping:
costImpactValue: row.cost_impact_value || null,
costImpactPct: row.cost_impact_pct || null,

// In the onConflictDoUpdate set:
costImpactValue: sql`EXCLUDED.cost_impact_value`,
costImpactPct: sql`EXCLUDED.cost_impact_pct`,
```

### 4.6 Apply schema and run pipeline

```bash
# Detect schema drift (symlink means webapp picks it up automatically)
cd /workspace/projects/cost-management-db
npm run db:drift          # Review the SQL changes
npm run db:drift:sql | psql "$DATABASE_URL"   # Apply manually

# Run ETL pipeline (only stage 3 needs re-running if data hasn't changed)
.venv/bin/python scripts/pipeline.py --stage3
npx tsx src/imports/po-line-items.ts
```

---

## 5. Phase 2: Simplify App-Layer P&L Calculations

### 5.1 Refactor `splitMappedAmount()` to Use `cost_impact_pct`

**File**: `cost-management/packages/api/src/utils/pl-calculations.ts`

Replace the current implementation (lines 28-64) with:

```typescript
/**
 * Fallback invoice ratio when actual invoice data unavailable.
 * Used to split mapped amounts into actual vs future.
 * TODO: Move to database configuration table for auditability.
 */
export const FALLBACK_INVOICE_RATIO = Number(process.env.FALLBACK_INVOICE_RATIO ?? 0.6);

/**
 * Split mapped amount into actual and future P&L impact.
 *
 * Uses pre-computed cost_impact_pct from the ETL pipeline.
 * Falls back to FALLBACK_INVOICE_RATIO when no data is available.
 *
 * @param mappedAmount - Total mapped amount from po_mappings
 * @param lineItem - PO line item with cost impact percentage (null if no line item data)
 */
export function splitMappedAmount(
  mappedAmount: number,
  lineItem: {
    costImpactPct: number | string | null;
  } | null
): { actual: number; future: number } {
  // No line item data at all — use fallback
  if (!lineItem || lineItem.costImpactPct === null || lineItem.costImpactPct === undefined) {
    return {
      actual: Math.round(mappedAmount * FALLBACK_INVOICE_RATIO * 100) / 100,
      future: Math.round(mappedAmount * (1 - FALLBACK_INVOICE_RATIO) * 100) / 100,
    };
  }

  const pct = Math.min(Math.max(Number(lineItem.costImpactPct), 0), 1);

  return {
    actual: Math.round(mappedAmount * pct * 100) / 100,
    future: Math.round(mappedAmount * (1 - pct) * 100) / 100,
  };
}
```

### 5.2 Remove `normalizeLineItem()` or Simplify

The `normalizeLineItem()` function (lines 72-101) exists to derive `costImpactValue` and `costImpactQty`. With the new columns, it can be simplified to pure type coercion:

```typescript
/**
 * Coerce Drizzle numeric string results to numbers.
 */
export function normalizeLineItem(raw: {
  id: string;
  poValueUsd: string | null;
  openPoValue: string | null;
  costImpactValue?: string | null;
  costImpactPct?: string | null;
  orderedQty?: string | null;
  openPoQty?: string | null;
}): {
  id: string;
  poValueUsd: number;
  openPoValue: number;
  costImpactValue: number;
  costImpactPct: number | null;
  orderedQty: number;
  openPoQty: number;
} {
  return {
    id: raw.id,
    poValueUsd: Number(raw.poValueUsd || 0),
    openPoValue: Number(raw.openPoValue || 0),
    costImpactValue: Number(raw.costImpactValue || 0),
    costImpactPct: raw.costImpactPct != null ? Number(raw.costImpactPct) : null,
    orderedQty: Number(raw.orderedQty || 0),
    openPoQty: Number(raw.openPoQty || 0),
  };
}
```

### 5.3 Remove Inline Fallback Pre-Checks from 3 Procedures

Each of these files has an inline check before calling `splitMappedAmount()` that duplicates the function's own fallback logic. Remove the pre-check and always call `splitMappedAmount()`:

#### `get-pl-metrics.procedure.ts` (lines 82-86)

**Before:**
```typescript
if (!mapping.poValueUsd) {
  const inferredActual = mappedAmount * FALLBACK_INVOICE_RATIO;
  actualPLImpact += inferredActual;
  futurePLImpact += Math.max(mappedAmount - inferredActual, 0);
} else {
  const { actual, future } = splitMappedAmount(mappedAmount, { ... });
```

**After:**
```typescript
const { actual, future } = splitMappedAmount(mappedAmount, mapping.costImpactPct != null ? {
  costImpactPct: mapping.costImpactPct,
} : null);
actualPLImpact += actual;
futurePLImpact += future;
```

Apply the same pattern to:
- `get-pl-timeline.procedure.ts` (lines 69-73)
- `get-project-metrics.procedure.ts` (lines 124-129 and 142-144)

Also update the SELECT clauses in these procedures to fetch `costImpactPct` instead of `poValueUsd` + `openPoValue` (where the only purpose was to derive the percentage).

### 5.4 Update `get-timeline-budget.procedure.ts`

Replace the reverse-derivation SQL (line 74):

**Before:**
```sql
COALESCE(po_value_usd::numeric, 0) - COALESCE(open_po_value::numeric, 0)
```

**After:**
```sql
COALESCE(cost_impact_value::numeric, 0)
```

And the filter (line 83):

**Before:**
```sql
COALESCE(open_po_value::numeric, 0) < COALESCE(po_value_usd::numeric, 0)
```

**After:**
```sql
COALESCE(cost_impact_value::numeric, 0) > 0
```

### 5.5 Update All Procedures That SELECT `poValueUsd` + `openPoValue` Only for Derivation

Review each procedure. Where `poValueUsd` and `openPoValue` are selected ONLY to compute `costImpactValue` or `costImpactPercentage`, replace with `costImpactPct` and/or `costImpactValue` from the database.

Procedures to update:
- `get-pl-metrics.procedure.ts` — SELECT clause (line 67-68)
- `get-pl-timeline.procedure.ts` — SELECT clause
- `get-project-metrics.procedure.ts` — SELECT clause
- `get-financial-control-metrics.procedure.ts` — SELECT clause
- `get-promise-dates.procedure.ts` — SELECT clause
- `get-po-summary.procedure.ts` — ratio calculation (lines 107-119)
- `get-timeline-budget.procedure.ts` — SQL expression (line 74)

---

## 6. Phase 3: Create Database Views

### 6.1 View: `v_project_financials`

Consolidates what `getKPIMetrics`, `getProjectMetrics`, and `getPLMetrics` compute independently:

```sql
CREATE VIEW dev_v3.v_project_financials AS
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
GROUP BY p.id, p.name, p.sub_business_line, budget.total_budget;
```

### 6.2 View: `v_po_mapping_detail`

Pre-joins the 4-table pattern used by 6+ procedures:

```sql
CREATE VIEW dev_v3.v_po_mapping_detail AS
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
LEFT JOIN dev_v3.po_line_items pli ON pli.id = pm.po_line_item_id;
```

### 6.3 How to Create the Views

Add these as SQL migrations. In `cost-management/packages/db/`, create a migration file or apply via `npm run db:drift:sql | psql "$DATABASE_URL"` after defining them in Drizzle schema files.

Alternatively, if Drizzle ORM supports views in your version, define them in a schema file. Otherwise, create them via a manual migration SQL file.

### 6.4 Why Regular Views (Not Materialized)

- Your data changes both via ETL (batch, manual) and via app (real-time user actions like creating mappings)
- Regular views are always current with both data sources
- Materialized views would require refresh management and could show stale data for user-created mappings
- With proper indexes on the underlying tables (which already exist), view query performance will be adequate for your data scale

---

## 7. Phase 4: Eliminate Client-Side Data Transformation Duplication

### 7.1 Remove `data-transform.ts` from Operations Table Cell

**File to audit**: `apps/web/components/cells/operations-table-cell/utils/data-transform.ts`

This file duplicates server-side logic from `packages/api/src/procedures/operations/helpers/transform-to-flat-rows.ts`. The server-side procedure should return data in the exact shape the table component needs.

**Action**: Move all data shaping into the tRPC procedure. The client component should only handle:
- Column formatting (`formatCurrency`, date formatting)
- UI state (expanded rows, selection, keyboard navigation)
- Display labels and status badges

### 7.2 Move Status Derivation to Server

**Client files with status logic:**
- `apps/web/components/cells/operations-table-cell/utils/derive-status.ts`
- `apps/web/components/cells/operations-table-cell/hooks/helpers/map-server-row.ts` (lines 33-60)

**Action**: Add a `simplifiedStatus` field to the server response in `transform-to-flat-rows.ts`. The status derivation logic (priority-based from receipt/approval/GTS/isActive/pendingCancel) should execute once on the server, not re-derived on the client.

### 7.3 Consolidate `getMajorityValue()`

**Current duplicated implementations:**
- `packages/api/src/procedures/po-mapping/helpers/transform-to-wbs-flat-rows.ts:112-132`
- `apps/web/components/cells/operations-table-cell/utils/data-transform.ts:86-107`

**Action**: Extract to a shared utility in `packages/api/src/utils/data-utils.ts` and use it from both server-side helpers. Remove the client-side copy.

### 7.4 Remove Client-Side `build-flat-rows.ts`

**File**: `apps/web/components/cells/operations-table-cell/hooks/helpers/build-flat-rows.ts`

This constructs project-level flat rows with financial metrics (totalCostHit, budgetUtilizationPercent, etc.) from server data. These calculations should be part of the server response.

### 7.5 Ensure Numeric Values Are Numbers, Not Strings

Drizzle returns `numeric` columns as strings. Currently, `parseFloat()` calls are scattered across both server and client code. 

**Action**: Create a standard numeric coercion step in each tRPC procedure that returns numeric data. All `numeric` fields should be converted to `number` before leaving the procedure. This eliminates string-to-number parsing in client code entirely.

---

## 8. Phase 5: Address Hardcoded Values

### 8.1 Burn Rate Start Date

**Current** (`get-project-metrics.procedure.ts:151`):
```typescript
const startDate = new Date(2024, 0, 1); // HARDCODED
```

**Fix**: Add `start_date` column to the `projects` table (DATE, nullable). Fall back to the earliest `po_creation_date` for the project:

```typescript
const startDate = project.startDate
  ? new Date(project.startDate)
  : new Date(earliestPoDate || '2024-01-01');
```

### 8.2 Timeline Extension

**Current** (`generate-pl-timeline.helper.ts:44`): Extends timeline 3 months into the future.

**Fix**: Keep as-is but extract to a named constant:
```typescript
const TIMELINE_FUTURE_MONTHS = 3;
```

### 8.3 Promise Dates Limit

**Current** (`get-promise-dates.procedure.ts:77`): `.slice(0, 10)` hardcoded.

**Fix**: Make it an input parameter with a default:
```typescript
input: z.object({
  projectId: z.string().uuid(),
  limit: z.number().min(1).max(50).default(10),
})
```

---

## 9. Phase 6: ETL Pipeline Scheduling

### 9.1 Document Current Cadence

Create a `PIPELINE_OPERATIONS.md` that documents:
- When to run (when new SAP exports arrive)
- Full command sequence
- How to verify results
- Impact on downstream data (GRIR `snapshot_date` accuracy, `wbs_validated` staleness)

### 9.2 Add Scheduling (When Ready)

Options:
- **GitHub Actions scheduled workflow**: `cron: '0 6 * * 1'` (weekly Monday 6 AM)
- **Local cron job**: On the machine where raw data files are deposited
- **Manual with reminders**: Calendar reminder to run weekly

This is lowest priority — get Phases 0–4 done first.

---

## 10. Execution Order & Dependencies

```
Phase 0 (Symlinks)                  ← Do FIRST, no code logic changes
    │
    ├── Phase 1 (ETL columns)       ← Schema change + ETL Python code
    │       │
    │       └── Phase 2 (App P&L)   ← Depends on Phase 1 columns existing in DB
    │               │
    │               └── Phase 3 (Views)  ← Can overlap with Phase 2
    │
    └── Phase 4 (Client cleanup)    ← Independent of Phases 1-3
    
Phase 5 (Hardcoded values)          ← Independent, do anytime
Phase 6 (Scheduling)                ← Last, when everything else is stable
```

### Estimated Effort

| Phase | Effort | Risk | Dependencies |
|-------|--------|------|-------------|
| **Phase 0** — Symlinks | 1-2 hours | Low | None |
| **Phase 1** — ETL columns | 2-3 hours | Low | Phase 0 |
| **Phase 2** — App P&L simplification | 4-6 hours | Medium | Phase 1 |
| **Phase 3** — Database views | 3-4 hours | Low-Medium | Phase 1 |
| **Phase 4** — Client cleanup | 3-4 hours | Medium | None |
| **Phase 5** — Hardcoded values | 1-2 hours | Low | None |
| **Phase 6** — Scheduling | 2-3 hours | Low | All above |

**Total: ~16-24 hours**

---

## 11. Appendix A: Complete File Inventory

### ETL Project (`cost-management-db`)

#### Schema Files (14)
```
src/schema/_schema.ts
src/schema/index.ts
src/schema/budget-forecasts.ts
src/schema/cost-breakdown.ts
src/schema/forecast-versions.ts
src/schema/grir-exposures.ts
src/schema/po-line-items.ts
src/schema/po-mappings.ts
src/schema/po-operations.ts
src/schema/po-transactions.ts
src/schema/pr-pre-mappings.ts
src/schema/projects.ts
src/schema/sap-reservations.ts
src/schema/wbs-details.ts
```

#### Pipeline Scripts (16)
```
scripts/pipeline.py                                    # Orchestrator
scripts/config/column_mappings.py                      # Central config (308 lines)
scripts/stage1_clean/01_po_line_items.py               # Clean PO data
scripts/stage1_clean/02_gr_postings.py                 # Clean GR data
scripts/stage1_clean/03_ir_postings.py                 # Clean IR data
scripts/stage1_clean/10_wbs_from_projects.py           # Clean WBS (projects)
scripts/stage1_clean/11_wbs_from_operations.py         # Clean WBS (operations)
scripts/stage1_clean/12_wbs_from_ops_activities.py     # Clean WBS (ops activities)
scripts/stage1_clean/13_reservations.py                # Clean SAP reservations
scripts/stage2_transform/04_enrich_po_line_items.py    # Enrich from PO details report
scripts/stage2_transform/05_calculate_cost_impact.py   # Type 1/2 cost impact algorithm
scripts/stage2_transform/06_calculate_grir.py          # GRIR exposure calculation
scripts/stage2_transform/07_process_wbs.py             # Merge WBS sources, parse SBL
scripts/stage3_prepare/06_prepare_po_line_items.py     # Map columns, calculate open values
scripts/stage3_prepare/07_prepare_po_transactions.py   # Generate transaction IDs
scripts/stage3_prepare/08_prepare_grir_exposures.py    # Map GRIR columns
scripts/stage3_prepare/09_prepare_wbs_details.py       # Deduplicate, JSON→PG array
scripts/stage3_prepare/10_prepare_reservations.py      # Extract PO/asset info
```

#### TypeScript Import Scripts (5)
```
src/imports/po-line-items.ts       # Upsert on po_line_id, soft delete, PR pre-mapping match
src/imports/po-transactions.ts     # Upsert on transaction_id, orphan handling
src/imports/grir-exposures.ts      # Upsert on (po_line_item_id, snapshot_date)
src/imports/wbs-details.ts         # Upsert on wbs_number (varchar PK)
src/imports/sap-reservations.ts    # Upsert on reservation_line_id, orphan analysis
```

#### Sync Script [DELETED — replaced by symlinks]
```
# cross_project_schema.py has been deleted.
# Schema sync is now handled by bidirectional symlinks + check-schema-symlinks.sh (in webapp project).
```

### Web App Project (`cost-management`)

#### Database Package Schema (21 files — 13 symlinked + 8 real after Phase 0)
```
packages/db/src/schema/_schema.ts               ← SYMLINK
packages/db/src/schema/index.ts                  ← REAL (different from ETL)
packages/db/src/schema/budget-forecasts.ts       ← SYMLINK
packages/db/src/schema/cost-breakdown.ts         ← SYMLINK
packages/db/src/schema/forecast-versions.ts      ← SYMLINK
packages/db/src/schema/grir-exposures.ts         ← SYMLINK
packages/db/src/schema/po-line-items.ts          ← SYMLINK
packages/db/src/schema/po-mappings.ts            ← SYMLINK
packages/db/src/schema/po-operations.ts          ← SYMLINK
packages/db/src/schema/po-transactions.ts        ← SYMLINK
packages/db/src/schema/pr-pre-mappings.ts        ← SYMLINK
packages/db/src/schema/projects.ts               ← SYMLINK
packages/db/src/schema/sap-reservations.ts       ← SYMLINK
packages/db/src/schema/wbs-details.ts            ← SYMLINK
packages/db/src/schema/agent-memories.ts         ← REAL (webapp-only)
packages/db/src/schema/pending-invites.ts        ← REAL (webapp-only)
packages/db/src/schema/registration-attempts.ts  ← REAL (webapp-only)
packages/db/src/schema/registration-audit-log.ts ← REAL (webapp-only)
packages/db/src/schema/users.ts                  ← REAL (webapp-only)
packages/db/src/schema/webauthn-credentials.ts   ← REAL (webapp-only)
packages/db/src/schema/webauthn-challenges.ts    ← REAL (webapp-only)
```

#### P&L Calculations (to be refactored in Phase 2)
```
packages/api/src/utils/pl-calculations.ts
```

#### Dashboard Procedures (11 + 1 helper — to be simplified in Phases 2-3)
```
packages/api/src/procedures/dashboard/dashboard.router.ts
packages/api/src/procedures/dashboard/get-financial-control-metrics.procedure.ts
packages/api/src/procedures/dashboard/get-kpi-metrics.procedure.ts
packages/api/src/procedures/dashboard/get-pl-metrics.procedure.ts
packages/api/src/procedures/dashboard/get-pl-timeline.procedure.ts
packages/api/src/procedures/dashboard/get-project-category-breakdown.procedure.ts
packages/api/src/procedures/dashboard/get-project-details.procedure.ts
packages/api/src/procedures/dashboard/get-project-hierarchical-breakdown.procedure.ts
packages/api/src/procedures/dashboard/get-project-metrics.procedure.ts
packages/api/src/procedures/dashboard/get-promise-dates.procedure.ts
packages/api/src/procedures/dashboard/get-timeline-budget.procedure.ts
packages/api/src/procedures/dashboard/helpers/generate-pl-timeline.helper.ts
```

#### PO-Mapping Procedures (11 + 2 helpers)
```
packages/api/src/procedures/po-mapping/po-mapping.router.ts
packages/api/src/procedures/po-mapping/clear-mappings.procedure.ts
packages/api/src/procedures/po-mapping/create-mapping.procedure.ts
packages/api/src/procedures/po-mapping/find-matching-cost-breakdown.procedure.ts
packages/api/src/procedures/po-mapping/get-existing-mappings.procedure.ts
packages/api/src/procedures/po-mapping/get-po-summary.procedure.ts
packages/api/src/procedures/po-mapping/get-pos-flat-rows.procedure.ts
packages/api/src/procedures/po-mapping/get-projects.procedure.ts
packages/api/src/procedures/po-mapping/get-spend-sub-categories.procedure.ts
packages/api/src/procedures/po-mapping/get-spend-types.procedure.ts
packages/api/src/procedures/po-mapping/update-mapping.procedure.ts
packages/api/src/procedures/po-mapping/helpers/build-po-filters.ts
packages/api/src/procedures/po-mapping/helpers/transform-to-wbs-flat-rows.ts
```

#### Operations Procedures (9 + 1 helper — client-side duplication in Phase 4)
```
packages/api/src/procedures/operations/operations.router.ts
packages/api/src/procedures/operations/bulk-flag-cancellation.procedure.ts
packages/api/src/procedures/operations/bulk-update-rdd.procedure.ts
packages/api/src/procedures/operations/delete-pending-operation.procedure.ts
packages/api/src/procedures/operations/get-operations-optimized.procedure.ts
packages/api/src/procedures/operations/get-project-aggregations.procedure.ts
packages/api/src/procedures/operations/get-project-list.procedure.ts
packages/api/src/procedures/operations/update-quantity.procedure.ts
packages/api/src/procedures/operations/update-rdd.procedure.ts
packages/api/src/procedures/operations/helpers/transform-to-flat-rows.ts
```

#### Agent Tool Procedures (5)
```
packages/api/src/procedures/agent-tools/agent-tools.router.ts
packages/api/src/procedures/agent-tools/get-cost-forecast.procedure.ts
packages/api/src/procedures/agent-tools/get-spend-summary.procedure.ts
packages/api/src/procedures/agent-tools/get-top-pos.procedure.ts
packages/api/src/procedures/agent-tools/search-pos.procedure.ts
```

#### Client-Side Files with Data Calculations (to be cleaned in Phase 4)
```
apps/web/components/cells/operations-table-cell/utils/data-transform.ts
apps/web/components/cells/operations-table-cell/utils/derive-status.ts
apps/web/components/cells/operations-table-cell/hooks/helpers/build-flat-rows.ts
apps/web/components/cells/operations-table-cell/hooks/helpers/map-server-row.ts
apps/web/hooks/use-forecast-calculations.ts
apps/web/lib/budget-utils.ts
apps/web/lib/version-utils.ts
apps/web/lib/version-comparison-utils.ts
```

---

## 12. Appendix B: All App-Layer Calculations Inventory

### Core Financial Derivations (repeated across multiple procedures)

| Calculation | Where Used | Current Logic | After Phase 2 |
|-------------|-----------|---------------|----------------|
| `costImpactValue` | `pl-calculations.ts:39,96`, `get-timeline-budget:74` | `poValueUsd - openPoValue` | Read `cost_impact_value` from DB |
| `costImpactPercentage` | `pl-calculations.ts:58` | `costImpactValue / poValueUsd` | Read `cost_impact_pct` from DB |
| Actual/Future P&L split | `splitMappedAmount()` in 5 procedures | `mappedAmount × costImpactPercentage` | `mappedAmount × cost_impact_pct` |
| Fallback 60/40 split | `pl-calculations.ts:42-54`, inline in 3 procedures | `FALLBACK_INVOICE_RATIO = 0.6` | Single path through `splitMappedAmount()` |
| Variance | `get-kpi-metrics:54`, `get-project-metrics:147` | `budget - actual` | Same (stays in app) |
| Utilization % | `get-project-metrics:149`, hierarchy builder | `actual / budget × 100` | Same (stays in app) |
| Burn Rate | `get-project-metrics:151-153` | `actualSpend / monthsElapsed` (hardcoded start) | Dynamic start date from DB |

### Aggregation Patterns

| Pattern | Procedures | Current | After Phase 3 |
|---------|-----------|---------|---------------|
| Budget total | `getKPIMetrics`, `getPLMetrics`, `getProjectMetrics`, `getFinancialControl`, `getTimelineBudget` | SQL `SUM(forecastedCost)` with version lookup | `SELECT total_budget FROM v_project_financials` |
| Committed total | Same 5 procedures | SQL `SUM(mappedAmount)` | `SELECT total_committed FROM v_project_financials` |
| 4-table join (PO→mapping→cost→project) | 6+ procedures | Repeated Drizzle query builder | `SELECT FROM v_po_mapping_detail` |

### Calculations That MUST Stay in the App

These depend on user-created data (mappings, forecasts, operations) that don't exist at ETL time:

| Calculation | Why It Stays |
|-------------|-------------|
| `splitMappedAmount()` | Depends on `po_mappings.mapped_amount` — user-created |
| Budget vs. actual variance | Depends on `budget_forecasts.forecasted_cost` — user-created |
| P&L timeline monthly bucketing | Depends on mappings + delivery dates |
| 4-level hierarchy construction | Depends on project/cost-breakdown structure — user-defined |
| Version comparison deltas | Depends on forecast versions — user-created |
| Operations aggregations | Depends on `po_operations` — user-created |
| Forecast value priority cascade | User changes → previous forecast → baseline |

---

## 13. Appendix C: ETL Pipeline Data Flow

```
data/raw/po line items.csv
    ↓ [01_po_line_items.py] Filter valuation classes, NIS levels, map vendors/locations
data/intermediate/po_line_items.csv
    ↓ [04_enrich_po_line_items.py] Add PR Number, Requester from po details report
data/intermediate/po_line_items.csv (enriched)
    ↓ [06_prepare_po_line_items.py] Calculate open values + NEW: cost_impact_value, cost_impact_pct
data/import-ready/po_line_items.csv → [po-line-items.ts] → po_line_items table

data/raw/gr table.csv + po_line_items
    ↓ [02_gr_postings.py] Filter zero qty, calculate GR Amount via unit price
data/intermediate/gr_postings.csv

data/raw/invoice table.csv + po_line_items
    ↓ [03_ir_postings.py] Calculate Invoice Amount via unit price
data/intermediate/ir_postings.csv

data/intermediate/{po_line_items, gr_postings, ir_postings}.csv
    ↓ [05_calculate_cost_impact.py] Type 1/2 classification, chronological GR/IR algorithm
data/intermediate/cost_impact.csv
    ↓ [07_prepare_po_transactions.py] Generate transaction_id, map columns
data/import-ready/po_transactions.csv → [po-transactions.ts] → po_transactions table

data/intermediate/{po_line_items, gr_postings, ir_postings}.csv
    ↓ [06_calculate_grir.py] Type 1 only, non-closed, IR > GR exposure tracking
data/intermediate/grir_exposures.csv
    ↓ [08_prepare_grir_exposures.py] Map columns
data/import-ready/grir_exposures.csv → [grir-exposures.ts] → grir_exposures table

data/raw/fdp/{Project,Operation,OpsActivity}Dashboard_Export_*.xlsx
    ↓ [10,11,12_wbs_from_*.py] Extract WBS, map locations, parse SBL codes
data/intermediate/wbs_from_{projects,operations,ops_activities}.csv
    ↓ [07_process_wbs.py] Merge, validate format, map locations
data/intermediate/wbs_processed.csv
    ↓ [09_prepare_wbs_details.py] Deduplicate, JSON→PG array
data/import-ready/wbs_details.csv → [wbs-details.ts] → wbs_details table

data/raw/reservations/Data Table - Open Reservation - *.xlsx
    ↓ [13_reservations.py] Filter business lines, split IDs, normalize PO Line IDs
data/intermediate/reservations.csv
    ↓ [10_prepare_reservations.py] Extract PO info, asset info, map columns
data/import-ready/sap_reservations.csv → [sap-reservations.ts] → sap_reservations table
```

---

## 14. Appendix D: Schema Comparison

### Files Shared Between Projects (13 — will become symlinks)

All 13 files listed in Phase 0 Section 3.1 are currently **byte-identical** between the two projects (verified via SHA-256 hash in the sync script).

### `index.ts` Differences

**ETL** (`cost-management-db/src/schema/index.ts`):
- Hand-maintained
- Exports only 12 data schemas + `_schema`
- 28 lines

**Webapp** (`cost-management/packages/db/src/schema/index.ts`):
- Manually maintained (previously auto-generated by the now-deleted `cross_project_schema.py`)
- Exports 12 data schemas + 7 webapp-only schemas
- 32 lines

### Webapp-Only Tables (7 files, not in ETL)

| File | Table(s) | Purpose |
|------|----------|---------|
| `agent-memories.ts` | `agent_memories`, `agent_memory_history` | AI agent long-term memory with vector embeddings |
| `pending-invites.ts` | `pending_invites` | Admin registration invitations |
| `registration-attempts.ts` | `registration_attempts` | Magic link verification |
| `registration-audit-log.ts` | `registration_audit_log` | Security audit trail |
| `users.ts` | `users` | User accounts with TOTP |
| `webauthn-credentials.ts` | `webauthn_credentials` | Passkey storage |
| `webauthn-challenges.ts` | `webauthn_challenges` | Temporary WebAuthn challenges |

### Both Projects' Drizzle Configuration

| Aspect | ETL | Webapp |
|--------|-----|--------|
| `drizzle-orm` | `0.44.6` | `0.44.6` |
| `drizzle-kit` | `0.31.5` | `0.31.5` |
| Schema filter | `['dev_v3']` | `['dev_v3']` |
| `moduleResolution` | `bundler` | `bundler` |
| Package name | `@cost-mgmt/db` | `@cost-mgmt/db` |
| Package manager | npm | pnpm (workspace) |
