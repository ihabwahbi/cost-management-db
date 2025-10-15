import postgres from 'postgres';

const sql = postgres(process.env.DATABASE_URL!, {
  ssl: 'require',
  max: 1,
});

async function dropSchema() {
  try {
    console.log('Dropping dev_v2 schema...');
    await sql`DROP SCHEMA IF EXISTS dev_v2 CASCADE`;
    await sql`CREATE SCHEMA dev_v2`;
    console.log('✓ Schema dev_v2 dropped successfully');
  } catch (error) {
    console.error('Error dropping schema:', error);
    throw error;
  } finally {
    await sql.end();
  }
}

dropSchema();
