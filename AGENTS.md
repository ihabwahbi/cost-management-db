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
| Check system health | `python3 scripts/ask_oracle.py health` |
| Validate before commit | `python3 scripts/ask_oracle.py validate schema-lock` |

### Key Files to Know

| File | Purpose |
|------|---------|
| `COST_MANAGEMENT_LOGIC.md` | **Business rules source of truth** (read for domain logic) |
| `pipeline-context/skeletons/index.json` | Overview of all scripts (read first) |
| `pipeline-context/registry/symbols.json` | All functions, columns, constants, tables |
| `pipeline-context/lineage/graph.json` | Data flow between scripts |
| `src/schema/index.ts` | All database table exports |
| `scripts/config/column_mappings.py` | CSV to DB column mappings |
| `schema_lock.json` | Tracks output schema hashes (auto-validated on commit) |
| `scripts/contracts/*.py` | Pandera data contracts for runtime validation |
| `tests/contracts/test_business_rules.py` | Business rule assertions (from COST_MANAGEMENT_LOGIC.md) |

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

## Data Pipeline

The data pipeline transforms raw CSV/Excel files into import-ready CSVs that match the database schema.

### Run Full Pipeline
```bash
# Use the virtual environment for Pandera validation support
.venv/bin/python scripts/pipeline.py           # Run all stages
.venv/bin/python scripts/pipeline.py --stage1  # Run only stage 1 (clean)
.venv/bin/python scripts/pipeline.py --stage2  # Run stages 1-2 (clean + transform)

# Run golden set tests
.venv/bin/pytest tests/test_pipeline_golden_set.py -v

# Run business rule tests (validates COST_MANAGEMENT_LOGIC.md rules)
.venv/bin/pytest tests/contracts/test_business_rules.py -v
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

---

## Command Reference

### Database (npm scripts)
```bash
npm run db:push              # Push schema changes to database
npm run db:generate          # Generate migration files
npm run db:studio            # Open Drizzle Studio GUI
npm run type-check           # TypeScript validation
npm test                     # Run tests
```

### Context Oracle CLI
```bash
python3 scripts/ask_oracle.py verify <name>           # Check if symbol exists
python3 scripts/ask_oracle.py impact <script>         # Predict change impact
python3 scripts/ask_oracle.py who <column>            # Find column readers/writers
python3 scripts/ask_oracle.py trace <column>          # Trace data lineage
python3 scripts/ask_oracle.py pattern <type>          # Get code pattern
python3 scripts/ask_oracle.py search <query>          # Search symbols
python3 scripts/ask_oracle.py health                  # Check artifact freshness
python3 scripts/ask_oracle.py validate schema-lock    # Validate output schemas
python3 scripts/ask_oracle.py validate pipeline-order # Check for DAG cycles
```

### Data Profiling
```bash
python3 scripts/profile_data.py <file> "<column>"     # Profile specific column
python3 scripts/profile_data.py <file>                # Profile entire file
```

### Validation
```bash
python3 scripts/validators/schema_lock.py --check              # Verify schemas match lock
python3 scripts/validators/schema_lock.py --update             # Update lock (if intentional)
python3 scripts/validators/cross_project_schema.py --check     # Verify webapp sync
python3 scripts/validators/cross_project_schema.py --sync      # Sync to webapp
```

---

## Schema Management

### Rules
1. **Never use direct SQL** - All changes through Drizzle ORM in `src/schema/`
2. **Always import shared schema**:
```typescript
// CORRECT
import { devV3Schema } from './_schema';

// WRONG - Creates duplicate schema instances
import { pgSchema } from 'drizzle-orm/pg-core';
const devV3Schema = pgSchema('dev_v3');
```

### Cross-Project Schema (This Project Owns Data Schemas)

This project owns schema definitions for data tables. The webapp (`cost-management`) imports them.

```bash
# Check sync status (runs automatically on commit)
python3 scripts/validators/cross_project_schema.py --check

# Sync to webapp after schema changes
python3 scripts/validators/cross_project_schema.py --sync

# Then apply from webapp
cd ../cost-management && npm run db:push
```

**Workflow for schema changes:**
1. Edit schema in `src/schema/`
2. Sync: `python3 scripts/validators/cross_project_schema.py --sync`
3. Apply: `cd ../cost-management && npm run db:push`
4. If pipeline-related: update `column_mappings.py` and stage scripts

### Workflow (Single Project)
1. Edit schema files in `src/schema/`
2. Run `npm run db:push`
3. Run `npm run type-check`
4. Verify with `npm run db:studio` if needed

### Naming Conventions
- **TypeScript properties**: `camelCase`
- **SQL columns/tables**: `snake_case`
- **Files**: `kebab-case.ts`

---

## Validation & Recovery

### Pre-commit Hooks (Automatic)

| Layer | What Runs | Purpose |
|-------|-----------|---------|
| **Layer 1** | ruff, mypy, pylint | Standard linting, types, duplicate detection |
| **Layer 2** | Schema lock, Pipeline DAG, Cross-project sync | Catch breaking changes, verify webapp sync |
| **Layer 3** | Oracle regeneration | Keep context artifacts in sync |

### Handling Failures

| Failure | Resolution |
|---------|------------|
| Ruff/MyPy/Pylint | Fix the reported code issues |
| Schema lock check | If INTENTIONAL: `python3 scripts/validators/schema_lock.py --update && git add schema_lock.json`. If UNINTENTIONAL: fix your code |
| Pipeline DAG | Fix circular script dependencies |
| Cross-project sync | Run `python3 scripts/validators/cross_project_schema.py --sync` then `cd ../cost-management && npm run db:push` |
| Oracle regeneration | Stage updated files: `git add pipeline-context/` |

### What Triggers Oracle Regeneration
- Any change to `scripts/stage*/*.py`
- Any change to `scripts/config/*.py`  
- Any change to `src/schema/*.ts`

---

## Safety Rules (NEVER Violate)

1. **NEVER modify `public` schema** - That's production
2. **NEVER commit `.env` file** - Contains credentials
3. **NEVER use direct SQL** - Always use Drizzle ORM
4. **NEVER skip `type-check`** after schema changes
5. **NEVER blindly run `schema_lock.py --update`** - Understand WHY schemas changed first

---

## Commit Discipline

- **Commit after each logical unit of work** - Don't batch unrelated changes
- **Commit before risky operations** - Create a checkpoint
- **Commit after successful tests** - Lock in working state

### Message Format
```
<type>: <short description>

Types: feat, fix, refactor, docs, chore, test
```

---

## Project Structure (Key Directories Only)

| Directory | Purpose |
|-----------|---------|
| `src/schema/` | Drizzle ORM schemas (source of truth for DB) |
| `scripts/stage{1,2,3}_*/` | Pipeline scripts by stage |
| `scripts/contracts/` | Pandera data contracts |
| `scripts/validators/` | Pre-commit validation scripts |
| `pipeline-context/` | Context Oracle artifacts (auto-generated) |
| `data/raw/` | Source files (never modified) |
| `data/intermediate/` | Cleaned/transformed data |
| `data/import-ready/` | Final CSVs matching DB schema |
| `tests/contracts/` | Business rule assertions |

---

## Common Issues

| Issue | Solution |
|-------|----------|
| Environment not loading | Use npm scripts (not direct scripts) |
| Type errors after changes | Run `npm run type-check` |
| Pre-commit hook fails | Read the error message, fix the issue |
| Schema lock mismatch | Intentional? Update lock. Unintentional? Fix code |
| Oracle artifacts stale | Commit triggers auto-regen, or run `python3 scripts/generate_context_oracle.py` |
