#!/bin/bash

# Script to introspect Supabase database and generate Drizzle schema
# 
# Usage:
#   1. Add DATABASE_URL to root .env.local:
#      DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
#   
#   2. Run this script:
#      ./scripts/introspect.sh

set -e

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
  echo "❌ ERROR: DATABASE_URL environment variable is not set"
  echo ""
  echo "Please add DATABASE_URL to your .env.local file:"
  echo "DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
  echo ""
  echo "You can find your connection string in Supabase Dashboard:"
  echo "Settings → Database → Connection string → URI"
  exit 1
fi

echo "🔍 Introspecting Supabase database..."
echo ""

# Run Drizzle introspection
pnpm drizzle-kit introspect

echo ""
echo "✅ Schema introspection complete!"
echo ""
echo "Generated files:"
echo "  - packages/db/src/schema/*.ts"
echo ""
echo "Next steps:"
echo "  1. Review generated schema files"
echo "  2. Run schema comparison: pnpm db:compare"
echo "  3. Update type exports if needed"
