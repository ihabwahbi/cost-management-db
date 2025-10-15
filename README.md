# Cost Management Database - Development Instance

**Isolated PostgreSQL Schema for Independent Database Development**

## Overview

This repository contains an isolated copy of the Cost Management database schema using PostgreSQL schema namespaces. Your friend can develop, modify, and experiment with the database structure without affecting the main application.

### Schema Isolation Strategy

- **Main App Schema**: `public` (used by the production web app)
- **Development Schema**: `dev_v2` (isolated development environment)
- **Database**: Same Azure PostgreSQL instance (no extra cost)
- **Isolation**: Complete data and structure independence

## Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

Create `.env` file with the same database connection as the main app:

```env
DATABASE_URL=postgresql://iwahbi:PASSWORD@cost-management-db.postgres.database.azure.com:5432/postgres?sslmode=require
```

### 3. Create Isolated Schema

Run this **one time** to create the `dev_v2` schema:

```bash
psql $DATABASE_URL -f scripts/setup-schema.sql
```

Or manually:

```sql
CREATE SCHEMA IF NOT EXISTS dev_v2;
```

### 4. Populate with Existing Data

Copy current production data to your isolated schema:

```bash
psql $DATABASE_URL -f scripts/copy-schema-structure.sql
```

This creates an exact replica of the current database in `dev_v2` schema.

## Development Commands

```bash
# Push schema changes to dev_v2
npm run db:push

# Generate migration files
npm run db:generate

# Open database GUI (Drizzle Studio)
npm run db:studio

# Introspect current schema
npm run db:introspect

# Type checking
npm run type-check

# Run tests
npm run test
```

## How It Works

### PostgreSQL Schema Namespaces

PostgreSQL supports multiple schemas (namespaces) in a single database:

```
Azure PostgreSQL Database
├── public schema (main app)
│   ├── projects
│   ├── cost_breakdown
│   └── ...
└── dev_v2 schema (your development)
    ├── projects
    ├── cost_breakdown
    └── ...
```

Both schemas exist independently with:
- ✅ Same database connection
- ✅ Zero additional Azure costs
- ✅ Complete data isolation
- ✅ Independent schema modifications
- ✅ Easy integration path

### Drizzle Configuration

The `drizzle.config.ts` uses `schemaFilter: ['dev_v2']` to target only the development schema:

```typescript
export default defineConfig({
  schema: './src/schema/index.ts',
  schemaFilter: ['dev_v2'],  // ← Only affects dev_v2 schema
  dbCredentials: {
    url: process.env.DATABASE_URL,
  },
});
```

## Development Workflow

### Making Schema Changes

1. **Edit Schema Files** in `src/schema/`:

```typescript
// src/schema/projects.ts
export const projects = devV2Schema.table('projects', {
  id: uuid('id').primaryKey().defaultRandom(),
  name: text('name').notNull(),
  // Add new column
  status: text('status').notNull().default('active'),
});
```

2. **Push Changes**:

```bash
npm run db:push
```

3. **Verify in Drizzle Studio**:

```bash
npm run db:studio
```

4. **Commit Your Changes**:

```bash
git add .
git commit -m "feat: add status column to projects"
git push
```

### Testing Changes

All changes only affect the `dev_v2` schema. The main app continues using `public` schema unaffected.

## Schema Files

Located in `src/schema/`:

- `projects.ts` - Projects table
- `cost-breakdown.ts` - Budget line items
- `pos.ts` - Purchase orders
- `po-line-items.ts` - PO line items
- `po-mappings.ts` - PO to budget mappings
- `forecast-versions.ts` - Forecast versions
- `budget-forecasts.ts` - Budget forecasts

Each file defines tables in the `dev_v2` schema namespace.

## Viewing Your Data

### Drizzle Studio (Recommended)

```bash
npm run db:studio
# Opens https://local.drizzle.studio
```

### psql CLI

```bash
psql $DATABASE_URL

# List tables
\dt dev_v2.*

# Query data
SELECT * FROM dev_v2.projects;

# Compare schemas
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'dev_v2';
```

### Azure Data Studio / pgAdmin

1. Connect using same DATABASE_URL
2. Navigate to `dev_v2` schema
3. Browse tables and data

## Integration with Main App

When database development is complete:

### 1. Share Migration Files

Export your migration files from `src/migrations/`:

```bash
# Copy migrations
cp -r src/migrations/ ../cost-management/packages/db/src/migrations/
```

### 2. Update Main App Schema

Main app developer updates their schema files to match your changes.

### 3. Apply to Production

Run migrations against `public` schema:

```bash
# In main app
npm run db:push
```

### 4. Update Application Code

Update Next.js app to use new schema features.

## Comparing Schemas

To see differences between `dev_v2` and `public`:

```sql
-- Compare table structures
SELECT 
  table_schema,
  table_name,
  column_name,
  data_type
FROM information_schema.columns
WHERE table_schema IN ('public', 'dev_v2')
ORDER BY table_name, column_name;
```

## Troubleshooting

### "Schema dev_v2 does not exist"

Run: `psql $DATABASE_URL -f scripts/setup-schema.sql`

### "Permission denied"

Grant permissions:

```sql
GRANT ALL ON SCHEMA dev_v2 TO iwahbi;
GRANT ALL ON ALL TABLES IN SCHEMA dev_v2 TO iwahbi;
GRANT ALL ON ALL SEQUENCES IN SCHEMA dev_v2 TO iwahbi;
```

### Can't connect to database

Verify DATABASE_URL in `.env` matches the main app's connection string.

## Best Practices

1. **Always work in dev_v2 schema** - Never modify public schema
2. **Commit frequently** - Track your changes in git
3. **Use migrations** - Generate migrations for schema changes
4. **Test before sharing** - Verify changes in Drizzle Studio
5. **Document changes** - Add comments for complex modifications

## Architecture

- **ORM**: Drizzle ORM v0.44.6
- **Database**: Azure PostgreSQL
- **Schema Isolation**: PostgreSQL schema namespaces
- **Type Safety**: Full TypeScript inference
- **Migration**: Drizzle Kit migration system

## Questions?

- **Schema changes**: Check `src/schema/` files
- **Setup issues**: See Troubleshooting section
- **Integration**: Coordinate with main app developer
