# Database Development Handoff

## What's Been Set Up

I've created an isolated database development environment for you using PostgreSQL schema namespaces. This allows you to work on the database independently without affecting the main application.

## Quick Summary

- **Repository**: `cost-management-db` (separate from main app)
- **Your Schema**: `dev_v2` (completely isolated)
- **Main App Schema**: `public` (remains untouched)
- **Database**: Same Azure PostgreSQL (no extra cost)
- **Technologies**: Drizzle ORM, TypeScript, PostgreSQL

## What You Need to Do

### 1. Get Database Credentials

Ask me for:
- Database connection string (DATABASE_URL)
- Or get it from: Azure Portal → Database → Settings → Connection strings

### 2. Follow Setup Guide

Open `SETUP.md` and follow the step-by-step instructions. It takes about 10 minutes.

**Quick version:**

```bash
# 1. Install dependencies
npm install

# 2. Create .env file with DATABASE_URL
cp .env.example .env
# Edit .env and add your password

# 3. Create dev_v2 schema (one-time)
psql $DATABASE_URL -f scripts/setup-schema.sql

# 4. Copy existing data to dev_v2
psql $DATABASE_URL -f scripts/copy-schema-structure.sql

# 5. Verify setup
npm run db:studio
```

### 3. Start Developing

You can now:
- Modify schema files in `src/schema/`
- Add new tables, columns, relationships
- Test changes with `npm run db:push`
- View data in Drizzle Studio (`npm run db:studio`)

**All your changes only affect the `dev_v2` schema!**

## How Schema Isolation Works

```
Azure PostgreSQL Database
├── public schema (main app's data)
│   ├── projects
│   ├── cost_breakdown
│   └── ...
└── dev_v2 schema (your development area)
    ├── projects
    ├── cost_breakdown
    └── ...
```

Both schemas are completely isolated. You can:
- ✅ Add/remove/modify tables in dev_v2
- ✅ Test with real data (copied from public)
- ✅ Experiment freely
- ✅ Make mistakes without affecting main app

The main app continues using `public` schema and is completely unaffected by your work.

## Development Workflow

### Making Changes

1. **Edit schema files** (`src/schema/*.ts`)
2. **Push changes**: `npm run db:push`
3. **Verify**: `npm run db:studio`
4. **Commit**: `git add . && git commit -m "description"`

### Example: Adding a New Column

```typescript
// Edit src/schema/projects.ts
export const projects = devV2Schema.table('projects', {
  id: uuid('id').primaryKey().defaultRandom(),
  name: text('name').notNull(),
  subBusinessLine: text('sub_business_line').notNull(),
  
  // Add new column
  status: text('status').notNull().default('active'),
  
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
});
```

```bash
# Apply change
npm run db:push

# Verify in Drizzle Studio
npm run db:studio
```

### Available Commands

```bash
npm run db:studio      # Open database GUI
npm run db:push        # Apply schema changes
npm run db:generate    # Generate migration files
npm run db:introspect  # Introspect current database
npm run type-check     # TypeScript validation
npm run test           # Run tests
```

## Schema Files

All database tables are defined in `src/schema/`:

- `projects.ts` - Projects table
- `cost-breakdown.ts` - Budget line items
- `pos.ts` - Purchase orders
- `po-line-items.ts` - PO line items
- `po-mappings.ts` - PO to budget mappings
- `forecast-versions.ts` - Forecast versions
- `budget-forecasts.ts` - Budget forecasts

Each file uses `devV2Schema.table()` to ensure changes only affect `dev_v2`.

## Integration Back to Main App

When you're done developing:

### Step 1: Share Your Changes

Send me:
1. Migration files from `src/migrations/`
2. Updated schema files from `src/schema/`
3. List of changes you made

### Step 2: I'll Review & Integrate

I will:
1. Review your schema changes
2. Copy migrations to main app
3. Update main app's schema files
4. Run migrations on `public` schema
5. Update application code to use new schema

### Step 3: Testing

We'll test together:
1. Run migrations on staging
2. Verify data integrity
3. Test application functionality
4. Deploy to production

## Safety Features

1. **Complete Isolation**: Your changes never touch `public` schema
2. **Same Database**: Easy to compare and migrate changes
3. **Version Control**: Git tracks all your changes
4. **Type Safety**: TypeScript catches errors before database
5. **Drizzle Studio**: Visual interface to verify changes

## Resources

- **README.md** - Comprehensive usage guide
- **SETUP.md** - Step-by-step setup instructions
- **Drizzle Docs** - https://orm.drizzle.team/
- **PostgreSQL Schema Docs** - https://www.postgresql.org/docs/current/ddl-schemas.html

## Current Schema Structure

Your `dev_v2` schema currently has these tables:

1. **projects** - Project metadata
2. **cost_breakdown** - Budget line items per project
3. **pos** - Purchase orders
4. **po_line_items** - Individual items in POs
5. **po_mappings** - Mapping PO items to budget lines
6. **forecast_versions** - Budget forecast versions
7. **budget_forecasts** - Forecasted costs per version

All tables use UUID primary keys and have `created_at`/`updated_at` timestamps.

## Need Help?

1. **Setup issues**: Check SETUP.md troubleshooting section
2. **Schema questions**: Read the schema files in `src/schema/`
3. **Drizzle help**: Check https://orm.drizzle.team/docs/overview
4. **Integration questions**: Ask me!

## Getting Started Checklist

- [ ] Clone repository
- [ ] Run `npm install`
- [ ] Create `.env` file with DATABASE_URL
- [ ] Run setup-schema.sql
- [ ] Run copy-schema-structure.sql
- [ ] Verify with `npm run db:studio`
- [ ] Make a test change
- [ ] Read README.md for detailed workflow

## Next Steps

1. **Complete setup** using SETUP.md
2. **Explore the schema** in Drizzle Studio
3. **Make test changes** to familiarize yourself
4. **Start developing** the database improvements
5. **Commit regularly** to track your progress

When you're ready to integrate your changes, let me know and we'll coordinate the merge back to the main application!
