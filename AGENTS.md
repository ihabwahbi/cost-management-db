# Cost Management Database

Isolated PostgreSQL schema (`dev_v2`) for database development using Drizzle ORM.

## Environment Setup

**Database credentials are in `.env` file (NOT auto-loaded by scripts)**

```env
DATABASE_URL=postgresql://user:password@host:5432/postgres?sslmode=require
```

- **Database**: Azure PostgreSQL (shared with production)
- **Our Schema**: `dev_v2` (isolated, safe to modify)
- **Production Schema**: `public` (NEVER TOUCH)
- **Schema isolation**: No extra costs, complete independence

## Development Commands

**Always use npm scripts** - they handle environment loading automatically:

```bash
# Schema Management
npm run db:push              # Push schema changes (auto-approved)
npm run db:reset             # Drop and recreate schema (DEV ONLY - DESTRUCTIVE)
npm run db:studio            # Open Drizzle Studio GUI

# Quality Checks
npm run type-check           # TypeScript validation
npm test                     # Run tests
```

❌ Don't run scripts directly (missing environment)  
✅ Use npm scripts (handles `--env-file=.env` automatically)

## Schema Management Rules

### 1. Never Use Direct SQL
All database changes MUST go through Drizzle ORM schema files in `src/schema/`.

### 2. Always Import Shared Schema
```typescript
// ✓ CORRECT
import { devV2Schema } from './_schema';

// ✗ WRONG - Creates duplicate schema instances
import { pgSchema } from 'drizzle-orm/pg-core';
const devV2Schema = pgSchema('dev_v2');
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
- `schemaFilter: ['dev_v2']` - Only touches `dev_v2`, never `public`
- This ensures all operations are scoped safely

## Naming Conventions

- **TypeScript properties**: `camelCase`
- **SQL columns/tables**: `snake_case`
- **Files**: `kebab-case.ts`
- **Type exports**: `export type TableName = typeof tableName.$inferSelect`

## Safety Rules

1. **Never modify `public` schema** - That's production
2. **Never run `db:reset` on production** - Only for local dev
3. **Never commit `.env` file** - Contains credentials
4. **Always use npm scripts** - They handle environment
5. **Always run type-check after changes** - Catches errors early

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
2. Ensure `devV2Schema` is imported from `_schema.ts`
3. Run `npm run db:push`
4. Run `npm run type-check`

### Clean Reset (Development Only)
```bash
npm run db:reset  # Drops all tables and recreates from schema files
```

### View Schema
```bash
npm run db:studio  # Opens GUI at https://local.drizzle.studio
```

## Project Structure

```
src/schema/           # Drizzle ORM schemas (SINGLE SOURCE OF TRUTH)
├── _schema.ts       # Shared devV2Schema instance (import this!)
├── *.ts             # Individual table definitions
└── index.ts         # Exports all tables

scripts/             # Utility scripts
├── drop-schema.ts   # Drop and recreate empty schema
└── create-schema.ts # Create schema

__tests__/           # Vitest tests
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
| "Schema does not exist" | Run `npm run db:reset` |
| Environment not loading | Use npm scripts (not direct tsx) |
| Type errors after changes | Run `npm run type-check` |
| Want to inspect changes | Run `npm run db:studio` |

## Additional Resources

- Drizzle ORM: https://orm.drizzle.team/
- PostgreSQL Schema Docs: https://www.postgresql.org/docs/current/ddl-schemas.html
