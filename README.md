# Cost Management Database

Isolated PostgreSQL schema (`dev_v2`) for database development using Drizzle ORM.

## Quick Start

```bash
# Install dependencies
npm install

# Create .env file (copy from .env.example and add password)
cp .env.example .env

# Reset schema and push (development only)
npm run db:reset

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
2. Run `npm run db:push` to apply changes

**Example:**
```typescript
// src/schema/pos.ts
export const pos = devV2Schema.table('pos', {
  // ... existing columns
  status: varchar('status').default('pending'),  // Add new column
});
```

Then: `npm run db:push`

## Available Scripts

- `npm run db:push` - Push schema changes (auto-approved for AI agents)
- `npm run db:reset` - Drop and recreate schema from scratch (dev only)
- `npm run db:studio` - Open Drizzle Studio GUI
- `npm run type-check` - TypeScript type checking
- `npm test` - Run tests

## Schema Files

All tables are defined in `src/schema/`:
- `projects.ts`, `cost-breakdown.ts`, `pos.ts`, `po-line-items.ts`
- `po-mappings.ts`, `forecast-versions.ts`, `budget-forecasts.ts`

## Key Conventions

- **Database**: Azure PostgreSQL, schema `dev_v2`
- **ORM**: Drizzle ORM (single source of truth)
- **No direct SQL**: All changes through Drizzle schema files
- **Environment**: Credentials in `.env` file (use npm scripts)
