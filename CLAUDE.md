# Cost Management Database - Claude Code Guide

Isolated PostgreSQL schema (`dev_v2`) for database development using Drizzle ORM.

## Quick Reference

```bash
npm run db:push       # Push schema changes to database
npm run db:generate   # Generate migration files
npm run db:studio     # Open Drizzle Studio GUI
npm run type-check    # TypeScript validation
npm test             # Run tests
```

## Critical Environment Information

- **Database Credentials**: In `.env` file (NOT auto-loaded)
- **Our Schema**: `dev_v2` (isolated, safe to modify)
- **Production Schema**: `public` (NEVER TOUCH)
- **All Scripts**: Use npm scripts (they handle environment loading)

## Core Rules

### 1. Never Use Direct SQL
All changes go through Drizzle schema files in `src/schema/`.

### 2. Always Import Shared Schema
```typescript
// ✓ CORRECT
import { devV2Schema } from './_schema';

// ✗ WRONG
import { pgSchema } from 'drizzle-orm/pg-core';
const devV2Schema = pgSchema('dev_v2');
```

### 3. Schema Changes Workflow
Edit `src/schema/*.ts` → `npm run db:push` → `npm run type-check`

### 4. Discover Current Schema
Schema files in `src/schema/` are the source of truth. Read them to understand current state.

## Development Workflow

### Planning Phase
1. Read schema files in `src/schema/` to understand current structure
2. Analyze requested changes
3. Suggest specific file modifications
4. Identify potential issues

### Implementation Phase
1. Edit schema files in `src/schema/`
2. Run `npm run db:push`
3. Run `npm run type-check`
4. Report results

### Verification
```bash
npm run db:studio     # Visual inspection
npm run type-check    # Type safety check
npm test             # Automated tests
```

## Naming Conventions

- **TypeScript**: `camelCase` for properties
- **SQL**: `snake_case` for columns and tables
- **Files**: `kebab-case.ts`

## Project Structure

```
src/schema/          # Drizzle schemas (SINGLE SOURCE OF TRUTH)
├── _schema.ts      # Shared devV2Schema instance
├── *.ts            # Table definitions
└── index.ts        # Exports

__tests__/          # Tests
```

## Safety Rules

1. Never modify `public` schema (production)
2. Never commit `.env` file
3. Always use npm scripts
4. Always run type-check after changes

## Common Tasks

### Add/Modify Schema
Edit file in `src/schema/` → `npm run db:push` → `npm run type-check`

### Inspect Schema
```bash
npm run db:studio  # Opens GUI
```

## Drizzle Configuration

`drizzle.config.ts`:
- `schemaFilter: ['dev_v2']` ensures we only touch dev_v2, never public
- Auto-approved push via `--force` flag in package.json

## Common Issues

| Issue | Fix |
|-------|-----|
| Env not loading | Use npm scripts |
| Type errors | `npm run type-check` |
| Want to inspect changes | `npm run db:studio` |

## Resources

- Full details: See `AGENTS.md`
- Drizzle Docs: https://orm.drizzle.team/
