# Data Exploration Findings

**Date:** November 27, 2025  
**Files Analyzed:**
- `po details report.xlsx` (5.67 MB)
- `po history report.xlsx` (7.22 MB)

---

## 1. File Overview

### PO Details Report
| Metric | Value |
|--------|-------|
| Rows | 22,150 |
| Columns | 171 |
| Sheets | 1 (Export) |
| Unique PO Numbers | 7,952 |
| Unique PO+Line combinations | 22,148 |

**Purpose:** Master data for PO line items - contains vendor category, account assignment, costs, etc.

### PO History Report
| Metric | Value |
|--------|-------|
| Rows | 50,863 |
| Columns | 95 |
| Sheets | 1 (Export) |
| Unique PO Numbers | 7,899 |
| Unique PO+Line combinations | 23,351 |

**Purpose:** Transaction data - GR (Goods Receipt) and Invoice postings

---

## 2. Key Column Mapping

### Join Keys
| PO Details | PO History | Notes |
|------------|------------|-------|
| `PO Number` | `PO Number` | String, e.g., "4584576859" |
| `PO Line Item` | `PO Line Item` | Float (1.0, 2.0, etc.) |

**Composite Key:** `PO Number` + `PO Line Item` uniquely identifies a PO line.

### Transaction Type Identification

**PO History Category** is the primary field to distinguish transactions:
| Category | Count | Description |
|----------|-------|-------------|
| Goods receipt | 24,703 | GR postings |
| Invoice receipt | 23,398 | Invoice postings |
| Service entry | 2,321 | Service-based GR |
| Account maintenance | 379 | Adjustments |
| Other | 62 | Down payments, delivery notes, etc. |

**Movement Type** (for GR only):
| Movement Type | Count | Description |
|---------------|-------|-------------|
| 101 | 16,392 | Standard GR |
| 107 | 4,020 | GR for stock transport (intercompany) |
| 109 | 3,655 | GR from production |
| 102 | 585 | GR reversal (negative qty) |
| 161 | 27 | Returns |
| 108, 110 | 24 | Other |

### Vendor Category

**CRITICAL FINDING:** PO Details has the granular vendor category, PO History shows simplified version.

**In PO Details (`SLB Vendor Category`):**
| Category | Count | Notes |
|----------|-------|-------|
| Third Party | 17,154 | External vendors |
| GLD | 3,350 | Internal (for cost recognition rule) |
| OPS | 1,459 | Operations |
| EMS | 176 | EMS division |
| EHQ | 9 | Headquarters |

**In PO History (`SLB Vendor Category`):**
| Category | Count | Notes |
|----------|-------|-------|
| Third Party | 38,884 | External vendors |
| Tech Centers | 11,977 | All ZICP (GLD+OPS+EMS+EHQ combined) |

**Mapping:** Must JOIN to PO Details to get accurate `SLB Vendor Category` for business logic.

### Account Assignment Category

| Category | PO Details Count | PO History Count | Description |
|----------|-----------------|------------------|-------------|
| P | 11,050 | 22,656 | Project |
| K | 7,286 | 17,350 | Cost Center |
| A | 550 | 1,209 | Asset |
| Z | 72 | 150 | New Asset |
| S | 21 | 28 | Sales Order |
| V | 14 | 39 | Reimbursable |
| NaN | 3,157 | 9,431 | Not assigned |

---

## 3. Document Type Analysis

| Doc Type | PO Details | PO History | Description | Vendor Category |
|----------|------------|------------|-------------|-----------------|
| ZNB | 11,146 | 22,762 | Standard PO | Third Party |
| ZREN | 5,690 | 11,435 | Rental | Third Party |
| ZICP | 4,994 | 11,977 | Intercompany PO-SO | GLD/OPS/EMS/EHQ |
| ZATF | 318 | 891 | After the fact PO | Third Party |
| ZFRT | - | 3,796 | Freight | Third Party |

**Note:** ZFRT (Freight) only exists in PO History, not in PO Details. These are 4,001 PO+Lines with no master data.

---

## 4. Join Analysis

| Metric | Count |
|--------|-------|
| PO+Lines in both files | 19,350 |
| PO+Lines in Details only | 2,798 |
| PO+Lines in History only | 4,001 |

**History-only records:** Mostly ZFRT (Freight) document type - no master data available.

---

## 5. Quantity and Amount Analysis

### GR/IR Quantity
| Category | Count | Zeros | Negative | Total Sum |
|----------|-------|-------|----------|-----------|
| Goods receipt | 24,703 | 4,048 (16.4%) | 614 | 706,123 |
| Invoice receipt | 23,398 | 0 | 418 | 747,491 |

### GR/GI/Invoice Amount
| Category | Total Amount (Local Currency) |
|----------|------------------------------|
| Goods receipt | 68,000,000+ |
| Invoice receipt | 83,400,000+ |
| **Total** | **151,414,086** |

### Zero Quantity GRs (Movement Type 107)
- **Count:** 3,569 rows (14.4% of all GR)
- **Movement Type:** 107 (stock transport / intercompany)
- **Pattern:** qty=0 but amount>0
- **Vendor:** All Tech Centers (ZICP)

**Question for domain expert:** Should cost recognition use **quantity** or **amount** for Movement Type 107 records?

---

## 6. Reversals and Credits

| Type | Count | Description |
|------|-------|-------------|
| Negative qty rows | 1,032 | Reversals/credits |
| Movement Type 102 | 585 | GR reversals |
| Credit indicator | 1,054 | Credit transactions |

**Impact on cost recognition:** Reversals should reduce previously recognized cost.

---

## 7. Business Logic Mapping (GLD Rule)

### Previous Rule (from archived data)
> GLD + P/K PO Lines: Only GR triggers cost recognition

### New Data Analysis

**GLD + P/K combinations in PO History (after join):**
| Metric | Value |
|--------|-------|
| Total rows | 591 |
| Unique PO Lines | 312 |
| GR rows | 280 |
| Invoice rows | 311 |
| GR total qty | 1,618 |
| Invoice total qty | 3,203 |
| GR with qty=0 | 21 |

**Third Party + P/K for comparison:**
| Metric | Value |
|--------|-------|
| Total rows | 31,733 |
| Unique PO Lines | 15,673 |
| GR rows | 15,925 |
| Invoice rows | 15,808 |
| GR total qty | 344,873 |
| Invoice total qty | 337,426 |

**Observation:** GLD + P/K is a small subset (312 PO lines vs 15,673 for Third Party).

---

## 8. Date Ranges

| Field | Min | Max |
|-------|-----|-----|
| PO Document Date | 2024-10-25 | 2025-11-26 |
| Delivery Date | 2024-01-06 | 2027-01-01 |
| Posting Date (GR) | 2024-10-27 | 2025-11-26 |
| Posting Date (Invoice) | 2024-10-25 | 2025-11-26 |

**Data covers ~13 months of transactions.**

---

## 9. Questions Requiring Domain Knowledge

### Q1: Movement Type 107 - Quantity vs Amount
Movement Type 107 (intercompany stock transport) has qty=0 but positive amounts. For cost recognition:
- Should we use **quantity** (would give 0 cost recognized)?
- Should we use **amount** (would recognize cost)?
- Is there a different rule for intercompany?

### Q2: GLD Rule Applicability
The GLD + P/K rule affects only 312 PO lines. Confirm:
- Is the rule still: "GLD + P/K = cost at GR only"?
- Does OPS/EMS/EHQ follow the same rule as GLD?

### Q3: ZFRT (Freight) Records
4,001 PO+Lines exist only in History (no Details master). How to handle:
- Should we include them in cost recognition?
- What vendor category should they use?

### Q4: Reversals
Movement Type 102 and Credit indicators represent reversals. Confirm:
- Should reversals reduce previously recognized cost?
- How to handle partial reversals?

### Q5: Service Entries
2,321 rows are "Service entry" with qty=1, amount varies. Are these:
- Treated as GR equivalent for cost recognition?
- Different business logic?

---

## 10. Recommended Data Pipeline

```
Step 1: Load PO Details
        - 22,150 PO lines with master data

Step 2: Load PO History  
        - Filter to 'Goods receipt' and 'Invoice receipt'
        - ~48,000 transaction rows

Step 3: Join on PO Number + PO Line Item
        - Get SLB Vendor Category from Details
        - Get Account Assignment Category from Details

Step 4: Apply Cost Recognition Rules
        - GLD + P/K: Cost at GR only
        - All others: High water mark logic

Step 5: Handle Edge Cases
        - Movement Type 107 (qty=0, amt>0)
        - Reversals (negative qty)
        - Missing master data (ZFRT)
```

---

## 11. Column Reference

### PO Details - Key Columns
| Column | Purpose |
|--------|---------|
| PO Number | Join key |
| PO Line Item | Join key |
| SLB Vendor Category | Business rule (GLD vs others) |
| Acct Assignment Cat. | Business rule (P, K) |
| PO Document Type | ZICP, ZNB, ZREN, ZATF |
| Net Order Value | PO line value |
| PO Requested Quantity | Ordered quantity |
| WBS | Project reference |
| Cost Center | Cost allocation |

### PO History - Key Columns
| Column | Purpose |
|--------|---------|
| PO Number | Join key |
| PO Line Item | Join key |
| PO History Category | GR vs Invoice |
| Movement Type | GR sub-type (101, 107, 102, etc.) |
| GR/IR Quantity | Transaction quantity |
| GR/GI/Invoice Amount in Local Currency | Transaction amount |
| Posting Date | When cost hits P&L |
| Debit/Credit Indicator | Reversal identification |
| Account Assignment Category | Business rule |

---

*End of Exploration Findings*
