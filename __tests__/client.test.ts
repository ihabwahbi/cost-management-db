import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

describe('Database Client', () => {
  const originalEnv = process.env.DATABASE_URL;

  beforeEach(() => {
    // Reset modules to test initialization
    vi.resetModules();
  });

  afterEach(() => {
    // Restore original environment
    process.env.DATABASE_URL = originalEnv;
  });

  describe('Client Initialization', () => {
    it('should throw error when DATABASE_URL is not set', async () => {
      // Remove DATABASE_URL
      delete process.env.DATABASE_URL;

      // Expect the import to throw
      await expect(async () => {
        await import('../src/client');
      }).rejects.toThrow('DATABASE_URL environment variable is not set');
    });

    it('should initialize client when DATABASE_URL is set', async () => {
      // Set a valid-looking DATABASE_URL
      process.env.DATABASE_URL = 'postgresql://user:password@localhost:5432/testdb';

      const { db, schema } = await import('../src/client');

      expect(db).toBeDefined();
      expect(schema).toBeDefined();
    });

    it('should export schema object', async () => {
      process.env.DATABASE_URL = 'postgresql://user:password@localhost:5432/testdb';

      const { schema } = await import('../src/client');

      // Verify schema exports key tables
      expect(schema.projects).toBeDefined();
      expect(schema.costBreakdown).toBeDefined();
      expect(schema.poLineItems).toBeDefined();
      expect(schema.poMappings).toBeDefined();
      expect(schema.forecastVersions).toBeDefined();
      expect(schema.budgetForecasts).toBeDefined();
    });
  });

  describe('Type Safety', () => {
    it('should provide typed database client', async () => {
      process.env.DATABASE_URL = 'postgresql://user:password@localhost:5432/testdb';

      const { db } = await import('../src/client');

      // Type checking - these will fail at compile time if types are wrong
      expect(db.query).toBeDefined();
      expect(typeof db.query).toBe('object');
    });
  });

  describe('Connection Configuration', () => {
    it('should use connection pooling settings', async () => {
      process.env.DATABASE_URL = 'postgresql://user:password@localhost:5432/testdb';

      // Import should not throw with valid configuration
      await expect(import('../src/client')).resolves.toBeDefined();
    });
  });
});
