# Pipeline Operations Guide

Operational runbook for the cost-management-db ETL pipeline.

---

## When to Run

Run the full pipeline when **new SAP export files arrive** in `data/raw/`. The pipeline is
currently triggered manually. A weekly Monday cadence (before team stand-up) is recommended
when data arrives on a regular schedule.

### Data Staleness Indicators

| Signal | Meaning |
|--------|---------|
| GRIR `snapshot_date` > 7 days old | Exposure figures may be stale |
| `wbs_validated` column has NULLs | WBS mapping hasn't run since new POs appeared |
| `cost_impact_pct` is NULL for open POs | ETL hasn't run since those POs were created |

---

## Full Run Command Sequence

```bash
# 1. Activate the virtual environment
cd /workspace/projects/cost-management-db

# 2. Run the full ETL pipeline (stages 1-3)
.venv/bin/python scripts/pipeline.py

# 3. Import into the database (all 5 tables)
npx tsx src/imports/po-line-items.ts
npx tsx src/imports/po-transactions.ts
npx tsx src/imports/grir-exposures.ts
npx tsx src/imports/wbs-details.ts
npx tsx src/imports/sap-reservations.ts

# 4. Verify schema matches (if schema changed)
npm run db:drift          # Shows SQL needed (never applies)
# Apply any drift SQL manually via psql or database MCP tool
```

### Partial Runs

If only specific data changed (e.g., only PO exports updated):

```bash
# Re-run from stage 3 only (fastest — skip clean/transform if raw data hasn't changed)
.venv/bin/python scripts/pipeline.py --stage3

# Then import only the affected table
npx tsx src/imports/po-line-items.ts
```

---

## Verification Checklist

After each pipeline run, verify:

```bash
# 1. Check import-ready CSVs were generated
ls -la data/import-ready/

# 2. Validate output schemas match lock file
.venv/bin/python scripts/validators/schema_lock.py --check

# 3. Run business rule tests
.venv/bin/pytest tests/contracts/test_business_rules.py -v

# 4. Spot-check key metrics via Drizzle Studio
npm run db:studio
```

### Key Columns to Verify

| Table | Column | Expected |
|-------|--------|----------|
| `po_line_items` | `cost_impact_pct` | 0.0-1.0 for open POs; 1.0 for closed POs; NULL when `po_value_usd = 0` |
| `po_line_items` | `cost_impact_value` | >= 0; equals `po_value_usd` for closed POs |
| `po_line_items` | `open_po_value` | >= 0; 0 for closed POs |
| `grir_exposures` | `snapshot_date` | Should be recent (within last pipeline run) |
| `wbs_details` | `wbs_number` | No duplicates |

---

## Pipeline Stages

| Stage | Scripts | Input | Output |
|-------|---------|-------|--------|
| **Stage 1: Clean** | `01`-`03`, `10`-`13` | `data/raw/` | `data/intermediate/` |
| **Stage 2: Transform** | `04`-`07` | `data/intermediate/` | `data/intermediate/` |
| **Stage 3: Prepare** | `06`-`10` | `data/intermediate/` | `data/import-ready/` |

### Import Scripts

| Script | Target Table | Upsert Key | Notes |
|--------|-------------|------------|-------|
| `po-line-items.ts` | `po_line_items` | `po_line_id` | Soft-deletes missing rows, matches PR pre-mappings |
| `po-transactions.ts` | `po_transactions` | `transaction_id` | Handles orphaned transactions |
| `grir-exposures.ts` | `grir_exposures` | `(po_line_item_id, snapshot_date)` | Composite key |
| `wbs-details.ts` | `wbs_details` | `wbs_number` | VARCHAR primary key |
| `sap-reservations.ts` | `sap_reservations` | `reservation_line_id` | Orphan analysis logging |

---

## Downstream Impact

Changes to `po_line_items` data affect:

- **Dashboard P&L metrics** — via `cost_impact_pct` and `cost_impact_value` columns
- **Financial control matrix** — via `cost_impact_pct`
- **Promise dates** — via `expected_delivery_date`
- **Timeline budget** — via `cost_impact_value`
- **PO summary** — via `cost_impact_value` and `cost_impact_pct`
- **Operations table** — via line item status fields

Changes to `grir_exposures` data affect:
- GRIR exposure reports (snapshot-based)

Changes to `wbs_details` data affect:
- WBS-based PO grouping in the mapping table
- WBS validation flags on PO line items

---

## Future: Automated Scheduling

When ready, add one of:

| Method | Config | Notes |
|--------|--------|-------|
| GitHub Actions | `cron: '0 6 * * 1'` | Weekly Monday 6 AM UTC |
| Local cron | `0 6 * * 1 /path/to/run-pipeline.sh` | Requires data host access |
| Manual + reminder | Calendar event | Current approach |

A GitHub Actions workflow would look like:

```yaml
name: ETL Pipeline
on:
  schedule:
    - cron: '0 6 * * 1'  # Weekly Monday 6 AM UTC
  workflow_dispatch:       # Manual trigger

jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: pip install -r requirements.txt
      - run: npm ci
      - run: python scripts/pipeline.py
      - run: |
          npx tsx src/imports/po-line-items.ts
          npx tsx src/imports/po-transactions.ts
          npx tsx src/imports/grir-exposures.ts
          npx tsx src/imports/wbs-details.ts
          npx tsx src/imports/sap-reservations.ts
    env:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
```
