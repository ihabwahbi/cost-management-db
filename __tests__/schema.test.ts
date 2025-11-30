import { describe, it, expect } from 'vitest';
import {
  projects,
  costBreakdown,
  poLineItems,
  poMappings,
  forecastVersions,
  budgetForecasts,
  type Project,
  type NewProject,
  type CostBreakdown,
  type POLineItem,
  type NewPOLineItem,
  type POMapping,
  type ForecastVersion,
  type BudgetForecast,
} from '../src/schema';

// Helper to access Drizzle internal table name
const getTableName = (table: unknown): string => {
  return (table as Record<symbol, string>)[Symbol.for('drizzle:Name')] ?? '';
};

describe('Database Schema Validation', () => {
  describe('Projects Schema', () => {
    it('should have correct table name', () => {
      expect(projects).toBeDefined();
      expect(getTableName(projects)).toBe('projects');
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
      expect(getTableName(costBreakdown)).toBe('cost_breakdown');
    });

    it('should export correct TypeScript types', () => {
      const mockCostBreakdown: CostBreakdown = {
        id: '123e4567-e89b-12d3-a456-426614174000',
        projectId: '123e4567-e89b-12d3-a456-426614174001',
        subBusinessLine: 'Test BL',
        costLine: 'Labor',
        spendType: 'Internal',
        spendSubCategory: 'Direct Labor',
        budgetCost: '100000.00',
        createdAt: new Date(),
        updatedAt: new Date(),
      };

      expect(mockCostBreakdown).toBeDefined();
      expect(mockCostBreakdown.costLine).toBe('Labor');
    });
  });

  describe('PO Line Items Schema', () => {
    it('should have correct table name', () => {
      expect(poLineItems).toBeDefined();
      expect(getTableName(poLineItems)).toBe('po_line_items');
    });

    it('should export correct TypeScript types', () => {
      const mockLineItem: POLineItem = {
        id: '123e4567-e89b-12d3-a456-426614174000',
        poLineId: 'PO-2024-001-10',
        poNumber: 'PO-2024-001',
        poCreationDate: '2024-01-15',
        plantCode: '1000',
        location: 'Houston',
        subBusinessLine: 'OFS',
        prNumber: 'PR-2024-100',
        prLine: 10,
        requester: 'John Doe',
        vendorId: 'V001',
        vendorName: 'Test Vendor',
        vendorCategory: 'GLD',
        ultimateVendorName: 'Parent Corp',
        lineItemNumber: 10,
        partNumber: 'PART-001',
        description: 'Test Line Item',
        orderedQty: '100',
        orderUnit: 'EA',
        poValueUsd: '10000.00',
        accountAssignmentCategory: 'K',
        nisLine: 'Materials',
        wbsNumber: null,
        assetCode: null,
        expectedDeliveryDate: '2024-02-15',
        poApprovalStatus: 'Approved',
        poReceiptStatus: 'Open',
        poGtsStatus: null,
        fmtPo: false,
        openPoQty: '50',
        openPoValue: '5000.00',
        createdAt: new Date(),
        updatedAt: new Date(),
      };

      expect(mockLineItem).toBeDefined();
      expect(mockLineItem.lineItemNumber).toBe(10);
    });

    it('should support NewPOLineItem type for inserts', () => {
      const newLineItem: NewPOLineItem = {
        poLineId: 'PO-2024-002-10',
        poNumber: 'PO-2024-002',
        lineItemNumber: 10,
        orderedQty: '50',
        poValueUsd: '5000.00',
        fmtPo: false,
      };

      expect(newLineItem).toBeDefined();
      expect(newLineItem.poLineId).toBe('PO-2024-002-10');
    });
  });

  describe('PO Mappings Schema', () => {
    it('should have correct table name', () => {
      expect(poMappings).toBeDefined();
      expect(getTableName(poMappings)).toBe('po_mappings');
    });

    it('should export correct TypeScript types', () => {
      const mockMapping: POMapping = {
        id: '123e4567-e89b-12d3-a456-426614174000',
        poLineItemId: '123e4567-e89b-12d3-a456-426614174001',
        costBreakdownId: '123e4567-e89b-12d3-a456-426614174002',
        mappedAmount: '5000.00',
        mappingNotes: 'Mapped for Q1 forecast',
        mappedBy: 'admin@example.com',
        mappedAt: new Date(),
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
      expect(getTableName(forecastVersions)).toBe('forecast_versions');
    });

    it('should export correct TypeScript types', () => {
      const mockVersion: ForecastVersion = {
        id: '123e4567-e89b-12d3-a456-426614174000',
        projectId: '123e4567-e89b-12d3-a456-426614174001',
        versionNumber: 1,
        reasonForChange: 'Initial Q1 2024 Forecast',
        createdAt: new Date(),
        createdBy: 'user@example.com',
      };

      expect(mockVersion).toBeDefined();
      expect(mockVersion.versionNumber).toBe(1);
    });
  });

  describe('Budget Forecasts Schema', () => {
    it('should have correct table name', () => {
      expect(budgetForecasts).toBeDefined();
      expect(getTableName(budgetForecasts)).toBe('budget_forecasts');
    });

    it('should export correct TypeScript types', () => {
      const mockForecast: BudgetForecast = {
        id: '123e4567-e89b-12d3-a456-426614174000',
        forecastVersionId: '123e4567-e89b-12d3-a456-426614174001',
        costBreakdownId: '123e4567-e89b-12d3-a456-426614174002',
        forecastedCost: '75000.00',
        createdAt: new Date(),
      };

      expect(mockForecast).toBeDefined();
      expect(mockForecast.forecastedCost).toBe('75000.00');
    });
  });

  describe('Schema Exports', () => {
    it('should export all required table schemas', () => {
      expect(projects).toBeDefined();
      expect(costBreakdown).toBeDefined();
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
        POLineItem: {} as POLineItem,
        NewPOLineItem: {} as NewPOLineItem,
        POMapping: {} as POMapping,
        ForecastVersion: {} as ForecastVersion,
        BudgetForecast: {} as BudgetForecast,
      };

      expect(types).toBeDefined();
    });
  });
});
