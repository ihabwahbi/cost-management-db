# Setup Guide - Cost Management DB (dev_v2 Schema)

This guide will help you set up an isolated database development environment.

## What You're Setting Up

You're creating an isolated copy of the Cost Management database using PostgreSQL schema namespaces:

- **Your work**: `dev_v2` schema (completely isolated)
- **Main app**: `public` schema (untouched)
- **Same database**: No extra Azure resources needed

## Prerequisites

- [ ] Node.js 18+ installed
- [ ] Database connection string from main developer
- [ ] Git installed
- [ ] PostgreSQL client (psql) or Azure Data Studio (for running SQL scripts)

## Step-by-Step Setup

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd cost-management-db
```

### Step 2: Install Dependencies

```bash
npm install
```

Expected output: Dependencies installed successfully

### Step 3: Configure Environment

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` and add your database password:

```env
DATABASE_URL=postgresql://iwahbi:YOUR_PASSWORD_HERE@cost-management-db.postgres.database.azure.com:5432/postgres?sslmode=require
```

Get the password from the main developer or Azure Portal.

### Step 4: Create dev_v2 Schema

**Option A: Using psql (Recommended)**

```bash
psql $DATABASE_URL -f scripts/setup-schema.sql
```

**Option B: Using Azure Data Studio**

1. Open Azure Data Studio
2. Connect using your DATABASE_URL
3. Open `scripts/setup-schema.sql`
4. Execute the script

**Option C: Manual SQL**

Connect to database and run:

```sql
CREATE SCHEMA IF NOT EXISTS dev_v2;
```

### Step 5: Copy Existing Data (Optional but Recommended)

This creates an exact replica of the current production data in your isolated schema.

**Option A: Using psql**

```bash
psql $DATABASE_URL -f scripts/copy-schema-structure.sql
```

**Option B: Using Azure Data Studio**

1. Open `scripts/copy-schema-structure.sql`
2. Execute the script

This will:
- Copy all table structures from `public` to `dev_v2`
- Copy all existing data
- Preserve all indexes and constraints

**Skip this step if you want to start with an empty schema**

### Step 6: Verify Setup

Check that your schema was created successfully:

```bash
npm run db:studio
```

This opens Drizzle Studio at https://local.drizzle.studio

You should see:
- All tables listed (projects, cost_breakdown, pos, etc.)
- Data if you copied from public schema
- Schema name: `dev_v2`

### Step 7: Test Database Connection

Create a test script to verify everything works:

```bash
# Create test file
cat > test-connection.js << 'EOF'
import postgres from 'postgres';

const sql = postgres(process.env.DATABASE_URL);

async function test() {
  try {
    const result = await sql`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'dev_v2'
    `;
    console.log('✅ Connection successful!');
    console.log('Tables in dev_v2 schema:', result);
    process.exit(0);
  } catch (error) {
    console.error('❌ Connection failed:', error.message);
    process.exit(1);
  }
}

test();
EOF

# Run test
node test-connection.js
```

## Verification Checklist

After setup, verify:

- [ ] `npm install` completed successfully
- [ ] `.env` file exists with correct DATABASE_URL
- [ ] `dev_v2` schema created (check in Drizzle Studio)
- [ ] Tables visible in `dev_v2` schema
- [ ] Data copied (if you chose to copy)
- [ ] `npm run db:studio` opens successfully

## First Steps After Setup

### 1. Explore the Schema

```bash
npm run db:studio
```

Browse tables and data in the GUI.

### 2. Make a Test Change

Try adding a test column:

```typescript
// Edit src/schema/projects.ts
export const projects = devV2Schema.table('projects', {
  // ... existing columns ...
  
  // Add test column
  testColumn: text('test_column'),
});
```

Push the change:

```bash
npm run db:push
```

Verify in Drizzle Studio that the column was added to `dev_v2.projects` (not `public.projects`).

### 3. Remove Test Change

Remove the test column and push again:

```bash
npm run db:push
```

## Common Issues

### Issue: "psql: command not found"

**Solution**: Install PostgreSQL client:

**macOS**:
```bash
brew install postgresql
```

**Ubuntu/Debian**:
```bash
sudo apt-get install postgresql-client
```

**Windows**: Install from https://www.postgresql.org/download/windows/ or use Azure Data Studio instead

### Issue: "schema dev_v2 does not exist"

**Solution**: Run Step 4 again to create the schema

### Issue: "Permission denied for schema dev_v2"

**Solution**: Ask database administrator to grant permissions:

```sql
GRANT ALL ON SCHEMA dev_v2 TO iwahbi;
GRANT ALL ON ALL TABLES IN SCHEMA dev_v2 TO iwahbi;
GRANT ALL ON ALL SEQUENCES IN SCHEMA dev_v2 TO iwahbi;
```

### Issue: "Cannot connect to database"

**Solutions**:
1. Verify DATABASE_URL in `.env`
2. Check firewall rules in Azure Portal
3. Verify password is correct
4. Ensure `sslmode=require` is in connection string

### Issue: "Tables already exist in dev_v2"

**Solution**: If you need to start fresh:

```sql
-- Drop and recreate schema
DROP SCHEMA dev_v2 CASCADE;
CREATE SCHEMA dev_v2;
```

Then run setup again.

## Next Steps

Once setup is complete:

1. **Read the README.md** - Understand the development workflow
2. **Explore the schema files** - Check `src/schema/` directory
3. **Start developing** - Make your first schema changes
4. **Commit your work** - Use git to track changes

## Getting Help

- **Setup issues**: Check Common Issues section above
- **Schema questions**: Examine `src/schema/` files
- **Integration questions**: Coordinate with main app developer

## Architecture Overview

```
┌─────────────────────────────────────────┐
│   Azure PostgreSQL Database             │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────┐  ┌──────────────┐ │
│  │ public schema   │  │ dev_v2       │ │
│  │ (main app)      │  │ (your work)  │ │
│  │                 │  │              │ │
│  │ • projects      │  │ • projects   │ │
│  │ • cost_breakdown│  │ • cost_...   │ │
│  │ • pos           │  │ • pos        │ │
│  └─────────────────┘  └──────────────┘ │
│                                         │
└─────────────────────────────────────────┘
         ▲                       ▲
         │                       │
    Main App                Your Work
  (untouched)            (isolated)
```

Your changes only affect `dev_v2` schema, the main app continues working with `public` schema.
