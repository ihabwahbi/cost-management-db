# Handoff Document: Cost Management Database

**Date:** November 26, 2025  
**Status:** Pausing for data source migration

---

## 1. Project Overview

This project creates an isolated PostgreSQL schema (`dev_v3`) for cost management data using Drizzle ORM. The goal is to track PO (Purchase Order) transactions and determine when costs are recognized (hit the P&L).

### Environment
- **Database:** Azure PostgreSQL (shared with production)
- **Development Schema:** `dev_v3` (isolated, safe to modify)
- **Previous Schema:** `dev_v2` (preserved, not modified)
- **Production Schema:** `public` (never touch)
- **ORM:** Drizzle ORM with TypeScript

---

## 2. Database Schema Created

### Schema Location: `src/schema/`

| File | Table | Description |
|------|-------|-------------|
| `_schema.ts` | - | Shared `devV3Schema` instance |
| `projects.ts` | `projects` | Project master data |
| `wbs-details.ts` | `wbs_details` | WBS reference data |
| `pos.ts` | `pos` | Purchase Order headers |
| `po-line-items.ts` | `po_line_items` | PO line item details |
| `po-mappings.ts` | `po_mappings` | PO to cost breakdown mappings |
| `po-operations.ts` | `po_operations` | PO operation tracking |
| `po-transactions.ts` | `po_transactions` | GR/Invoice transactions with cost recognition |
| `sap-reservations.ts` | `sap_reservations` | SAP reservation data |
| `cost-breakdown.ts` | `cost_breakdown` | Cost breakdown structure |
| `forecast-versions.ts` | `forecast_versions` | Forecast version tracking |
| `budget-forecasts.ts` | `budget_forecasts` | Budget forecast data |

### Key Schema: `po_transactions`

```typescript
poTransactions = devV3Schema.table('po_transactions', {
  id: uuid('id').primaryKey().defaultRandom(),
  poLineItemId: uuid('po_line_item_id').notNull().references(() => poLineItems.id),
  transactionType: varchar('transaction_type').notNull(),  // 'GR' or 'Invoice'
  postingDate: date('posting_date').notNull(),
  quantity: numeric('quantity').notNull().default('0'),
  amount: numeric('amount').notNull().default('0'),
  costRecognizedQty: numeric('cost_recognized_qty').notNull().default('0'),  // NEW
  isCostRecognized: boolean('is_cost_recognized').notNull().default(false),
  referenceNumber: varchar('reference_number'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
});
```

---

## 3. Data Pipeline Created

### Directory Structure

```
data/
├── raw/                              # Original source files (untouched)
│   ├── gr table.csv                  # Goods Receipt data
│   ├── invoice table.csv             # Invoice data
│   └── po line items.csv             # PO line item master data
│
├── intermediate/                     # Cleaned/enriched data
│   ├── gr_cleaned.csv               # Cleaned GR (66,249 rows)
│   ├── invoice_cleaned.csv          # Cleaned Invoice (66,393 rows)
│   └── po_cost_recognition_lookup.csv # Cost recognition rules (64,258 rows)
│
└── import_ready/                     # Final DB-ready files
    └── po_transactions.csv          # Ready for import (132,642 rows)

scripts/
├── config.py                        # Centralized paths & constants
├── 01_clean_gr_data.py              # Step 1: Clean GR data
├── 02_clean_invoice_data.py         # Step 2: Clean Invoice data
├── 03_build_po_lookup.py            # Step 3: Build cost recognition lookup
├── 04_prepare_po_transactions.py    # Step 4: Combine with cost recognition
├── run_pipeline.py                  # Run all steps
│
└── _archive/                        # Old scripts
    ├── simple_gr_cleanup.py
    └── combine_gr_invoice.py
```

### Pipeline Execution

```bash
python3 scripts/run_pipeline.py
```

Or run individually:
```bash
python3 scripts/01_clean_gr_data.py
python3 scripts/02_clean_invoice_data.py
python3 scripts/03_build_po_lookup.py
python3 scripts/04_prepare_po_transactions.py
```

---

## 4. Business Logic Implemented

### Cost Recognition Rules

#### Rule 1: GLD + P/K PO Lines
**Condition:** `PO Account Assignment Category` IN ("P", "K") AND `Main Vendor SLB Vendor Category` = "GLD"

**Result:** Only GR triggers cost recognition
- GR transactions: `cost_recognized_qty = quantity`
- Invoice transactions: `cost_recognized_qty = 0`

#### Rule 2: All Other PO Lines (High Water Mark)
**Condition:** Everything else (including 3rd Party vendors)

**Result:** Whichever event (GR or Invoice) advances `max(cumulative_gr, cumulative_inv)` gets cost recognition

**Algorithm:**
```
For each PO line:
    Sort transactions by: date ASC, quantity DESC
    
    cum_gr = 0, cum_inv = 0, prev_high_water = 0
    
    For each transaction:
        if GR:      cum_gr += quantity
        if Invoice: cum_inv += quantity
        
        high_water = max(cum_gr, cum_inv)
        cost_recognized_qty = high_water - prev_high_water
        prev_high_water = high_water
    
    is_cost_recognized = (cost_recognized_qty > 0)
```

#### Same-Date Tiebreaker
When GR and Invoice have the same posting date, process the **higher quantity first**.

### Example: Partial Quantity Recognition

| Month | Event | Qty | Cum GR | Cum Inv | High Water | Cost Recog Qty |
|-------|-------|-----|--------|---------|------------|----------------|
| Jan | GR | 1 | 1 | 0 | 1 | **1** |
| Feb | Invoice | 2 | 1 | 2 | 2 | **1** |
| Feb | GR | 1 | 2 | 2 | 2 | **0** |
| Mar | Invoice | 4 | 2 | 6 | 6 | **4** |
| Apr | GR | 4 | 6 | 6 | 6 | **0** |
| May | GR | 4 | 10 | 6 | 10 | **4** |
| Jun | Invoice | 4 | 10 | 10 | 10 | **0** |

---

## 5. Current Statistics

| Metric | Value |
|--------|-------|
| Total transactions | 132,642 |
| GR transactions | 66,249 |
| Invoice transactions | 66,393 |
| Total quantity | 7,996,802 |
| Cost recognized qty | 4,252,687 (53%) |
| Transactions with cost | 68,641 |
| Transactions without | 64,001 |
| Unique PO Lines | 64,806 |
| GLD+P/K PO Lines | 1,727 |
| High Water Mark PO Lines | 63,079 |

---

## 6. Configuration Files

### `drizzle.config.ts`
- Points to `dev_v3` schema
- Uses `schemaFilter: ['dev_v3']` for safety

### `scripts/config.py`
- All file paths centralized
- Business rule constants:
  - `VENDOR_CATEGORY_GLD = 'GLD'`
  - `ACCOUNT_ASSIGNMENTS_FOR_GLD = ['P', 'K']`

### `AGENTS.md`
- Instructions for AI agents working on this codebase
- Updated to reference `dev_v3`

---

## 7. Git Commits (Recent)

| Commit | Description |
|--------|-------------|
| `ab2362e` | Add partial quantity cost recognition with high water mark logic |
| `b433bcd` | Add timing-based cost recognition for Invoice PO lines |
| `b8b9f64` | Update cost recognition: remove 3rd Party rule |
| `1aa19ca` | Add invoice cleaning step to pipeline |
| `584b0d6` | Filter GR rows with 0 quantity while keeping amount column |
| `b474e6d` | Restore GR amount in pipeline |
| `66b2af7` | Reorganize data pipeline with numbered scripts |
| `c5c53fb` | Updated scheme to dev_v3 |

---

## 8. What's Being Archived

### Files to Archive
All current data processing scripts and raw data files will be moved to `_archive/` when switching to new data source:

```
scripts/_archive/
├── 01_clean_gr_data.py
├── 02_clean_invoice_data.py
├── 03_build_po_lookup.py
├── 04_prepare_po_transactions.py
├── config.py (or parts of it)
└── run_pipeline.py

data/_archive/
├── raw/
│   ├── gr table.csv
│   ├── invoice table.csv
│   └── po line items.csv
├── intermediate/
└── import_ready/
```

### What Stays
- Database schema (`src/schema/`) - may need updates
- Drizzle configuration
- Project structure
- Business logic concepts (high water mark, cost recognition rules)

---

## 9. New Data Source Plan

### New Files Expected
1. **`po details report.xlsx`** - Replaces `po line items.csv`
   - Different structure with more columns
   - Contains PO line item master data

2. **`po history report.xlsx`** - Replaces `gr table.csv` + `invoice table.csv`
   - Combined GR and Invoice data
   - Has posting type field to distinguish transactions
   - Already structured by PO line with different postings

### Migration Steps
1. Archive all current scripts and data to `_archive/`
2. Analyze new file structures
3. Create new cleaning/transformation scripts
4. Potentially simplify pipeline (fewer steps since data is combined)
5. Apply same business logic (cost recognition rules)
6. Test and validate against expected results

### Questions to Address
- What columns are in the new files?
- Is the posting type field reliable for GR vs Invoice?
- Are partial quantities handled the same way?
- Do we need the same cost recognition lookup?

---

## 10. Commands Reference

### Database
```bash
npm run db:push          # Push schema to database
npm run db:generate      # Generate migrations
npm run db:studio        # Open Drizzle Studio
npm run type-check       # TypeScript validation
npm test                 # Run tests
```

### Pipeline
```bash
python3 scripts/run_pipeline.py                    # Run full pipeline
python3 scripts/01_clean_gr_data.py                # Clean GR only
python3 scripts/04_prepare_po_transactions.py      # Prepare transactions
```

---

## 11. Contact & Notes

- **Repository:** https://github.com/ihabwahbi/cost-management-db
- **Database:** Azure PostgreSQL (credentials in `.env`)
- **Schema:** `dev_v3`

### Key Decisions Made
1. Cost recognized at GR only for GLD vendors with P/K account assignment
2. All other vendors use high water mark logic (timing-based)
3. Same-date transactions: higher quantity processed first
4. Partial quantity recognition supported via `cost_recognized_qty` column

---

*End of Handoff Document*
