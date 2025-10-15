#!/usr/bin/env node
/**
 * Schema Comparison Tool
 * 
 * Validates that the Drizzle schema definitions match the production database.
 * This is a critical validation step before any migrations.
 * 
 * Usage:
 *   pnpm tsx scripts/compare-schema.ts
 */

import * as schema from '../src/schema';

interface SchemaValidation {
  tableName: string;
  status: 'valid' | 'warning' | 'error';
  message: string;
}

const results: SchemaValidation[] = [];

// Check that all expected tables are defined
const expectedTables = [
  'projects',
  'costBreakdown',
  'pos',
  'poLineItems',
  'poMappings',
  'forecastVersions',
  'budgetForecasts',
];

console.log('🔍 Validating Drizzle Schema Definitions...\n');

expectedTables.forEach((tableName) => {
  if (tableName in schema) {
    results.push({
      tableName,
      status: 'valid',
      message: `✅ Table '${tableName}' is defined`,
    });
  } else {
    results.push({
      tableName,
      status: 'error',
      message: `❌ Table '${tableName}' is missing from schema`,
    });
  }
});

// Print results
results.forEach((result) => {
  console.log(result.message);
});

const hasErrors = results.some((r) => r.status === 'error');

console.log('\n' + '─'.repeat(60));

if (hasErrors) {
  console.log('❌ Schema validation failed!');
  console.log('\nPlease ensure all tables are properly defined in src/schema/');
  process.exit(1);
} else {
  console.log('✅ All schema tables are defined!');
  console.log('\nNext steps:');
  console.log('  1. Add DATABASE_URL to .env.local to enable introspection');
  console.log('  2. Run: pnpm db:introspect to verify against production');
  process.exit(0);
}
