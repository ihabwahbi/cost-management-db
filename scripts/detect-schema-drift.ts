#!/usr/bin/env npx tsx
/**
 * Schema Drift Detection Tool
 * 
 * Compares local Drizzle schema definitions against the live database
 * and reports differences WITHOUT applying any changes.
 * 
 * This is the safe alternative to `db:push`. Changes should be applied
 * manually via SQL (e.g., through a database MCP tool or psql).
 * 
 * Exit codes:
 *   0 — No drift detected (schemas match)
 *   1 — Drift detected (shows SQL statements needed)
 *   2 — Error (connection failure, etc.)
 * 
 * Usage:
 *   npm run db:drift          # Human-readable output
 *   npm run db:drift:sql      # Output raw SQL only (for piping)
 *   npm run db:drift:json     # Output JSON (for CI)
 */

import 'dotenv/config';
import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import { pushSchema } from 'drizzle-kit/api';
import * as schema from '../src/schema';

const SCHEMA_FILTER = ['dev_v3'];

/**
 * The pushSchema() API internally calls db.execute(sql.raw(query))
 * and expects the result to have a `.rows` property.
 * 
 * With the postgres-js driver, execute() returns a plain array.
 * This proxy wraps the result so `.rows` returns the array itself.
 */
function wrapDrizzleForPush(db: ReturnType<typeof drizzle>) {
  return new Proxy(db, {
    get(target, prop, receiver) {
      if (prop === 'execute') {
        return async (...args: unknown[]) => {
          // @ts-expect-error - proxy forwarding
          const result = await target.execute(...args);
          // Attach .rows if not already present (postgres-js returns plain array)
          if (Array.isArray(result) && !('rows' in result)) {
            Object.defineProperty(result, 'rows', { value: result, enumerable: false });
          }
          return result;
        };
      }
      return Reflect.get(target, prop, receiver);
    },
  });
}

async function main() {
  const args = process.argv.slice(2);
  const sqlOnly = args.includes('--sql');
  const jsonOutput = args.includes('--json');

  // Validate environment
  const connectionString = process.env.DATABASE_URL;
  if (!connectionString) {
    console.error('ERROR: DATABASE_URL environment variable is not set.');
    process.exit(2);
  }

  // Connect to database (read-only intent — we never call apply())
  const client = postgres(connectionString, {
    max: 1,
    idle_timeout: 10,
    connect_timeout: 10,
  });

  const db = wrapDrizzleForPush(drizzle(client, { schema }));

  try {
    // Compare local schema against live database
    // extensionsFilters: ['postgis'] prevents drizzle from choking on extension types
    const result = await pushSchema(schema, db as any, SCHEMA_FILTER, undefined, ['postgis']);

    const { hasDataLoss, warnings, statementsToExecute } = result;
    // NOTE: We intentionally never call result.apply()

    // Filter out empty statements
    const statements = statementsToExecute.filter((s) => s.trim().length > 0);

    if (jsonOutput) {
      // Machine-readable output for CI
      console.log(JSON.stringify({
        hasDrift: statements.length > 0,
        hasDataLoss,
        warnings,
        statements,
        statementCount: statements.length,
      }, null, 2));
    } else if (sqlOnly) {
      // Raw SQL output (for piping to psql or review)
      if (statements.length === 0) {
        // Nothing to output
      } else {
        statements.forEach((stmt) => {
          console.log(stmt.endsWith(';') ? stmt : `${stmt};`);
        });
      }
    } else {
      // Human-readable output
      console.log('Schema Drift Detection');
      console.log('='.repeat(60));
      console.log(`Schema filter: ${SCHEMA_FILTER.join(', ')}`);
      console.log('');

      if (statements.length === 0) {
        console.log('No drift detected — local schema matches the database.');
      } else {
        console.log(`Drift detected: ${statements.length} statement(s) needed\n`);

        if (hasDataLoss) {
          console.log('WARNING: Some changes involve potential DATA LOSS:');
          warnings.forEach((w) => console.log(`  - ${w}`));
          console.log('');
        }

        console.log('SQL statements to bring DB in sync with local schema:');
        console.log('-'.repeat(60));
        statements.forEach((stmt, i) => {
          console.log(`\n-- [${i + 1}/${statements.length}]`);
          console.log(stmt.endsWith(';') ? stmt : `${stmt};`);
        });
        console.log('\n' + '-'.repeat(60));
        console.log('\nReview these statements carefully, then apply manually.');
        console.log('DO NOT use db:push — apply via SQL tool or psql.');
      }
    }

    await client.end();

    // Exit code: 0 = no drift, 1 = drift found
    process.exit(statements.length > 0 ? 1 : 0);

  } catch (error) {
    console.error('ERROR: Failed to detect schema drift:', error);
    await client.end();
    process.exit(2);
  }
}

main();
