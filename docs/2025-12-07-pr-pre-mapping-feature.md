# Implementation Report: PR Pre-Mapping Feature

**Generated**: 2025-12-07  
**Updated**: 2025-12-07 (Inbox Confirmation Flow)  
**Request**: Design a PR (Purchase Requisition) pre-mapping feature that allows users to submit project mappings before POs are generated, with user confirmation before mappings are finalized.

---

## 1. Executive Summary

**Task**: Create a pre-mapping system where users can map Purchase Requisition (PR) numbers to project cost breakdowns. When PO data is imported with matching PR reference, the system creates pending mappings that require user confirmation via an inbox workflow. Once confirmed and closed, future imports cannot modify the mappings.

**Complexity**: Medium-High (new domain with UI, API, ETL integration, and inbox workflow)

**Estimated Files**: 
- Schema: 1 new table + modifications to po_mappings (in cost-management-db, synced here)
- Procedures: 10-12 new procedures (in new `pr-mapping` domain)
- Cells: 4 new Cells (PR mapping table, toolbar, inbox, dashboard widget)
- Import hook: 1 script modification (in cost-management-db)

**Key Risk**: Schema ownership split - tables must be created in `cost-management-db` and synced here.

---

## 2. Current State Analysis

### 2.1 How It Works Today

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ CURRENT FLOW: Reactive Mapping (Manual, After-the-Fact)                        │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  1. User creates PR in SAP ──► PR has WBS/project context (user knows mapping)│
│                                                                                │
│  2. Procurement generates PO ──► PR number linked to PO in SAP                 │
│                                                                                │
│  3. ETL imports PO data ──► po_line_items has prNumber, prLine, requester      │
│     (cost-management-db)      packages/db/src/schema/po-line-items.ts:25-27    │
│                                                                                │
│  4. User manually maps PO ──► Creates po_mappings → cost_breakdown             │
│     (cost-management app)     packages/db/src/schema/po-mappings.ts:6-23       │
│                                                                                │
│  ⚠️ PROBLEM: Context lost - user forgot mapping intent by time PO arrives!    │
└────────────────────────────────────────────────────────────────────────────────┘
```

**Pain Points**:
1. Users know the correct project mapping at PR creation but can't record it
2. By the time POs arrive (days/weeks later), mapping intent is forgotten
3. Manual mapping of every PO line item is tedious and error-prone
4. No traceability between PR intent and actual PO allocation
5. If user changes a mapping, future imports could override their change

### 2.2 Key Components

| Component | Location | Purpose | Modify? |
|-----------|----------|---------|---------|
| `po_line_items` schema | `packages/db/src/schema/po-line-items.ts:10-79` | PO data with PR fields | No - read only |
| `po_mappings` schema | `packages/db/src/schema/po-mappings.ts:6-23` | PO → cost breakdown links | **Yes - add confirmation fields** |
| `cost_breakdown` schema | `packages/db/src/schema/cost-breakdown.ts:5-19` | Budget categories | No |
| `create-mapping` procedure | `packages/api/src/procedures/po-mapping/create-mapping.procedure.ts:12-78` | Creates mappings | Pattern source |
| `MappingToolbarCell` | `apps/web/components/cells/mapping-toolbar-cell/component.tsx:34-236` | Cascade dropdown UI | Pattern source |

### 2.3 PR Fields Already in Schema

```typescript
// packages/db/src/schema/po-line-items.ts:24-27
prNumber: varchar('pr_number'),      // Line 25 - PR identifier
prLine: integer('pr_line'),          // Line 26 - Line within PR
requester: varchar('requester'),     // Line 27 - Who submitted PR
```

---

## 3. Proposed Solution: Inbox Confirmation Flow

### 3.1 Design Philosophy

**"Capture Intent, Verify Execution, Lock Results"**

The flow ensures:
1. **Intent Capture**: User records mapping when knowledge is fresh
2. **Automatic Matching**: System finds matching POs during import
3. **User Verification**: All matches go to inbox for confirmation
4. **Explicit Closure**: User decides when pre-mapping is complete
5. **Permanence**: Once closed, future imports cannot modify mappings

### 3.2 The Complete Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ INBOX CONFIRMATION FLOW                                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────┐                                                                │
│  │ 1. PRE-MAP  │  User creates pre-mapping: PR 12345 → Project A                │
│  │             │  Status: ACTIVE                                                 │
│  └──────┬──────┘                                                                │
│         │                                                                        │
│         ▼                                                                        │
│  ┌─────────────┐                                                                │
│  │ 2. IMPORT   │  ETL imports PO 111 with prNumber = 12345                      │
│  │             │  System finds matching pre-mapping                              │
│  └──────┬──────┘                                                                │
│         │                                                                        │
│         ▼                                                                        │
│  ┌─────────────┐                                                                │
│  │ 3. MATCH    │  Creates po_mapping with:                                      │
│  │             │  • requiresConfirmation = TRUE                                  │
│  │             │  • mappingSource = 'pre-mapping'                                │
│  └──────┬──────┘                                                                │
│         │                                                                        │
│         ▼                                                                        │
│  ┌─────────────┐                                                                │
│  │ 4. INBOX    │  User sees pending confirmation in inbox                       │
│  │             │  Options: [Confirm] [Change] [Reject]                          │
│  └──────┬──────┘                                                                │
│         │                                                                        │
│         ▼                                                                        │
│  ┌─────────────┐                                                                │
│  │ 5. VERIFY   │  User confirms (or changes) the mapping                        │
│  │             │  requiresConfirmation = FALSE                                   │
│  └──────┬──────┘                                                                │
│         │                                                                        │
│         ▼                                                                        │
│  ┌─────────────┐                                                                │
│  │ 6. CLOSE    │  User clicks "Complete - No More POs Expected"                 │
│  │             │  Pre-mapping status: CLOSED                                     │
│  └──────┬──────┘                                                                │
│         │                                                                        │
│         ▼                                                                        │
│  ┌─────────────┐                                                                │
│  │ 7. LOCKED   │  Future imports: Pre-mapping is CLOSED                         │
│  │             │  • No new matches created                                       │
│  │             │  • User can still manually change po_mappings                   │
│  │             │  • Manual changes are PERMANENT                                 │
│  └─────────────┘                                                                │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 State Machine

```
                                    ┌─────────────────┐
                                    │   CANCELLED     │
                         ┌──────────│  (user action)  │
                         │          └─────────────────┘
                         │
┌─────────────┐    ┌─────┴─────┐    ┌─────────────────┐
│   ACTIVE    │───►│  ACTIVE   │───►│     CLOSED      │
│ (no matches │    │ (pending  │    │ (user clicked   │
│    yet)     │    │ confirms) │    │   "Complete")   │
└─────────────┘    └───────────┘    └─────────────────┘
       │                 ▲                   
       │                 │ New PO matched    
       │                 │ (while still ACTIVE)
       ▼                 │                   
┌─────────────┐          │                   
│   EXPIRED   │──────────┘                   
│  (90 days)  │  If match before expiry     
└─────────────┘                              

CLOSED = Terminal state. No more matching. Permanent.
```

### 3.4 Edge Cases Handled

| Scenario | Behavior |
|----------|----------|
| PR already has PO | Check at pre-map time, offer direct mapping |
| PR never becomes PO | Expires after 90 days, user can cancel early |
| One PR → Multiple POs | Each match goes to inbox, pre-mapping stays ACTIVE |
| User changes after confirm | Change is permanent (mappingSource = 'manual') |
| User changes, then re-import | Pre-mapping CLOSED = no re-matching |
| Manual mapping exists | Skip already-mapped line items |
| Duplicate pre-mapping | Prevent at creation, show existing owner |
| PR format inconsistency | Normalize at boundaries |

---

## 4. Schema Design

### 4.1 New Table: `pr_pre_mappings` (cost-management-db)

```typescript
// pr-pre-mappings.ts
import { uuid, varchar, integer, text, timestamp, index, unique } from 'drizzle-orm/pg-core';
import { costBreakdown } from './cost-breakdown';
import { users } from './users';
import { devV3Schema } from './_schema';

/**
 * PR Pre-Mappings - Advance project allocation for Purchase Requisitions
 * 
 * Lifecycle:
 * 1. User creates pre-mapping: status = 'active'
 * 2. ETL finds matching PO: creates po_mapping with requiresConfirmation = true
 * 3. User confirms matches in inbox
 * 4. User closes pre-mapping: status = 'closed'
 * 5. Future imports: CLOSED pre-mappings are ignored
 */
export const prPreMappings = devV3Schema.table('pr_pre_mappings', {
  id: uuid('id').primaryKey().defaultRandom(),
  
  // PR identification
  prNumber: varchar('pr_number', { length: 20 }).notNull(),
  prLine: integer('pr_line'), // NULL = all lines, specific = single line
  
  // Target mapping
  costBreakdownId: uuid('cost_breakdown_id')
    .notNull()
    .references(() => costBreakdown.id),
  
  // Status: 'active' | 'closed' | 'expired' | 'cancelled'
  status: varchar('status', { length: 20 }).notNull().default('active'),
  
  // Tracking counts (for UI display)
  pendingConfirmationCount: integer('pending_confirmation_count').notNull().default(0),
  confirmedCount: integer('confirmed_count').notNull().default(0),
  
  // Closure tracking
  closedAt: timestamp('closed_at', { withTimezone: true }),
  closedBy: uuid('closed_by').references(() => users.id),
  
  // User context
  notes: text('notes'),
  createdBy: uuid('created_by').references(() => users.id),
  
  // Expiry (for cleanup of unmatched records)
  expiresAt: timestamp('expires_at', { withTimezone: true }).notNull(),
  
  // Timestamps
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
}, (table) => [
  index('pr_pre_mappings_pr_number_idx').on(table.prNumber),
  index('pr_pre_mappings_status_idx').on(table.status),
  index('pr_pre_mappings_expires_at_idx').on(table.expiresAt),
  unique('pr_pre_mappings_pr_number_line_unique').on(table.prNumber, table.prLine),
]);

export type PRPreMapping = typeof prPreMappings.$inferSelect;
export type NewPRPreMapping = typeof prPreMappings.$inferInsert;

export const PR_PRE_MAPPING_EXPIRY_DAYS = 90;
```

### 4.2 Modifications to `po_mappings` (cost-management-db)

```typescript
// po-mappings.ts - ADD these fields
export const poMappings = devV3Schema.table('po_mappings', {
  // ... existing fields ...
  id: uuid('id').primaryKey().defaultRandom(),
  poLineItemId: uuid('po_line_item_id').notNull().references(() => poLineItems.id),
  costBreakdownId: uuid('cost_breakdown_id').notNull().references(() => costBreakdown.id),
  mappedAmount: numeric('mapped_amount').notNull(),
  mappingNotes: text('mapping_notes'),
  mappedBy: varchar('mapped_by'),
  mappedAt: timestamp('mapped_at', { withTimezone: true }).defaultNow(),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
  
  // NEW: Source tracking
  mappingSource: varchar('mapping_source', { length: 20 }).notNull().default('manual'),
  // Values: 'manual' | 'pre-mapping' | 'bulk' | 'inline'
  
  sourcePrPreMappingId: uuid('source_pr_pre_mapping_id')
    .references(() => prPreMappings.id),
  
  // NEW: Confirmation tracking
  requiresConfirmation: boolean('requires_confirmation').notNull().default(false),
  confirmedAt: timestamp('confirmed_at', { withTimezone: true }),
  confirmedBy: uuid('confirmed_by').references(() => users.id),
  
}, (table) => [
  unique('po_mappings_po_line_item_id_key').on(table.poLineItemId),
  index('po_mappings_cost_breakdown_id_idx').on(table.costBreakdownId),
  // NEW: For inbox queries
  index('po_mappings_requires_confirmation_idx').on(table.requiresConfirmation),
  index('po_mappings_source_pr_pre_mapping_id_idx').on(table.sourcePrPreMappingId),
]);
```

---

## 5. Implementation Approach

### Phase 1: Schema Updates (cost-management-db)

**Goal**: Create new table and modify existing

**Files**:
| File | Action |
|------|--------|
| `src/schema/pr-pre-mappings.ts` | Create new |
| `src/schema/po-mappings.ts` | Add new fields |
| `src/schema/index.ts` | Export new table |
| `src/migrations/XXXX_add_pr_pre_mappings.ts` | Migration |

**Success criteria**:
- [ ] Migration runs successfully
- [ ] Schema synced to cost-management project
- [ ] Types exported from `@cost-mgmt/db`

---

### Phase 2: tRPC Procedures (cost-management API)

**Goal**: Create complete API for pre-mapping and inbox

**New Domain**: `packages/api/src/procedures/pr-mapping/`

| File | Purpose |
|------|---------|
| `pr-mapping.router.ts` | Router aggregating all procedures |
| `create-pre-mapping.procedure.ts` | Create single pre-mapping |
| `check-existing-pos.procedure.ts` | Check if PR already has POs before creating |
| `list-pre-mappings.procedure.ts` | List with filters, pagination |
| `get-pre-mapping-stats.procedure.ts` | Dashboard statistics |
| `update-pre-mapping.procedure.ts` | Edit pre-mapping (while active) |
| `delete-pre-mapping.procedure.ts` | Delete/cancel pre-mapping |
| `close-pre-mapping.procedure.ts` | Mark as closed (no more matches) |
| `get-pending-confirmations.procedure.ts` | Get inbox items |
| `confirm-matches.procedure.ts` | Confirm/change/reject matches |
| `bulk-confirm-matches.procedure.ts` | Confirm all for a pre-mapping |

#### Key Procedure: `create-pre-mapping.procedure.ts`

```typescript
export const createPreMapping = protectedProcedure
  .input(z.object({
    prNumber: z.string().min(1).max(20).transform(normalizePRNumber),
    prLine: z.number().int().positive().optional(),
    projectId: z.string().uuid(),
    spendType: z.string(),
    spendSubCategory: z.string(),
    notes: z.string().optional(),
    expiresInDays: z.number().int().min(1).max(365).default(90),
  }))
  .mutation(async ({ input, ctx }) => {
    // 1. Check if POs already exist for this PR
    const existingPOs = await ctx.db.select({
      id: poLineItems.id,
      poNumber: poLineItems.poNumber,
      poValueUsd: poLineItems.poValueUsd,
    })
    .from(poLineItems)
    .leftJoin(poMappings, eq(poMappings.poLineItemId, poLineItems.id))
    .where(and(
      eq(poLineItems.prNumber, input.prNumber),
      isNull(poMappings.id), // Only unmapped
    ))
    .limit(10);
    
    if (existingPOs.length > 0) {
      // Return info for UI to show options
      return {
        existingPOsFound: true,
        unmappedCount: existingPOs.length,
        poNumbers: [...new Set(existingPOs.map(p => p.poNumber))],
        message: 'This PR already has POs. Map them directly or create pre-mapping for future POs.',
      };
    }
    
    // 2. Find matching cost breakdown
    const matchingCostBreakdown = await ctx.db.query.costBreakdown.findFirst({
      where: and(
        eq(costBreakdown.projectId, input.projectId),
        eq(costBreakdown.spendType, input.spendType),
        eq(costBreakdown.spendSubCategory, input.spendSubCategory),
      ),
    });
    
    if (!matchingCostBreakdown) {
      throw new TRPCError({
        code: 'NOT_FOUND',
        message: 'No matching cost breakdown found.',
      });
    }
    
    // 3. Check for duplicate
    const existing = await ctx.db.query.prPreMappings.findFirst({
      where: and(
        eq(prPreMappings.prNumber, input.prNumber),
        input.prLine 
          ? eq(prPreMappings.prLine, input.prLine) 
          : isNull(prPreMappings.prLine),
        inArray(prPreMappings.status, ['active']),
      ),
    });
    
    if (existing) {
      throw new TRPCError({
        code: 'CONFLICT',
        message: `Active pre-mapping exists (created by ${existing.createdBy})`,
      });
    }
    
    // 4. Create pre-mapping
    const expiresAt = new Date(Date.now() + input.expiresInDays * 24 * 60 * 60 * 1000);
    
    const [created] = await ctx.db.insert(prPreMappings).values({
      prNumber: input.prNumber,
      prLine: input.prLine || null,
      costBreakdownId: matchingCostBreakdown.id,
      status: 'active',
      notes: input.notes,
      createdBy: ctx.user.id,
      expiresAt,
    }).returning();
    
    return { 
      success: true, 
      id: created.id,
      expiresAt,
      existingPOsFound: false,
    };
  });
```

#### Key Procedure: `confirm-matches.procedure.ts`

```typescript
export const confirmMatches = protectedProcedure
  .input(z.object({
    poMappingIds: z.array(z.string().uuid()).min(1),
    action: z.enum(['confirm', 'change', 'reject']),
    newCostBreakdownId: z.string().uuid().optional(),
    closePreMapping: z.boolean().default(false),
  }))
  .mutation(async ({ input, ctx }) => {
    return await ctx.db.transaction(async (tx) => {
      // Get the mappings
      const mappings = await tx.select()
        .from(poMappings)
        .where(inArray(poMappings.id, input.poMappingIds));
      
      if (mappings.length === 0) {
        throw new TRPCError({ code: 'NOT_FOUND' });
      }
      
      const prPreMappingId = mappings[0].sourcePrPreMappingId;
      
      if (input.action === 'confirm') {
        // Confirm with original mapping
        await tx.update(poMappings)
          .set({
            requiresConfirmation: false,
            confirmedAt: new Date(),
            confirmedBy: ctx.user.id,
            updatedAt: new Date(),
          })
          .where(inArray(poMappings.id, input.poMappingIds));
      }
      
      if (input.action === 'change') {
        if (!input.newCostBreakdownId) {
          throw new TRPCError({ 
            code: 'BAD_REQUEST', 
            message: 'newCostBreakdownId required for change action' 
          });
        }
        
        // Change to new cost breakdown, mark as manual
        await tx.update(poMappings)
          .set({
            costBreakdownId: input.newCostBreakdownId,
            mappingSource: 'manual', // User overrode, now manual
            sourcePrPreMappingId: null, // Unlink from pre-mapping
            requiresConfirmation: false,
            confirmedAt: new Date(),
            confirmedBy: ctx.user.id,
            updatedAt: new Date(),
          })
          .where(inArray(poMappings.id, input.poMappingIds));
      }
      
      if (input.action === 'reject') {
        // Delete the auto-created mapping
        await tx.delete(poMappings)
          .where(inArray(poMappings.id, input.poMappingIds));
      }
      
      // Update pre-mapping counts
      if (prPreMappingId) {
        const pendingCount = await tx.select({ count: sql`count(*)` })
          .from(poMappings)
          .where(and(
            eq(poMappings.sourcePrPreMappingId, prPreMappingId),
            eq(poMappings.requiresConfirmation, true),
          ));
        
        const confirmedCount = await tx.select({ count: sql`count(*)` })
          .from(poMappings)
          .where(and(
            eq(poMappings.sourcePrPreMappingId, prPreMappingId),
            eq(poMappings.requiresConfirmation, false),
          ));
        
        await tx.update(prPreMappings)
          .set({
            pendingConfirmationCount: Number(pendingCount[0].count),
            confirmedCount: Number(confirmedCount[0].count),
            updatedAt: new Date(),
          })
          .where(eq(prPreMappings.id, prPreMappingId));
        
        // Close pre-mapping if requested
        if (input.closePreMapping) {
          await tx.update(prPreMappings)
            .set({
              status: 'closed',
              closedAt: new Date(),
              closedBy: ctx.user.id,
              updatedAt: new Date(),
            })
            .where(eq(prPreMappings.id, prPreMappingId));
        }
      }
      
      return { success: true, action: input.action, count: input.poMappingIds.length };
    });
  });
```

---

### Phase 3: ETL Matching Logic (cost-management-db)

**Goal**: Auto-match PRs to POs during import, create pending confirmations

**Files**:
| File | Action |
|------|--------|
| `src/imports/po-line-items.ts` | Add post-import hook |
| `src/matching/match-pr-pre-mappings.ts` | New matching logic |

#### Matching Logic

```typescript
// match-pr-pre-mappings.ts
export async function matchPRPreMappings(tx: Transaction) {
  // 1. Find ACTIVE pre-mappings only (not closed, not expired)
  const activeMappings = await tx.query.prPreMappings.findMany({
    where: eq(prPreMappings.status, 'active'),
  });
  
  for (const preMapping of activeMappings) {
    // 2. Find unmapped PO line items with matching PR
    const unmappedLineItems = await tx.select()
      .from(poLineItems)
      .leftJoin(poMappings, eq(poMappings.poLineItemId, poLineItems.id))
      .where(and(
        eq(poLineItems.prNumber, preMapping.prNumber),
        preMapping.prLine 
          ? eq(poLineItems.prLine, preMapping.prLine) 
          : sql`1=1`,
        isNull(poMappings.id), // No existing mapping
      ));
    
    if (unmappedLineItems.length === 0) continue;
    
    // 3. Create pending-confirmation mappings
    const newMappings = unmappedLineItems.map(item => ({
      poLineItemId: item.po_line_items.id,
      costBreakdownId: preMapping.costBreakdownId,
      mappedAmount: item.po_line_items.poValueUsd || '0',
      mappingNotes: `Auto-matched from PR ${preMapping.prNumber}`,
      mappedBy: 'system',
      mappingSource: 'pre-mapping',
      sourcePrPreMappingId: preMapping.id,
      requiresConfirmation: true, // ← GOES TO INBOX
      mappedAt: new Date(),
    }));
    
    await tx.insert(poMappings).values(newMappings);
    
    // 4. Update pre-mapping counts
    await tx.update(prPreMappings)
      .set({
        pendingConfirmationCount: sql`${prPreMappings.pendingConfirmationCount} + ${newMappings.length}`,
        updatedAt: new Date(),
      })
      .where(eq(prPreMappings.id, preMapping.id));
  }
  
  // 5. Expire old pre-mappings
  await tx.update(prPreMappings)
    .set({ status: 'expired', updatedAt: new Date() })
    .where(and(
      eq(prPreMappings.status, 'active'),
      lt(prPreMappings.expiresAt, new Date()),
    ));
}
```

**Key Behaviors**:
- Only matches ACTIVE pre-mappings (ignores CLOSED)
- Creates mappings with `requiresConfirmation: true`
- Skips line items that already have any mapping
- Updates pending count on pre-mapping

---

### Phase 4: UI Components (cost-management web)

**Goal**: Create complete UI for pre-mapping and inbox

#### A. Pre-Mapping Management Cell

**Path**: `apps/web/components/cells/pr-pre-mapping-cell/`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PR Pre-Mappings                                    [+ Create Pre-Mapping]  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Filters: [Status ▼] [Project ▼] [Date Range] [Search PR#]    [Clear All]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PR #     │ Line │ Project          │ Category    │ Status   │ Inbox │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ 12345    │ All  │ Project Alpha    │ Drilling    │ 🟡 Active │ 3 ⏳ │   │
│  │ 12346    │ 1    │ Project Beta     │ Completion  │ 🟢 Closed │ -    │   │
│  │ 12347    │ All  │ Project Alpha    │ Equipment   │ 🔴 Expired│ -    │   │
│  │ 12348    │ 2    │ Project Gamma    │ Services    │ 🟡 Active │ 1 ⏳ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Showing 4 of 24 pre-mappings                          [< 1 2 3 4 5 >]     │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### B. Confirmation Inbox Cell

**Path**: `apps/web/components/cells/pr-mapping-inbox-cell/`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  📥 Pre-Mapping Inbox                                        4 pending      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PR 12345 → Project Alpha (Drilling Equipment)        2 matches      │   │
│  │ Created by John Smith on Dec 5, 2025                                │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                     │   │
│  │  ☐ PO 4501234  │ Line 1 │ $45,000 │ Pump Assembly                  │   │
│  │    └─ Suggested: Project Alpha / Drilling / Pumps                   │   │
│  │                                                                     │   │
│  │  ☐ PO 4501234  │ Line 2 │ $12,000 │ Valve Set                      │   │
│  │    └─ Suggested: Project Alpha / Drilling / Pumps                   │   │
│  │                                                                     │   │
│  │  ────────────────────────────────────────────────────────────────  │   │
│  │                                                                     │   │
│  │  [Confirm Selected]  [Change Selected]  [Reject Selected]           │   │
│  │                                                                     │   │
│  │  ☑ No more POs expected - Close this pre-mapping                   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PR 12348 → Project Gamma (Services)                  1 match        │   │
│  │ ...                                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### C. Change Mapping Dialog

When user clicks "Change Selected":

```
┌─────────────────────────────────────────────────────────────────┐
│  Change Mapping                                           [X]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Changing 2 line items from:                                    │
│  Project Alpha / Drilling / Pumps                               │
│                                                                 │
│  To:                                                            │
│  Project:   [Project Beta        ▼]                             │
│  Type:      [Completion          ▼]                             │
│  Category:  [Valves              ▼]                             │
│                                                                 │
│  Note: This will unlink from the pre-mapping.                   │
│  Future POs will still match to original target.                │
│                                                                 │
│              [Cancel]                    [Save Changes]         │
└─────────────────────────────────────────────────────────────────┘
```

#### D. Dashboard Widget

**Path**: `apps/web/components/cells/pr-mapping-widget/`

```
┌──────────────────────────────────┐
│  📋 PR Pre-Mappings              │
│  ─────────────────────────────── │
│  12 Active    │  4 Pending ⏳    │
│  ─────────────────────────────── │
│  45 Closed    │  3 Expired       │
│  ─────────────────────────────── │
│  ⚠️ 4 items need confirmation    │
│  [View Inbox →]                  │
└──────────────────────────────────┘
```

---

## 6. Anti-Patterns to Avoid

| DO NOT | WHY | INSTEAD |
|--------|-----|---------|
| Auto-confirm any matches | User must verify all matches | All matches go to inbox |
| Allow re-matching after CLOSED | User explicitly said "done" | Check status before matching |
| Override manual mappings | User intent is explicit | Skip already-mapped items |
| Match during API requests | Expensive, should be batch | Match during ETL only |
| Delete matched pre-mappings | Lose audit trail | Keep with CLOSED status |
| Allow duplicate PR+line | Ambiguous intent | Unique constraint |

---

## 7. Data Flow Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ COMPLETE DATA FLOW                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User Action                  API                      Database              │
│  ───────────────────────────────────────────────────────────────────────── │
│                                                                             │
│  1. Create Pre-Mapping                                                      │
│     [Form Submit] ──────► createPreMapping ──────► INSERT pr_pre_mappings   │
│                            │                        status = 'active'       │
│                            │                                                │
│                            └─► Check existing POs                           │
│                                Return warning if found                      │
│                                                                             │
│  2. ETL Import (cost-management-db)                                         │
│     [Pipeline Run] ─────► importPOLineItems ────► UPSERT po_line_items     │
│                            │                                                │
│                            └─► matchPRPreMappings                           │
│                                 │                                           │
│                                 └─► For each ACTIVE pre-mapping:            │
│                                      Find matching PO line items            │
│                                      INSERT po_mappings with:               │
│                                        requiresConfirmation = true          │
│                                        sourcePrPreMappingId = X             │
│                                      UPDATE pr_pre_mappings counts          │
│                                                                             │
│  3. View Inbox                                                              │
│     [Load Page] ────────► getPendingConfirmations ─► SELECT po_mappings    │
│                                                       WHERE requires... = T │
│                                                       JOIN pr_pre_mappings  │
│                                                                             │
│  4. Confirm/Change/Reject                                                   │
│     [User Action] ──────► confirmMatches ──────────► UPDATE/DELETE         │
│                            │                          po_mappings           │
│                            │                                                │
│                            └─► If closePreMapping:                          │
│                                 UPDATE pr_pre_mappings                      │
│                                   status = 'closed'                         │
│                                                                             │
│  5. Future Imports (after CLOSED)                                           │
│     [Pipeline Run] ─────► matchPRPreMappings ───► Skip CLOSED pre-mappings │
│                                                   No new matches created    │
│                                                                             │
│  6. Manual Change (anytime)                                                 │
│     [User Action] ──────► updateMapping ───────► UPDATE po_mappings        │
│                                                   mappingSource = 'manual'  │
│                                                   (Permanent, never touched)│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Test Strategy

### Unit Tests

| Test Case | Location | Assertions |
|-----------|----------|------------|
| Create pre-mapping | `pr-mapping.test.ts` | Creates record, validates cost breakdown |
| Duplicate detection | Same | Throws CONFLICT for same PR/line |
| Existing PO detection | Same | Returns warning when POs exist |
| Confirm match | Same | Sets requiresConfirmation = false |
| Change match | Same | Updates costBreakdownId, sets source = 'manual' |
| Reject match | Same | Deletes po_mapping |
| Close pre-mapping | Same | Sets status = 'closed' |

### Integration Tests

| Test Case | Assertions |
|-----------|------------|
| Full flow: create → match → confirm → close | All states transition correctly |
| Closed pre-mapping ignored on re-import | No new matches created |
| Manual change persists after re-import | mappingSource = 'manual' protects it |
| Multiple POs from same PR | Each goes to inbox separately |

---

## 9. Validation Checklist

```bash
# Required (must all pass)
pnpm type-check
pnpm test
pnpm lint

# Cell validation
pnpm cell-validator apps/web/components/cells/pr-pre-mapping-cell
pnpm cell-validator apps/web/components/cells/pr-mapping-inbox-cell

# Build
pnpm build
```

### Manual Verification
- [ ] Create pre-mapping → appears in table with ACTIVE status
- [ ] Import PO with matching PR → appears in inbox
- [ ] Confirm in inbox → disappears from inbox, stays in PO mapping
- [ ] Change in inbox → uses new cost breakdown, marked as manual
- [ ] Close pre-mapping → status = CLOSED
- [ ] Re-import after CLOSED → no new inbox items
- [ ] Manual change after close → persists through re-import
- [ ] Dashboard widget shows correct counts

---

## 10. Files Summary

### New Files (cost-management)

| Path | Purpose |
|------|---------|
| `packages/api/src/procedures/pr-mapping/pr-mapping.router.ts` | Router |
| `packages/api/src/procedures/pr-mapping/create-pre-mapping.procedure.ts` | Create |
| `packages/api/src/procedures/pr-mapping/check-existing-pos.procedure.ts` | Check POs |
| `packages/api/src/procedures/pr-mapping/list-pre-mappings.procedure.ts` | List |
| `packages/api/src/procedures/pr-mapping/get-pre-mapping-stats.procedure.ts` | Stats |
| `packages/api/src/procedures/pr-mapping/update-pre-mapping.procedure.ts` | Update |
| `packages/api/src/procedures/pr-mapping/delete-pre-mapping.procedure.ts` | Delete |
| `packages/api/src/procedures/pr-mapping/close-pre-mapping.procedure.ts` | Close |
| `packages/api/src/procedures/pr-mapping/get-pending-confirmations.procedure.ts` | Inbox |
| `packages/api/src/procedures/pr-mapping/confirm-matches.procedure.ts` | Confirm |
| `apps/web/components/cells/pr-pre-mapping-cell/*` | Management UI |
| `apps/web/components/cells/pr-mapping-inbox-cell/*` | Inbox UI |
| `apps/web/components/cells/pr-mapping-widget/*` | Dashboard widget |
| `apps/web/app/pr-mapping/page.tsx` | Route page |

### New/Modified Files (cost-management-db)

| Path | Purpose |
|------|---------|
| `src/schema/pr-pre-mappings.ts` | New table |
| `src/schema/po-mappings.ts` | Add confirmation fields |
| `src/matching/match-pr-pre-mappings.ts` | Matching logic |
| `src/imports/po-line-items.ts` | Hook matching after import |

---

## 11. Open Questions (Resolved)

| Question | Resolution |
|----------|------------|
| Should matching run every import? | Yes, to minimize delay |
| Auto-confirm option? | No - all matches require confirmation |
| When to close pre-mapping? | User explicitly clicks "Complete" |
| What if user never confirms? | Dashboard warning, potential email reminder |
| Re-import after manual change? | Safe - CLOSED prevents re-matching |

---

## 12. World-Class UX Summary

This design delivers exceptional UX through:

1. **Intent Capture**: Record mapping when knowledge is fresh
2. **Visibility**: Inbox shows exactly what needs attention
3. **Control**: User confirms every match - no silent automation
4. **Permanence**: CLOSED means done - no surprises from re-imports
5. **Flexibility**: Change individual matches without affecting others
6. **Audit Trail**: Full history of who created, confirmed, changed
7. **Safety**: Manual changes are always protected

The flow transforms mapping from a reactive chore to a proactive, controlled workflow where user intent is captured early, verified explicitly, and locked permanently.

---

## 13. Implementation Status (2025-12-07)

### Phase 1: Schema Updates - COMPLETED

| Item | Status | Notes |
|------|--------|-------|
| `pr_pre_mappings` table | Done | Created at `packages/db/src/schema/pr-pre-mappings.ts` |
| `po_mappings` additions | Done | Added mappingSource, sourcePrPreMappingId, requiresConfirmation, confirmedAt, confirmedBy |
| Schema export | Done | Both exported from `packages/db/src/schema/index.ts` |
| Schema sync | Done | `pnpm db:compare` validates, `npm run db:drift` shows no changes |

### Phase 2: tRPC Procedures - COMPLETED

New domain created at `packages/api/src/procedures/pr-mapping/`:

| Procedure | Type | Status |
|-----------|------|--------|
| `pr-mapping.router.ts` | Router | Done |
| `create-pre-mapping.procedure.ts` | Mutation | Done |
| `check-existing-pos.procedure.ts` | Query | Done |
| `list-pre-mappings.procedure.ts` | Query | Done |
| `get-pre-mapping-stats.procedure.ts` | Query | Done |
| `update-pre-mapping.procedure.ts` | Mutation | Done |
| `delete-pre-mapping.procedure.ts` | Mutation | Done |
| `close-pre-mapping.procedure.ts` | Mutation | Done |
| `get-pending-confirmations.procedure.ts` | Query | Done |
| `confirm-matches.procedure.ts` | Mutation | Done |

Router registered in `packages/api/src/index.ts` as `prMapping`.

### Phase 3: ETL Matching Logic - COMPLETED

**Location**: `cost-management-db`

| File | Action | Status |
|------|--------|--------|
| `src/matching/match-pr-pre-mappings.ts` | New matching logic | Done |
| `src/imports/po-line-items.ts` | Hook matching after import (Step 6) | Done |

**Implementation Details**:
- `matchPRPreMappings()` finds ACTIVE pre-mappings and matches against unmapped PO line items
- Creates `po_mappings` with `requiresConfirmation=true` and `mappingSource='pre-mapping'`
- Updates `pendingConfirmationCount` and `confirmedCount` on the pre-mapping
- Automatically expires pre-mappings past their `expiresAt` date
- Called as Step 6 of the PO Line Items import process

**Call Point**: After PO line item import in ETL pipeline (Step 6/6).

### Phase 4: UI Components - NOT STARTED

Cells to create:
- `pr-pre-mapping-cell` - Management table
- `pr-mapping-inbox-cell` - Confirmation inbox
- `pr-mapping-widget` - Dashboard stats widget
- Page route at `apps/web/app/pr-mapping/page.tsx`

### Validation Results

```bash
# Webapp (cost-management)
pnpm type-check  # PASSED
pnpm lint        # PASSED (pre-existing warnings only)
pnpm db:compare  # PASSED - schema validated

# Database (cost-management-db) - Phase 3 ETL Matching
npm run type-check  # PASSED
npm test            # PASSED - 21 tests
```

### Summary

| Phase | Status | Blocker |
|-------|--------|---------|
| Schema | COMPLETE | - |
| Procedures | COMPLETE | - |
| ETL Matching | COMPLETE | - |
| UI Components | NOT STARTED | - |

**Next Steps**:
1. Create UI Cells for pre-mapping management
2. Create inbox Cell for confirmations
3. Add dashboard widget
4. Add page route and navigation
