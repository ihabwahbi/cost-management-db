# Cost Management Database

Isolated PostgreSQL schema (`dev_v3`) for database development using Drizzle ORM.

## Quick Start

```bash
# Install dependencies
npm install

# Create .env file (copy from .env.example and add password)
cp .env.example .env

# Detect schema drift (shows SQL needed, never applies)
npm run db:drift

# Open database GUI
npm run db:studio
```

## AI Agent Setup

This project includes configuration for AI coding agents:

- **`AGENTS.md`** - For OpenCode and other agents supporting the agents.md standard
- **`CLAUDE.md`** - For Claude Code compatibility

Both files contain comprehensive project context, conventions, and workflows. Use the built-in **BUILD** and **PLAN** agents in OpenCode, or default/plan modes in Claude Code.

## Making Schema Changes

1. Edit schema files in `src/schema/`
2. Run `npm run db:drift` to see the SQL needed
3. Apply the SQL manually via psql or database MCP tool

**Example:**
```typescript
// src/schema/some-table.ts
export const someTable = devV3Schema.table('some_table', {
  // ... existing columns
  status: varchar('status').default('pending'),  // Add new column
});
```

Then: `npm run db:drift` → review SQL → apply manually

## Available Scripts

- `npm run db:drift` - Detect schema drift (shows SQL, never applies)
- `npm run db:drift:sql` - Output raw SQL only (for review/piping)
- `npm run db:drift:json` - Output JSON (for CI)
- `npm run db:studio` - Open Drizzle Studio GUI
- `npm run db:generate` - Generate migration files
- `npm run type-check` - TypeScript type checking
- `npm test` - Run tests

## Schema Files

All tables are defined in `src/schema/`:
- Data tables (owned here): `projects.ts`, `cost-breakdown.ts`, `po-line-items.ts`, etc.
- Database views (owned here): `v-project-financials.ts`, `v-po-mapping-detail.ts`
- Webapp tables (symlinked from cost-management): `users.ts`, `agent-memories.ts`, etc.

## Key Conventions

- **Database**: Azure PostgreSQL, schema `dev_v3`
- **ORM**: Drizzle ORM (single source of truth)
- **No direct SQL for schema definitions**: All changes through Drizzle schema files
- **No db:push**: Schema changes applied manually after drift review
- **Environment**: Credentials in `.env` file (use npm scripts)
