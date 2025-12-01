# Cost Management Logic & Design Decisions

This document captures the core business logic and design decisions for the cost management system. It serves as a reference for understanding how costs are calculated and tracked.

## Overview

The system tracks Purchase Orders (POs) and calculates their cost impact on the Net Income Statement based on Goods Receipt (GR) and Invoice Receipt (IR) postings.

---

## Data Flow

```
Raw PO Line Items CSV
        ↓
   [Cleaning & Filtering]
        ↓
Cleaned PO Line Items  →  po_line_items table
        ↓
GR Table + Invoice Table
        ↓
   [Cost Impact Calculation]
        ↓
Cost Impact Data  →  po_transactions table
        ↓
   [GRIR Exposure Calculation] (Type 1 POs only)
        ↓
GRIR Exposures  →  grir_exposures table
```

---

## PO Line Items Cleaning Rules

### Exclusion Filters (rows removed)

| Filter | Values Excluded |
|--------|-----------------|
| PO Valuation Class | 7800, 7900, 5008 |
| NIS Level 0 Desc | "Compensation Business Delivery", "Compensation Business Enablement" |

### Transformations

| Field | Transformation |
|-------|----------------|
| NIS Level 0 Desc → NIS Line | Renamed column |
| "Lease and Rent Total" | Changed to "Lease and Rent" |
| Valuation Class 3021 with null NIS | Set to "Materials and Supplies" |
| Delivery dates | Consolidated: Use Promised Date if available, else Requested Date → "Expected Delivery Date" |

### Vendor Name Mappings

When Main Vendor ID or Ultimate Vendor Number matches these codes, the corresponding name is applied:

| Vendor ID | Vendor Name |
|-----------|-------------|
| P9516 | Dubai Hub |
| P9109 | Houston Hub |
| P9517 | Shanghai Hub |
| P9518 | Singapore Hub |
| P9514 | Canada Hub |
| P9519 | Japan Hub |
| P9097 | Rotterdam Hub |
| P9107 | NAM RDC |
| P9071 | PPCU |
| P9052 | SRC |
| P9057 | SKK |
| P9060 | SRPC |
| P9036 | HFE |
| P9035 | HCS |
| P9086 | ONESUBSEA |
| P9064 | PPCS |
| P9066 | SWTC |
| P9562 | QRTC |
| P9032 | FCS |

---

## Cost Impact Calculation

### PO Classification

POs are classified into two types for cost impact calculation:

**Type 1 (Simple):**
- Main Vendor SLB Vendor Category = "GLD"
- AND PO Account Assignment Category IN ("K", "P", "S", "V")
- **Cost impact = GR postings only** (IR is ignored)

**Type 2 (Complex):**
- All other POs
- Cost impact calculated using GR/IR posting logic below

### Type 2 Cost Impact Algorithm

For each PO Line ID, process GR and IR postings chronologically:

**State Variables:**
- `Cumulative GR` - Running total of GR quantities
- `Cumulative IR` - Running total of IR quantities  
- `Last Cumulative Cost Impact` - Running total of cost impact quantities

**For each posting (sorted by date):**

```
IF posting is GR:
    Cumulative GR += posting quantity
    IF Cumulative GR >= Cumulative IR:
        Reference = Cumulative GR
    ELSE:
        Reference = MAX(Cumulative GR, Cumulative IR)

IF posting is IR:
    Cumulative IR += posting quantity
    IF Cumulative IR >= Cumulative GR:
        Reference = Cumulative IR
    ELSE:
        Reference = MAX(Cumulative GR, Cumulative IR)

Cost Impact Qty = Reference - Last Cumulative Cost Impact
Cost Impact Amount = Cost Impact Qty × Unit Price
Last Cumulative Cost Impact += Cost Impact Qty
```

**Key Points:**
- Negative cost impact is allowed (reversals)
- Cost is recognized on whichever comes first (GR or IR)
- When one type falls behind, it uses the max to prevent double-counting

### Example

| Date | Type | Qty | Cum GR | Cum IR | Last Cum | Calculation | Cost Impact |
|------|------|-----|--------|--------|----------|-------------|-------------|
| Jan | GR | 1 | 1 | 0 | 0 | 1 >= 0 → Cum GR | **1** |
| Feb | IR | 2 | 1 | 2 | 1 | 2 >= 1 → Cum IR - 1 | **1** |
| Mar | GR | 3 | 4 | 2 | 2 | 4 >= 2 → Cum GR - 2 | **2** |
| Apr | IR | -1 | 4 | 1 | 4 | 1 < 4 → Max(4,1) - 4 | **0** |
| May | GR | 5 | 9 | 1 | 4 | 9 >= 1 → Cum GR - 4 | **5** |
| Jun | IR | 9 | 9 | 10 | 9 | 10 >= 9 → Cum IR - 9 | **1** |
| Jul | GR | -5 | 4 | 10 | 10 | 4 < 10 → Max(4,10) - 10 | **0** |
| Aug | GR | 6 | 10 | 10 | 10 | 10 >= 10 → Cum GR - 10 | **0** |
| Sep | GR | -2 | 8 | 10 | 10 | 8 < 10 → Max(8,10) - 10 | **0** |
| Oct | IR | -2 | 8 | 8 | 10 | 8 >= 8 → Cum IR - 10 | **-2** |

---

## GRIR Exposure Tracking

### What is GRIR?

GRIR (Goods Receipt / Invoice Receipt) exposure tracks the difference between invoiced quantities and goods-received quantities for Type 1 (Simple) POs.

**Why it matters:**
- For Type 1 POs, cost impact is recognized only on GR (IR is ignored for NIS)
- But IR still happens - when IR > GR, we have invoiced value not yet goods-received
- This value sits on the **balance sheet** as an accrual
- Eventually, when GR catches up, this will hit the **Net Income Statement**
- Long-standing GRIR = "timed bomb" of future NIS impact

### GRIR Calculation

**Applies to:** Type 1 (Simple) POs only
- Vendor Category = "GLD"
- Account Assignment Category IN ("K", "P", "S", "V")
- PO Receipt Status ≠ "CLOSED PO" (closed POs have no exposure)

**Formula:**
```
GRIR Qty = Cumulative IR Qty - Cumulative GR Qty
GRIR Value = GRIR Qty × Unit Price

Only tracked when GRIR Qty > 0 (IR exceeds GR)
```

### Time Bucket Aging

GRIR exposures are categorized by age to identify risk:

| Time Bucket | Days Open | Risk Level | Action |
|-------------|-----------|------------|--------|
| < 1 month | 0-30 | Normal | Within same period, acceptable |
| 1-3 months | 31-90 | Monitor | Track for resolution |
| 3-6 months | 91-180 | Investigate | Why hasn't GR happened? |
| 6-12 months | 181-365 | Escalate | Requires management attention |
| > 1 year | 366+ | Critical | Potential write-off or adjustment needed |

### First Exposure Date

The system tracks when the exposure first occurred:
- Walk through GR and IR postings chronologically
- Record the first date when Cumulative IR > Cumulative GR
- If GR later catches up (GR ≥ IR), reset the exposure date
- If IR exceeds GR again, record new exposure date

### Example

| Date | Type | Qty | Cum GR | Cum IR | GRIR Qty | First Exposure |
|------|------|-----|--------|--------|----------|----------------|
| Jan | GR | 10 | 10 | 0 | 0 | — |
| Feb | IR | 15 | 10 | 15 | **5** | Feb (IR > GR) |
| Mar | GR | 3 | 13 | 15 | **2** | Feb (still exposed) |
| Apr | GR | 5 | 18 | 15 | 0 | — (GR caught up) |
| May | IR | 10 | 18 | 25 | **7** | May (new exposure) |

**Final State:** GRIR Qty = 7, First Exposure = May, Days Open = (Today - May)

### Why Only Type 1 POs?

Type 2 (Complex) POs recognize cost impact from **both** GR and IR. The GRIR concept doesn't apply because:
- IR already triggers cost impact when it exceeds GR
- There's no "hidden" balance sheet exposure
- The NIS impact is immediate

Type 1 POs ignore IR for cost impact, creating the exposure situation.

---

## GR and Invoice Table Processing

### GR Table
- Rows with zero quantity are removed
- Rows without matching PO Line ID (in cleaned PO line items) are removed
- GR Amount = Unit Price × GR Effective Quantity

### Invoice Table
- Rows without matching PO Line ID are removed
- Invoice Amount = Unit Price × IR Effective Quantity

### Unit Price Calculation
```
Unit Price = Purchase Value USD / Ordered Quantity
```
(from PO Line Items)

---

## Scripts Location

| Script | Purpose |
|--------|---------|
| `scripts/po-line-items/clean_po_line_items.py` | Clean raw PO line items CSV |
| `scripts/gr-table/clean_gr_table.py` | Clean GR table, calculate GR amounts |
| `scripts/invoice-table/clean_invoice_table.py` | Clean Invoice table, calculate amounts |
| `scripts/cost-impact/calculate_cost_impact.py` | Calculate cost impact from GR/IR |

---

## Output Files

| File | Description |
|------|-------------|
| `data/processed/po_line_items_cleaned.csv` | Cleaned PO line items |
| `data/processed/gr_table_cleaned.csv` | Cleaned GR with amounts |
| `data/processed/invoice_table_cleaned.csv` | Cleaned invoices with amounts |
| `data/processed/cost_impact.csv` | Final cost impact calculations |

---

## Database Schema Notes

- `pos` table was removed - data merged into `po_line_items`
- `po_line_items.po_line_id` is the business key matching source system (e.g., "4581848878-1")
- `po_transactions` stores GR/IR postings with calculated `cost_impact_qty` and `cost_impact_amount`
- `grir_exposures` stores balance sheet exposure for Type 1 POs where IR > GR
- `vendor_category` and `account_assignment_category` are used for Type 1/Type 2 classification

---

*Last updated: December 2024*
