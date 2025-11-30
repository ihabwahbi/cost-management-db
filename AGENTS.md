# Cost Management Database

Isolated PostgreSQL schema (`dev_v3`) for database development using Drizzle ORM.

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

### Pipeline Map (AI Context)
For AI agents working on the pipeline, read `pipeline-map.json` at session start. It contains:
- All scripts with their inputs/outputs and dependencies
- Column mappings (CSV → DB schema)
- Function definitions and data flow

Regenerate after pipeline changes:
```bash
python3 scripts/generate_pipeline_map.py
```

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
    └── graph.json        # 193 nodes, 68 edges tracking data flow
```

### Context Oracle CLI Tool

Use `scripts/ask_oracle.py` to query the Context Oracle. All output is JSON for easy parsing.

**Verify a symbol exists** (anti-hallucination):
```bash
python3 scripts/ask_oracle.py verify filter_valuation_classes
# {"found":true,"type":"function","location":"scripts/stage1_clean/01_po_line_items.py:42",...}

python3 scripts/ask_oracle.py verify nonexistent_function
# {"found":false,"suggestion":"Did you mean 'filter_valuation_classes'?",...}
```

**Predict impact before modifying a script**:
```bash
python3 scripts/ask_oracle.py impact 05_calculate_cost_impact
# {"script":"05_calculate_cost_impact","affected_scripts":[7 scripts],"risk_level":"high",...}
```

**Trace column lineage**:
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
| Understanding data flow | `trace <column>` | Find dependencies |
| Writing new code | `pattern <type>` | Follow conventions |
| Finding existing code | `search <query>` | Avoid duplication |

### Regenerate Context Oracle

```bash
python3 scripts/generate_context_oracle.py           # Full regeneration
python3 scripts/generate_context_oracle.py --skip-pipeline-map  # Skip if pipeline-map is current
```

The pre-commit hook automatically regenerates Context Oracle when pipeline scripts or schema files change.

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
This project uses pre-commit hooks. When committing changes to pipeline scripts or schema files, the pipeline map is automatically regenerated.

```bash
# Install pre-commit (one-time setup)
pip install pre-commit
pre-commit install

# If pre-commit blocks your commit, the pipeline map was updated
# Stage the updated files and commit again:
git add pipeline-map.json pipeline-map.md
git commit -m "your message"
```

### What Triggers Pipeline Map Regeneration
- Any change to `scripts/*.py`
- Any change to `scripts/config/*.py`  
- Any change to `src/schema/*.ts`

The hook ensures `pipeline-map.json` and `pipeline-map.md` stay in sync with the codebase.

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
