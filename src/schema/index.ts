/**
 * Database schema definitions for dev_v3 schema
 * 
 * These schemas match the dev_v3 PostgreSQL database structure.
 */

export * from './_schema';

// Core tables
export * from './projects';
export * from './wbs-details';
export * from './cost-breakdown';
export * from './po-line-items';
export * from './pr-pre-mappings';  // Must be before po-mappings (dependency)
export * from './po-mappings';

// PO Operations & Transactions
export * from './po-operations';
export * from './po-transactions';
export * from './grir-exposures';

// SAP Integration
export * from './sap-reservations';

// Forecasting tables
export * from './forecast-versions';
export * from './budget-forecasts';

// Database views
export * from './v-project-financials';
export * from './v-po-mapping-detail';

// Webapp-only schemas (symlinked from cost-management)
// Included so db:drift from this project reports correct drift (no false DROP proposals)
export * from './users';
export * from './agent-memories';
export * from './pending-invites';
export * from './registration-attempts';
export * from './registration-audit-log';
export * from './webauthn-credentials';
export * from './webauthn-challenges';
