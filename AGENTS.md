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
