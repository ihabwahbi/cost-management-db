# Cost Management Database

Isolated PostgreSQL schema (`dev_v3`) for database development using Drizzle ORM.

---

## QUICK START (AI Agents - Read First)

### Step 1: Understand the Codebase (30 seconds)
```bash
# Read the skeleton index - shows all scripts with compression stats
cat pipeline-context/skeletons/index.json
```

### Step 2: Before ANY Code Change
```bash
# Verify symbols exist before using them
python3 scripts/ask_oracle.py verify <function_or_column_name>

# Check impact before modifying a script
python3 scripts/ask_oracle.py impact <script_name>
```

### Step 3: Follow Patterns
```bash
# Get the pattern for the type of code you're writing
python3 scripts/ask_oracle.py pattern pipeline_script
python3 scripts/ask_oracle.py pattern drizzle_schema
```

### Step 4: Read Full Source Before Writing Code
**Mandatory:** Before writing any code changes, read the full content of the target file.
Do not rely solely on skeletons - they show structure but hide implementation details
(NaN handling, edge cases, pandas quirks).

```bash
# After identifying the target file via skeleton/oracle:
cat scripts/stage3_prepare/06_prepare_po_line_items.py
```

### Freshness Guard (Automatic)
The Oracle CLI automatically regenerates stale artifacts. If you see:
```
Oracle artifacts are stale. Regenerating...
```
This is normal - it means source files changed and context is being updated.
If regeneration fails, the Oracle will exit with an error (never uses broken context).

### Decision Tree

| Task | First Action |
|------|--------------|
| Understand a pipeline script | Read `pipeline-context/skeletons/<stage>/<script>.skeleton.py` |
| Find where a column is used | `python3 scripts/ask_oracle.py trace <column> --direction both` |
| Check if a function exists | `python3 scripts/ask_oracle.py verify <name>` |
| Modify a pipeline script | `python3 scripts/ask_oracle.py impact <script>` first |
| Find who uses a column | `python3 scripts/ask_oracle.py who <column>` |
| Add new pipeline script | `python3 scripts/ask_oracle.py pattern pipeline_script` |
| Add new DB table | `python3 scripts/ask_oracle.py pattern drizzle_schema` |
| Find similar code | `python3 scripts/ask_oracle.py search <query>` |

### Key Files to Know

| File | Purpose |
|------|---------|
| `pipeline-context/skeletons/index.json` | Overview of all scripts (read first) |
| `pipeline-context/registry/symbols.json` | All functions, columns, constants, tables |
| `pipeline-context/lineage/graph.json` | Data flow between scripts |
| `src/schema/index.ts` | All database table exports |
| `scripts/config/column_mappings.py` | CSV to DB column mappings |

### Searching the Codebase

**Always use `rg` (ripgrep) instead of `grep`** - it's faster and has better defaults:

```bash
# Search for a function/variable
rg "filter_valuation" --type py

# Search with context (3 lines before/after)
rg "cost_impact" --type py -C 3

# Search in specific directory
rg "open_po_value" scripts/stage3_prepare/

# Case-insensitive search
rg -i "purchase" --type py

# List files containing pattern (no content)
rg -l "pd.merge" --type py
```

**But prefer the Oracle first** - before blind searching:
```bash
# Find which scripts read/write a column
python3 scripts/ask_oracle.py who "Unit Price"

# Better: Use Oracle to find symbols
python3 scripts/ask_oracle.py search cost_impact

# Better: Trace data lineage
python3 scripts/ask_oracle.py trace open_po_value --direction both
```

---

## PROTOCOL: Before Implementing New Features

**This protocol prevents blind assumptions about data that cause bugs.**

### Step 1: Profile Filter/Transform Columns

Before writing any code that filters or transforms data, profile the relevant columns:

```bash
# Profile a specific column to see its values
python3 scripts/profile_data.py data/intermediate/po_line_items.csv "PO Receipt Status"

# Profile entire file to see all columns
python3 scripts/profile_data.py data/intermediate/po_line_items.csv
```

### Step 2: State Assumptions Explicitly

After profiling, list your assumptions based on what you found:

```
ASSUMPTIONS (based on data profile):
- Column "PO Receipt Status" has values: CLOSED PO, OPEN PO, PO does not require GR
- I will EXCLUDE "CLOSED PO" because [reason]
- I will INCLUDE "OPEN PO" and "PO does not require GR" because [reason]
```

### Step 3: Confidence-Based Proceeding

| Confidence | Action |
|------------|--------|
| **High** | Profile shows expected values, proceed and log assumption |
| **Medium** | Unexpected values found, state assumption and proceed |
| **Low** | Ambiguous/critical values found, ask user before proceeding |

**Low Confidence Examples (STOP and ask):**
- Filter column has unexpected values not mentioned in requirements
- Numeric column has negative values when expecting positive
- Date column has future dates when expecting historical
- Categorical has >10 unique values when expecting few

### Step 4: Run Impact Analysis

```bash
# Before modifying existing script
python3 scripts/ask_oracle.py impact <script_name>

# Check what else uses columns you're touching
python3 scripts/ask_oracle.py who "<column_name>"
```

### Example: GRIR Implementation (What Should Have Happened)

```bash
# 1. Profile the filter columns
python3 scripts/profile_data.py data/intermediate/po_line_items.csv "PO Receipt Status"
# Output: CLOSED PO (53039), OPEN PO (3939), PO does not require GR (185)

# 2. State assumption
# "I see CLOSED PO is 93% of data. Since we're tracking exposure, 
#  CLOSED POs have no exposure. I will EXCLUDE CLOSED PO."

# 3. Confidence: HIGH (clear business logic)
# Proceed with implementation including the filter.
```

---

## Environment Setup

**Database credentials are in `.env` file (NOT auto-loaded by scripts)**

```env
DATABASE_URL=postgresql://user:password@host:5432/postgres?sslmode=require
```

- **Database**: Azure PostgreSQL (shared with production)
- **Our Schema**: `dev_v3` (isolated, safe to modify)
- **Production Schema**: `public` (NEVER TOUCH)
- **Previous Dev Schema**: `dev_v2` (preserved, do not modify)
- **Schema isolation**: No extra costs, complete independence

## Development Commands

**Always use npm scripts** - they handle environment loading automatically:

```bash
# Schema Management
npm run db:push              # Push schema changes to database
npm run db:generate          # Generate migration files
npm run db:studio            # Open Drizzle Studio GUI

# Quality Checks
npm run type-check           # TypeScript validation
npm test                     # Run tests
```

❌ Don't run scripts directly (missing environment)  
✅ Use npm scripts (handles `--env-file=.env` automatically)

## Data Pipeline

The data pipeline transforms raw CSV/Excel files into import-ready CSVs that match the database schema.

### Run Full Pipeline
```bash
python3 scripts/pipeline.py           # Run all stages
python3 scripts/pipeline.py --stage1  # Run only stage 1 (clean)
python3 scripts/pipeline.py --stage2  # Run stages 1-2 (clean + transform)
```

### Pipeline Stages

| Stage | Purpose | Input | Output |
|-------|---------|-------|--------|
| **Stage 1: Clean** | Filter, transform, standardize | `data/raw/` | `data/intermediate/` |
| **Stage 2: Transform** | Enrich, calculate derived values | `data/intermediate/` | `data/intermediate/` |
| **Stage 3: Prepare** | Map columns to DB schema | `data/intermediate/` | `data/import-ready/` |

### Script Conventions
- Scripts are numbered (`01_`, `02_`, etc.) for execution order
- Each stage folder contains scripts that run sequentially by number
- `scripts/config/column_mappings.py` - Central source for CSV→DB column mappings
- Output CSVs in `data/import-ready/` match database table names

**Note:** Static type checker warnings (Pyright/Pylance) for pandas code can be ignored - they're false positives due to pandas' dynamic typing. Runtime behavior is what matters.

## Context Oracle (AI Intelligence Layer)

The Context Oracle is an active guidance system that transforms blind file operations into guided, verified, consistent code changes.

### Three Pillars

| Pillar | Purpose | Artifact |
|--------|---------|----------|
| **Symbol Registry** | Verify before use (anti-hallucination) | `pipeline-context/registry/symbols.json` |
| **Pattern Library** | Follow conventions (anti-drift) | `pipeline-context/patterns/index.json` |
| **Lineage Oracle** | Know impact (guided search) | `pipeline-context/lineage/graph.json` |

### Generated Artifacts

```
pipeline-context/
├── registry/
│   └── symbols.json      # 46 functions, 10 constants, 88 columns, 10 tables
├── skeletons/            # Compressed code views (3.3x compression)
│   ├── stage1_clean/     # Skeleton versions of pipeline scripts
│   ├── stage2_transform/
│   └── stage3_prepare/
├── patterns/
│   └── index.json        # 4 patterns (pipeline_script, drizzle_schema, etc.)
└── lineage/
    └── graph.json        # Data flow graph with variable tracing
```

### Skeleton Column Annotations

Each skeleton file includes a column summary in its docstring:

```python
"""
Stage 3: Prepare PO Line Items for Import
...
Column Operations:
  WRITES: fmt_po, open_po_qty, open_po_value
  READS:  Main Vendor SLB Vendor Category, PO Line ID, PO Receipt Status
"""
```

This tells you at a glance which columns a script touches without reading full source.

### Context Oracle CLI Tool

Use `scripts/ask_oracle.py` to query the Context Oracle. All output is JSON for easy parsing.

**Verify a symbol exists** (anti-hallucination):
```bash
python3 scripts/ask_oracle.py verify filter_valuation_classes
# {"found":true,"type":"function","location":"scripts/stage1_clean/01_po_line_items.py:42",...}

python3 scripts/ask_oracle.py verify nonexistent_function
# {"found":false,"suggestion":"Did you mean 'filter_valuation_classes'?",...}
```

**Predict impact before modifying a script** (with tiered classification):
```bash
python3 scripts/ask_oracle.py impact 05_calculate_cost_impact
# {"script":"05_calculate_cost_impact",
#  "columns_modified":["Unit Price","Cost Impact Qty"],
#  "tiered_impact":{
#    "column_readers":["02_gr_postings","03_ir_postings"],  # Scripts that READ your columns
#    "file_consumers":["06_prepare_po_line_items"]          # Scripts that consume output files
#  },
#  "risk_level":"high",
#  "recommendation":"Test affected scripts: ['02_gr_postings','03_ir_postings']"}
```

**Find which scripts read/write a column**:
```bash
python3 scripts/ask_oracle.py who "Unit Price"
# {"column":"Unit Price",
#  "writers":[{"script":"02_gr_postings","location":"...py:53"}],
#  "readers":[{"script":"02_gr_postings","location":"...py:64"}],
#  "summary":"3 scripts write, 2 scripts read"}
```

**Trace column lineage** (now with variable tracing):
```bash
python3 scripts/ask_oracle.py trace open_po_value --direction upstream
# {"target":"open_po_value","upstream":[...],"critical_files":[...]}
```

**Get code pattern for a task**:
```bash
python3 scripts/ask_oracle.py pattern pipeline_script
# {"found":true,"pattern":{"structure":[...],"conventions":[...],"function_templates":{...}}}
```

**Search for similar symbols**:
```bash
python3 scripts/ask_oracle.py search calculate --limit 5
# {"query":"calculate","count":5,"results":[...]}
```

### When to Use the Oracle

| Task | Command | Purpose |
|------|---------|---------|
| Before calling a function | `verify <name>` | Prevent hallucination |
| Before modifying a script | `impact <script>` | Know what breaks |
| Find who touches a column | `who <column>` | Direct read/write info |
| Understanding data flow | `trace <column>` | Find dependencies |
| Writing new code | `pattern <type>` | Follow conventions |
| Finding existing code | `search <query>` | Avoid duplication |

### Regenerate Context Oracle

```bash
python3 scripts/generate_context_oracle.py    # Full regeneration
```

The pre-commit hook automatically regenerates Context Oracle when pipeline scripts or schema files change.

### Known Limitations (Be Aware)

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| **Voluntary compliance** | Agent can skip Oracle and make blind changes | Always run `verify` and `impact` before writing code |
| **Stale after edits** | After modifying files, artifacts are outdated until regenerated | Run `generate_context_oracle.py` after major changes, or commit to trigger pre-commit |
| **Static analysis only** | Dynamic column names (`df[f"col_{i}"]`) not captured | Check actual code if lineage seems incomplete |
| **Python/TS only** | SQL in strings, config files may be missed | Manually verify database-related changes |

**Critical Rule**: The Oracle is a guide, not a safety net. Always verify your understanding by reading the actual source code before making changes.

## Schema Management Rules

### 1. Never Use Direct SQL
All database changes MUST go through Drizzle ORM schema files in `src/schema/`.

### 2. Always Import Shared Schema
```typescript
// ✓ CORRECT
import { devV3Schema } from './_schema';

// ✗ WRONG - Creates duplicate schema instances
import { pgSchema } from 'drizzle-orm/pg-core';
const devV3Schema = pgSchema('dev_v3');
```

### 3. Standard Workflow
1. Edit schema files in `src/schema/`
2. Run `npm run db:push`
3. Run `npm run type-check`
4. Verify with `npm run db:studio` if needed

### 4. Schema Discovery
- Schema files in `src/schema/` are the source of truth
- Use Read/Grep tools to understand current schema
- Check `src/schema/index.ts` for all table exports

## Drizzle Configuration

Located in `drizzle.config.ts`:
- `schemaFilter: ['dev_v3']` - Only touches `dev_v3`, never `public`
- This ensures all operations are scoped safely

## Naming Conventions

- **TypeScript properties**: `camelCase`
- **SQL columns/tables**: `snake_case`
- **Files**: `kebab-case.ts`
- **Type exports**: `export type TableName = typeof tableName.$inferSelect`

## Safety Rules

1. **Never modify `public` schema** - That's production
2. **Never commit `.env` file** - Contains credentials
3. **Always use npm scripts** - They handle environment
4. **Always run type-check after changes** - Catches errors early

## Commit Discipline (AI Agents)

### Commit Frequently
- **Commit after each logical unit of work** - Don't batch unrelated changes
- **Commit before risky operations** - Create a checkpoint you can revert to
- **Commit after successful tests** - Lock in working state

### Commit Message Format
```
<type>: <short description>

Types: feat, fix, refactor, docs, chore, test
```

### Pre-commit Hooks
This project uses pre-commit hooks. When committing changes to pipeline scripts or schema files, the Context Oracle is automatically regenerated.

```bash
# Install pre-commit (one-time setup)
pip install pre-commit
pre-commit install

# If pre-commit blocks your commit, Context Oracle artifacts were updated
# Stage the updated files and commit again:
git add pipeline-context/
git commit -m "your message"
```

### What Triggers Context Oracle Regeneration
- Any change to `scripts/*.py`
- Any change to `scripts/config/*.py`  
- Any change to `src/schema/*.ts`

The hook ensures Context Oracle artifacts stay in sync with the codebase.

## Development Workflow

### Using PLAN Agent (OpenCode)
1. Analyze schema files in `src/schema/`
2. Suggest changes
3. Identify potential issues

### Using BUILD Agent (OpenCode)
1. Edit schema files
2. Run `npm run db:push`
3. Run `npm run type-check`
4. Report results

## Common Tasks

### Add/Modify Schema
1. Edit relevant file in `src/schema/`
2. Ensure `devV3Schema` is imported from `_schema.ts`
3. Run `npm run db:push`
4. Run `npm run type-check`

### View Schema
```bash
npm run db:studio  # Opens GUI at https://local.drizzle.studio
```

## Project Structure

```
src/schema/              # Drizzle ORM schemas (SINGLE SOURCE OF TRUTH)
├── _schema.ts          # Shared devV3Schema instance (import this!)
├── *.ts                # Individual table definitions
└── index.ts            # Exports all tables

scripts/                 # Data pipeline scripts
├── pipeline.py         # Orchestrator - runs all stages
├── config/
│   └── column_mappings.py  # CSV→DB column mappings
├── stage1_clean/       # Raw → Intermediate
├── stage2_transform/   # Enrichment, calculations
└── stage3_prepare/     # Intermediate → Import-ready

data/
├── raw/                # Source files (never modified)
├── intermediate/       # Cleaned and transformed data
└── import-ready/       # Final CSVs matching DB schema

pipeline-context/        # Context Oracle artifacts (AI guidance)
├── registry/           # Symbol registry (functions, columns, tables)
├── skeletons/          # Compressed code views
├── patterns/           # Code patterns and conventions
└── lineage/            # Data flow graph

__tests__/              # Vitest tests
```

## Migration Strategy

### Development (Current)
Use `npm run db:push` for instant schema changes.

### Production (Future)
```bash
npm run db:generate  # Creates migration files
# Review SQL
# Apply to production with proper controls
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Environment not loading | Use npm scripts (not direct scripts) |
| Type errors after changes | Run `npm run type-check` |
| Want to inspect changes | Run `npm run db:studio` |

## Additional Resources

- Drizzle ORM: https://orm.drizzle.team/
- PostgreSQL Schema Docs: https://www.postgresql.org/docs/current/ddl-schemas.html
