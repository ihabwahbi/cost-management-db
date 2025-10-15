import { describe, it, expect } from 'vitest';
import {
  projects,
  costBreakdown,
  pos,
  poLineItems,
  poMappings,
  forecastVersions,
  budgetForecasts,
  type Project,
  type NewProject,
  type CostBreakdown,
  type PO,
  type POLineItem,
  type POMapping,
  type ForecastVersion,
  type BudgetForecast,
} from '../src/schema';

describe('Database Schema Validation', () => {
  describe('Projects Schema', () => {
    it('should have correct table name', () => {
      expect(projects).toBeDefined();
      // @ts-expect-error - accessing internal property for testing
      expect(projects[Symbol.for('drizzle:Name')]).toBe('projects');
    });

    it('should export correct TypeScript types', () => {
      // Type inference test - this will fail at compile time if types are wrong
      const mockProject: Project = {
        id: '123e4567-e89b-12d3-a456-426614174000',
        name: 'Test Project',
        subBusinessLine: 'Test BL',
        createdAt: new Date(),
        updatedAt: new Date(),
      };

      expect(mockProject).toBeDefined();
      expect(mockProject.id).toBe('123e4567-e89b-12d3-a456-426614174000');
    });

    it('should support NewProject type for inserts', () => {
      const newProject: NewProject = {
        name: 'New Project',
        subBusinessLine: 'New BL',
      };

      expect(newProject).toBeDefined();
      expect(newProject.name).toBe('New Project');
    });
  });

  describe('Cost Breakdown Schema', () => {
    it('should have correct table name', () => {
      expect(costBreakdown).toBeDefined();
      // @ts-expect-error - accessing internal property for testing
      expect(costBreakdown[Symbol.for('drizzle:Name')]).toBe('cost_breakdown');
    });

    it('should export correct TypeScript types', () => {
      const mockCostBreakdown: CostBreakdown = {
        id: '123e4567-e89b-12d3-a456-426614174000',
        projectId: '123e4567-e89b-12d3-a456-426614174001',
        subBusinessLine: 'Test BL',
        costLine: 'Labor',
        spendType: 'Internal',
        budgetCost: '100000.00',
        forecastCost: '95000.00',
        actualCost: '90000.00',
        createdAt: new Date(),
        updatedAt: new Date(),
      };

      expect(mockCostBreakdown).toBeDefined();
      expect(mockCostBreakdown.costLine).toBe('Labor');
    });
  });

  describe('PO Schema', () => {
    it('should have correct table name', () => {
      expect(pos).toBeDefined();
      // @ts-expect-error - accessing internal property for testing
      expect(pos[Symbol.for('drizzle:Name')]).toBe('pos');
    });

    it('should export correct TypeScript types', () => {
      const mockPO: PO = {
        id: '123e4567-e89b-12d3-a456-426614174000',
        poNumber: 'PO-2024-001',
        projectId: '123e4567-e89b-12d3-a456-426614174001',
        description: 'Test PO',
        totalAmount: '250000.00',
        currency: 'USD',
        status: 'approved',
        createdAt: new Date(),
        updatedAt: new Date(),
      };

      expect(mockPO).toBeDefined();
      expect(mockPO.poNumber).toBe('PO-2024-001');
    });
  });

  describe('PO Line Items Schema', () => {
    it('should have correct table name', () => {
      expect(poLineItems).toBeDefined();
      // @ts-expect-error - accessing internal property for testing
      expect(poLineItems[Symbol.for('drizzle:Name')]).toBe('po_line_items');
    });

    it('should export correct TypeScript types', () => {
      const mockLineItem: POLineItem = {
        id: '123e4567-e89b-12d3-a456-426614174000',
        poId: '123e4567-e89b-12d3-a456-426614174001',
        lineNumber: 1,
        description: 'Test Line Item',
        quantity: '10',
        unitPrice: '1000.00',
        totalPrice: '10000.00',
        createdAt: new Date(),
        updatedAt: new Date(),
      };

      expect(mockLineItem).toBeDefined();
      expect(mockLineItem.lineNumber).toBe(1);
    });
  });

  describe('PO Mappings Schema', () => {
    it('should have correct table name', () => {
      expect(poMappings).toBeDefined();
      // @ts-expect-error - accessing internal property for testing
      expect(poMappings[Symbol.for('drizzle:Name')]).toBe('po_mappings');
    });

    it('should export correct TypeScript types', () => {
      const mockMapping: POMapping = {
        id: '123e4567-e89b-12d3-a456-426614174000',
        poLineItemId: '123e4567-e89b-12d3-a456-426614174001',
        costBreakdownId: '123e4567-e89b-12d3-a456-426614174002',
        mappedAmount: '5000.00',
        createdAt: new Date(),
        updatedAt: new Date(),
      };

      expect(mockMapping).toBeDefined();
      expect(mockMapping.mappedAmount).toBe('5000.00');
    });
  });

  describe('Forecast Versions Schema', () => {
    it('should have correct table name', () => {
      expect(forecastVersions).toBeDefined();
      // @ts-expect-error - accessing internal property for testing
      expect(forecastVersions[Symbol.for('drizzle:Name')]).toBe('forecast_versions');
    });

    it('should export correct TypeScript types', () => {
      const mockVersion: ForecastVersion = {
        id: '123e4567-e89b-12d3-a456-426614174000',
        projectId: '123e4567-e89b-12d3-a456-426614174001',
        versionName: 'Q1 2024 Forecast',
        createdAt: new Date(),
        createdBy: 'user@example.com',
      };

      expect(mockVersion).toBeDefined();
      expect(mockVersion.versionName).toBe('Q1 2024 Forecast');
    });
  });

  describe('Budget Forecasts Schema', () => {
    it('should have correct table name', () => {
      expect(budgetForecasts).toBeDefined();
      // @ts-expect-error - accessing internal property for testing
      expect(budgetForecasts[Symbol.for('drizzle:Name')]).toBe('budget_forecasts');
    });

    it('should export correct TypeScript types', () => {
      const mockForecast: BudgetForecast = {
        id: '123e4567-e89b-12d3-a456-426614174000',
        versionId: '123e4567-e89b-12d3-a456-426614174001',
        costBreakdownId: '123e4567-e89b-12d3-a456-426614174002',
        forecastedAmount: '75000.00',
        notes: 'Updated forecast based on Q1 actuals',
        createdAt: new Date(),
      };

      expect(mockForecast).toBeDefined();
      expect(mockForecast.forecastedAmount).toBe('75000.00');
    });
  });

  describe('Schema Exports', () => {
    it('should export all required table schemas', () => {
      expect(projects).toBeDefined();
      expect(costBreakdown).toBeDefined();
      expect(pos).toBeDefined();
      expect(poLineItems).toBeDefined();
      expect(poMappings).toBeDefined();
      expect(forecastVersions).toBeDefined();
      expect(budgetForecasts).toBeDefined();
    });

    it('should export all required type definitions', () => {
      // This is validated at compile time - if types are missing, TypeScript will error
      const types = {
        Project: {} as Project,
        NewProject: {} as NewProject,
        CostBreakdown: {} as CostBreakdown,
        PO: {} as PO,
        POLineItem: {} as POLineItem,
        POMapping: {} as POMapping,
        ForecastVersion: {} as ForecastVersion,
        BudgetForecast: {} as BudgetForecast,
      };

      expect(types).toBeDefined();
    });
  });
});
