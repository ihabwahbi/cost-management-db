# Handoff Document: Cost Management Database

**Date:** November 27, 2025  
**Status:** Starting fresh with new data sources (xlsx files)

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

## 2. Current State

### Active Data Files
```
data/raw/
├── po details report.xlsx      # PO line item master data (NEW SOURCE)
└── po history report.xlsx      # Combined GR/Invoice transactions (NEW SOURCE)
```

### Database Schema Location: `src/schema/`

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
  costRecognizedQty: numeric('cost_recognized_qty').notNull().default('0'),
  isCostRecognized: boolean('is_cost_recognized').notNull().default(false),
  referenceNumber: varchar('reference_number'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
});
```

---

## 3. Next Steps

### New Data Source Exploration
1. Analyze `po details report.xlsx` structure and columns
2. Analyze `po history report.xlsx` structure and columns
3. Create new data transformation scripts
4. Apply same business logic (cost recognition rules)
5. Generate import-ready files for database

### Questions to Address
- What columns are in the new xlsx files?
- Is the posting type field reliable for GR vs Invoice?
- Are partial quantities handled the same way?
- Do we need the same cost recognition lookup?

---

## 4. Business Logic (from previous implementation)

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

## 5. Archived Content

All previous data pipeline scripts and CSV data files have been archived:

```
data/_archive/
├── raw/
│   ├── gr table.csv
│   ├── invoice table.csv
│   └── po line items.csv
├── intermediate/
│   ├── gr_cleaned.csv
│   ├── invoice_cleaned.csv
│   ├── combined_transactions.csv
│   └── po_cost_recognition_lookup.csv
└── import_ready/
    └── po_transactions.csv

scripts/_archive/
├── 01_clean_gr_data.py
├── 02_clean_invoice_data.py
├── 03_build_po_lookup.py
├── 04_prepare_po_transactions.py
├── config.py
├── run_pipeline.py
├── combine_gr_invoice.py
└── simple_gr_cleanup.py
```

### Previous Statistics (from archived data)
| Metric | Value |
|--------|-------|
| Total transactions | 132,642 |
| GR transactions | 66,249 |
| Invoice transactions | 66,393 |
| Cost recognized qty | 4,252,687 (53%) |
| Unique PO Lines | 64,806 |

---

## 6. Commands Reference

### Database
```bash
npm run db:push          # Push schema to database
npm run db:generate      # Generate migrations
npm run db:studio        # Open Drizzle Studio
npm run type-check       # TypeScript validation
npm test                 # Run tests
```

---

## 7. Configuration

### `drizzle.config.ts`
- Points to `dev_v3` schema
- Uses `schemaFilter: ['dev_v3']` for safety

### `AGENTS.md`
- Instructions for AI agents working on this codebase
- Reference for development workflow

---

## 8. Contact & Notes

- **Repository:** https://github.com/ihabwahbi/cost-management-db
- **Database:** Azure PostgreSQL (credentials in `.env`)
- **Schema:** `dev_v3`

### Key Decisions Made (carry forward to new implementation)
1. Cost recognized at GR only for GLD vendors with P/K account assignment
2. All other vendors use high water mark logic (timing-based)
3. Same-date transactions: higher quantity processed first
4. Partial quantity recognition supported via `cost_recognized_qty` column

---

*End of Handoff Document*
