import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema';

/**
 * Database client for Supabase PostgreSQL
 * Uses connection pooling for optimal performance
 */
const connectionString = process.env.DATABASE_URL;

if (!connectionString) {
  throw new Error(
    'DATABASE_URL environment variable is not set. Please add it to your .env.local file.'
  );
}

// Create PostgreSQL client
const client = postgres(connectionString, {
  max: 10,
  idle_timeout: 20,
  connect_timeout: 10,
});

// Create Drizzle ORM instance with schema
export const db = drizzle(client, { schema });

// Export schema for direct access
export { schema };
