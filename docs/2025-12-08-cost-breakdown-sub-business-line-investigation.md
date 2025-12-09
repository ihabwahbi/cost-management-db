# Implementation Report: cost_breakdown.sub_business_line Investigation

**Generated**: 2025-12-08
**Request**: Investigate whether removing `sub_business_line` from `cost_breakdown` table would cause frontend breaking issues and document how it's currently being used.

---

## 1. Executive Summary

**Task**: Analyze the usage of `sub_business_line` column in `cost_breakdown` table and determine the impact of its removal.

**Complexity**: High  
**Estimated Files to Modify**: 15+ files (if removing)  
**Key Risk**: Breaking changes across multiple API procedures and frontend components that depend on this field.

### Key Finding

The user's hypothesis is **CORRECT**: The `sub_business_line` in `cost_breakdown` is **redundant**. It stores the same conceptual data that already exists at the project level. However, it is **heavily used** across the codebase for display, grouping, and sorting purposes.

**Critical Discovery**: There is **NO RELATIONSHIP** between `cost_breakdown.sub_business_line` and `projects.sub_business_line`:
- No foreign key constraint
- No JOIN condition links them
- Values are independently set via user input
- A cost entry can have a different `sub_business_line` than its parent project

---

## 2. Current State Analysis

### 2.1 Schema Definitions

#### cost_breakdown Table
**File:** `packages/db/src/schema/cost-breakdown.ts:5-19`
```typescript
export const costBreakdown = devV3Schema.table('cost_breakdown', {
  id: uuid('id').primaryKey().defaultRandom(),
  projectId: uuid('project_id')
    .notNull()
    .references(() => projects.id),
  subBusinessLine: text('sub_business_line').notNull(),  // ← THE FIELD IN QUESTION
  costLine: text('cost_line').notNull(),
  spendType: text('spend_type').notNull(),
  spendSubCategory: text('spend_sub_category').notNull(),
  budgetCost: numeric('budget_cost').notNull().default('0'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
}, (table) => [
  index('cost_breakdown_project_id_idx').on(table.projectId),
]);
```

#### projects Table
**File:** `packages/db/src/schema/projects.ts:4-10`
```typescript
export const projects = devV3Schema.table('projects', {
  id: uuid('id').primaryKey().defaultRandom(),
  name: text('name').notNull(),
  subBusinessLine: text('sub_business_line').notNull(),  // ← PROJECT-LEVEL SBL
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
});
```

### 2.2 How Data Flows Today

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          USER CREATES PROJECT                                 │
│          create-project.procedure.ts:20-28                                    │
│          └── projects.sub_business_line = USER INPUT                          │
└─────────────────────────────┬────────────────────────────────────────────────┘
                              │ (NO automatic propagation)
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       USER CREATES COST ENTRY                                 │
│          create-cost-entry.procedure.ts:25-37                                 │
│          └── cost_breakdown.sub_business_line = SEPARATE USER INPUT           │
│              (NOT inherited from projects.sub_business_line!)                 │
└─────────────────────────────┬────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    cost_breakdown ←────→ projects                             │
│          Relationship: projectId → projects.id ONLY                           │
│          NO relationship via: sub_business_line fields                        │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 All JOINs Between cost_breakdown and projects

Every JOIN uses ONLY `projectId`, never `sub_business_line`:

| Procedure | File:Line | JOIN Condition |
|-----------|-----------|----------------|
| getPOsWithLineItems | `get-pos-with-line-items.procedure.ts:177` | `eq(costBreakdown.projectId, projects.id)` |
| listPreMappings | `list-pre-mappings.procedure.ts:75,116` | `eq(costBreakdown.projectId, projects.id)` |
| getPendingConfirmations | `get-pending-confirmations.procedure.ts:112` | `eq(costBreakdown.projectId, projects.id)` |
| getOpenPOsWithOperations | `get-open-pos-with-operations.procedure.ts:126` | `eq(costBreakdown.projectId, projects.id)` |
| findMatchingCostBreakdown | `find-matching-cost-breakdown.procedure.ts:39` | `eq(projects.id, costBreakdown.projectId)` |
| getCostBreakdownsForMapping | `get-cost-breakdowns-for-mapping.procedure.ts:36` | `eq(projects.id, costBreakdown.projectId)` |

**Conclusion**: No procedure enforces or checks that `cost_breakdown.sub_business_line` matches `projects.sub_business_line`.

---

## 3. Complete Usage Inventory

### 3.1 INSERT Operations (3 locations)

| File:Line | Context | Source of Value |
|-----------|---------|-----------------|
| `create-cost-entry.procedure.ts:31` | Create new cost entry | User input via form |
| `create-forecast-version.procedure.ts:38` | Create new entries during forecast | User input via wizard |
| `update-cost-entry.procedure.ts:111` | Fork entry on structural update | Inherited OR user input |

### 3.2 UPDATE Operations (1 location)

| File:Line | Context |
|-----------|---------|
| `update-cost-entry.procedure.ts:144` | Direct update when editing cost entry |

### 3.3 SELECT Operations (Returns in Query Results)

| Procedure | File:Line | Purpose |
|-----------|-----------|---------|
| `getCostBreakdownByVersion` | `get-cost-breakdown-by-version.procedure.ts:87` | Returns full `costBreakdown` row |
| `getForecastData` | `get-forecast-data.procedure.ts:55,105` | Explicitly selects `subBusinessLine` |
| `getCostBreakdownsForMapping` | `get-cost-breakdowns-for-mapping.procedure.ts:26` | Explicitly selects `subBusinessLine` |
| `findMatchingCostBreakdown` | `find-matching-cost-breakdown.procedure.ts:32` | Explicitly selects `subBusinessLine` |
| `getProjectHierarchicalBreakdown` | `get-project-hierarchical-breakdown.procedure.ts:67` | Uses for ORDER BY and grouping |
| `getComparisonData` | `get-comparison-data.procedure.ts:67-70` | Returns full `costBreakdown` for display |

### 3.4 ORDER BY / GROUP BY Usage

**File:** `get-project-hierarchical-breakdown.procedure.ts:66-71`
```typescript
.orderBy(
  costBreakdown.subBusinessLine,  // ← Used for sorting
  costBreakdown.costLine,
  costBreakdown.spendType,
  costBreakdown.spendSubCategory
)
```
This procedure builds a hierarchical tree where `subBusinessLine` is the **top-level grouping node**.

### 3.5 Frontend Components Using subBusinessLine

| Component | File:Line | Usage |
|-----------|-----------|-------|
| **Cost Breakdown Table** | `columns.tsx:80-98` | Editable column with dropdown |
| **CostEntry Type** | `types.ts:4` | `subBusinessLine: string` required field |
| **Version Comparison** | `component.tsx:111` | Category label: `costBreakdown?.subBusinessLine \|\| 'Uncategorized'` |
| **Forecast Wizard** | `component.tsx:26` | Interface has `sub_business_line: string` |
| **Inline Entry Row** | `inline-entry-row.tsx:12,33,53` | Form field with default value |
| **Forecast Editable Table** | `forecast-editable-table.tsx:17` | Interface requires `sub_business_line` |
| **Budget Review Step** | `budget-review-step.tsx:17` | Interface requires `sub_business_line` |
| **Preview Step** | `preview-step.tsx:10` | Interface requires `sub_business_line` |

---

## 4. Impact Assessment: What Would Break

### 4.1 API Procedures (MUST Modify)

| Procedure | File | Change Required |
|-----------|------|-----------------|
| `createCostEntry` | `create-cost-entry.procedure.ts` | Remove `subBusinessLine` from input schema |
| `updateCostEntry` | `update-cost-entry.procedure.ts` | Remove `subBusinessLine` from input/update logic |
| `createForecastVersion` | `create-forecast-version.procedure.ts` | Remove `subBusinessLine` from `newEntries` schema |
| `getCostBreakdownByVersion` | `get-cost-breakdown-by-version.procedure.ts` | JOIN to projects for display |
| `getForecastData` | `get-forecast-data.procedure.ts` | JOIN to projects for display |
| `getCostBreakdownsForMapping` | `get-cost-breakdowns-for-mapping.procedure.ts` | Already JOINs, just change SELECT |
| `findMatchingCostBreakdown` | `find-matching-cost-breakdown.procedure.ts` | Change output schema, JOIN projects |
| `getProjectHierarchicalBreakdown` | `get-project-hierarchical-breakdown.procedure.ts` | **Complex change**: Would need to JOIN projects OR change grouping logic |
| `getComparisonData` | `get-comparison-data.procedure.ts` | JOIN to projects for context |

### 4.2 Frontend Components (MUST Modify)

| Component | File | Change Required |
|-----------|------|-----------------|
| `cost-breakdown-table-cell` | `columns.tsx:80-98` | Remove editable column |
| `cost-breakdown-table-cell` | `types.ts:4` | Remove from interface |
| `forecast-wizard` | `component.tsx:26` | Remove from CostBreakdown interface |
| `forecast-wizard` | `inline-entry-row.tsx:12,33,53` | Remove form field |
| `forecast-wizard` | Multiple step files | Update interfaces |
| `version-comparison-cell` | `component.tsx:111` | Get category from project instead |
| `project-dashboard-cell` | `component.tsx:109,122` | Update data transformation |

### 4.3 Tests (MUST Update)

| Test File | Impact |
|-----------|--------|
| `budget-review-step.test.tsx` | Mock data has `sub_business_line` |
| `preview-step.test.tsx` | Mock data has `sub_business_line` |
| `forecast-editable-table.test.tsx` | Mock data has `sub_business_line` |

---

## 5. Validation Schema Impact

**File:** `packages/api/src/schemas/enums.ts:18-23`
```typescript
export const subBusinessLineSchema = z.enum([
  "WLES", "WLPS", "TCPF", "SLKN", "TSW",
  "WIS", "WPS", "PSV", "LABR", "DHT",
  "TWL", "TTPS"
])
```

This schema is used in:
- `create-cost-entry.procedure.ts:15` - Input validation
- `update-cost-entry.procedure.ts:24` - Input validation
- `create-forecast-version.procedure.ts:14` - Input validation
- `create-project.procedure.ts:18` - Would KEEP (projects still need it)

---

## 6. Recommendations

### Option A: Remove `sub_business_line` from `cost_breakdown` (Recommended Long-term)

**Rationale**: The field is logically redundant since sub-business line is a project-level attribute, not a cost-line-level attribute.

**Migration Steps:**

1. **Schema change** in `cost-management-db` project:
   ```sql
   ALTER TABLE dev_v3.cost_breakdown DROP COLUMN sub_business_line;
   ```

2. **API procedure updates** (9 procedures):
   - Remove from INSERT values
   - JOIN to `projects` when `subBusinessLine` needed for display
   - Update output schemas

3. **Frontend updates** (8+ components):
   - Remove editable column from cost breakdown table
   - Update type interfaces
   - Get `subBusinessLine` from parent project for display

4. **Test updates** (3+ test files):
   - Update mock data

**Estimated Effort**: 3-5 days

### Option B: Keep but Deprecate (Short-term)

If immediate removal is risky:
1. Add a comment marking it as deprecated
2. Auto-populate from `projects.sub_business_line` on INSERT
3. Remove UI editing capability (display only, inherited from project)
4. Schedule full removal in future release

---

## 7. Answer to Original Question

### Will removing `sub_business_line` from `cost_breakdown` cause frontend breaking issues?

**YES**, removing this column will cause breaking issues in:

| Category | Count | Severity |
|----------|-------|----------|
| API Procedures | 9 | HIGH - Type errors, runtime failures |
| Frontend Components | 8+ | HIGH - Type errors, missing data |
| Tests | 3+ | MEDIUM - Test failures |

### Is the field used in procedures?

**YES**, extensively:
- 3 INSERT operations
- 1 UPDATE operation  
- 6+ SELECT operations
- 1 ORDER BY/GROUP BY operation (hierarchical breakdown)

### How is it being used?

1. **Display**: Shown in tables, comparison views, forms
2. **Grouping**: Top-level node in hierarchical breakdown
3. **Sorting**: Used in ORDER BY clauses
4. **User Input**: Editable field in cost entry forms

### Is removal feasible?

**YES**, but requires coordinated changes:
1. Schema change in `cost-management-db` (source of truth)
2. API procedure updates to JOIN projects table
3. Frontend component updates to remove editing, update display
4. Test updates

The user's intuition is correct that this data is redundant at the cost entry level. The `sub_business_line` should be derived from the parent project, not stored independently per cost entry.

---

## 8. Quick Reference

### Files to Modify for Removal

**API Layer:**
```
packages/api/src/procedures/cost-breakdown/create-cost-entry.procedure.ts
packages/api/src/procedures/cost-breakdown/update-cost-entry.procedure.ts
packages/api/src/procedures/cost-breakdown/get-cost-breakdown-by-version.procedure.ts
packages/api/src/procedures/forecasts/create-forecast-version.procedure.ts
packages/api/src/procedures/forecasts/get-forecast-data.procedure.ts
packages/api/src/procedures/forecasts/get-comparison-data.procedure.ts
packages/api/src/procedures/po-mapping/get-cost-breakdowns-for-mapping.procedure.ts
packages/api/src/procedures/po-mapping/find-matching-cost-breakdown.procedure.ts
packages/api/src/procedures/dashboard/get-project-hierarchical-breakdown.procedure.ts
```

**Frontend Layer:**
```
apps/web/components/cells/cost-breakdown-table-cell/components/columns.tsx
apps/web/components/cells/cost-breakdown-table-cell/types.ts
apps/web/components/cells/forecast-wizard/component.tsx
apps/web/components/cells/forecast-wizard/components/inline-entry-row.tsx
apps/web/components/cells/forecast-wizard/components/forecast-editable-table.tsx
apps/web/components/cells/forecast-wizard/steps/*.tsx
apps/web/components/cells/version-comparison-cell/component.tsx
apps/web/components/cells/project-dashboard-cell/component.tsx
```

### Do Not Touch (Related but Unaffected)

| File | Reason |
|------|--------|
| `packages/db/src/schema/projects.ts` | Project-level SBL is correct |
| `packages/db/src/schema/po-line-items.ts` | Different context (PO filtering) |
| `packages/db/src/schema/wbs-details.ts` | Different context (WBS array) |
| `packages/api/src/schemas/enums.ts` | Still needed for projects |
| `apps/web/lib/constants.ts` | Still needed for UI options |

---

## 9. Conclusion

The `sub_business_line` column in `cost_breakdown` is a **data modeling redundancy** that was likely introduced for convenience but creates logical inconsistency (cost entries can have different SBL than their parent project). 

**Recommendation**: Proceed with removal, but coordinate:
1. Schema change in `cost-management-db` first
2. Sync to this project
3. Update all procedures to JOIN to projects
4. Update all frontend components
5. Update tests

This will result in cleaner data model where `sub_business_line` is truly a project-level attribute, not a cost-line attribute.
