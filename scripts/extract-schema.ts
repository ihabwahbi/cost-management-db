/**
 * TypeScript Schema Extractor (using ts-morph AST)
 * 
 * Extracts database schema information from Drizzle ORM schema files
 * using proper TypeScript AST parsing via ts-morph.
 * 
 * Usage: npx ts-node scripts/extract-schema.ts
 * Output: JSON to stdout
 */

import { Project, SyntaxKind, PropertyAssignment } from 'ts-morph';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

// ESM-compatible __dirname equivalent
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

interface ColumnInfo {
  name: string;
  type: string;
  primary_key?: boolean;
  not_null?: boolean;
  references?: string;
  has_default?: boolean;
  unique?: boolean;
}

interface TableInfo {
  name: string;
  file: string;
  columns: ColumnInfo[];
  extraction_method: string;
}

const SCHEMA_DIR = join(__dirname, '..', 'src', 'schema');

// Drizzle column type functions we recognize
const DRIZZLE_TYPES = new Set([
  'uuid', 'varchar', 'text', 'numeric', 'integer', 'date', 
  'timestamp', 'boolean', 'serial', 'bigint', 'real', 'json', 'jsonb'
]);

function extractTables(): TableInfo[] {
  const tables: TableInfo[] = [];
  
  // Create a ts-morph project
  const project = new Project({
    skipAddingFilesFromTsConfig: true,
  });
  
  // Add schema files
  const schemaFiles = project.addSourceFilesAtPaths(
    join(SCHEMA_DIR, '*.ts')
  );
  
  for (const sourceFile of schemaFiles) {
    const fileName = sourceFile.getBaseName();
    
    // Skip utility files
    if (fileName === '_schema.ts' || fileName === 'index.ts') {
      continue;
    }
    
    // Find all call expressions that are .table() calls
    const callExpressions = sourceFile.getDescendantsOfKind(SyntaxKind.CallExpression);
    
    for (const call of callExpressions) {
      const callText = call.getExpression().getText();
      
      // Look for .table('table_name', { ... }) pattern
      if (callText.endsWith('.table')) {
        const args = call.getArguments();
        if (args.length < 2) continue;
        
        // First argument is table name (string literal)
        const tableNameArg = args[0];
        let tableName: string | null = null;
        
        if (tableNameArg.getKind() === SyntaxKind.StringLiteral) {
          tableName = tableNameArg.getText().replace(/['"]/g, '');
        }
        
        if (!tableName) continue;
        
        // Second argument is the column definitions object
        const columnsArg = args[1];
        const columns: ColumnInfo[] = [];
        
        if (columnsArg.getKind() === SyntaxKind.ObjectLiteralExpression) {
          const objLiteral = columnsArg.asKind(SyntaxKind.ObjectLiteralExpression);
          if (!objLiteral) continue;
          
          // Each property is a column definition
          for (const prop of objLiteral.getProperties()) {
            if (prop.getKind() !== SyntaxKind.PropertyAssignment) continue;
            
            const propAssign = prop as PropertyAssignment;
            const colName = propAssign.getName();
            const initializer = propAssign.getInitializer();
            
            if (!initializer) continue;
            
            const initText = initializer.getText();
            const colInfo: ColumnInfo = {
              name: colName,
              type: 'unknown',
            };
            
            // Find the column type (e.g., uuid(), varchar(), etc.)
            for (const typeName of DRIZZLE_TYPES) {
              // Match type function call like uuid( or varchar(
              const typePattern = new RegExp(`\\b${typeName}\\s*\\(`);
              if (typePattern.test(initText)) {
                colInfo.type = typeName;
                break;
              }
            }
            
            // Check for modifiers in the chain
            if (initText.includes('.primaryKey()')) {
              colInfo.primary_key = true;
            }
            if (initText.includes('.notNull()')) {
              colInfo.not_null = true;
            }
            if (initText.includes('.unique()')) {
              colInfo.unique = true;
            }
            if (initText.includes('.default(')) {
              colInfo.has_default = true;
            }
            
            // Check for references - look for .references(() => tableName.columnName)
            const refMatch = initText.match(/\.references\s*\(\s*\(\s*\)\s*=>\s*(\w+)\.(\w+)/);
            if (refMatch) {
              colInfo.references = `${refMatch[1]}.${refMatch[2]}`;
            }
            
            columns.push(colInfo);
          }
        }
        
        tables.push({
          name: tableName,
          file: fileName,
          columns: columns,
          extraction_method: 'ts-morph-ast',
        });
      }
    }
  }
  
  return tables;
}

// Main execution
try {
  const tables = extractTables();
  console.log(JSON.stringify(tables, null, 2));
} catch (error) {
  console.error(JSON.stringify({ error: String(error) }));
  process.exit(1);
}
