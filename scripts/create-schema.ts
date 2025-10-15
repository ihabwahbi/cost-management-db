import postgres from 'postgres';

const sql = postgres(process.env.DATABASE_URL!, {
  ssl: 'require',
  max: 1,
});

async function createSchema() {
  try {
    console.log('Creating dev_v2 schema...');
    await sql`CREATE SCHEMA IF NOT EXISTS dev_v2`;
    console.log('✓ Schema dev_v2 created successfully');
  } catch (error) {
    console.error('Error creating schema:', error);
    throw error;
  } finally {
    await sql.end();
  }
}

createSchema();
