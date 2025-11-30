# Pipeline Map v2: The Context Oracle

**Goal**: Build the world's best "Intelligence Layer" for AI coding agents - a system that transforms blind file operations into guided, verified, consistent code changes at any scale.

**Core Problem**: The agent already has tools (glob, grep, read, write). What it lacks is:
- **Knowledge of what exists** → Causes hallucinations
- **Knowledge of conventions** → Causes code drift  
- **Knowledge of impact** → Causes regressions
- **Knowledge of where to look** → Causes wasted tokens

**Solution**: The **Context Oracle** - An active guidance system with three pillars:
1. **Symbol Registry** - Verify before use (anti-hallucination)
2. **Pattern Library** - Follow conventions (anti-drift)
3. **Lineage Oracle** - Know impact (guided search)

---

# REVISED ARCHITECTURE: The Context Oracle

## The Intelligence Layer Concept

```
┌─────────────────────────────────────────────────────────────┐
│                     AI CODING AGENT                         │
│  (Has: glob, ripgrep, read, write, bash)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   CONTEXT ORACLE                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   SYMBOL    │  │   PATTERN   │  │   LINEAGE   │        │
│  │  REGISTRY   │  │   LIBRARY   │  │   ORACLE    │        │
│  │             │  │             │  │             │        │
│  │ • verify()  │  │ • match()   │  │ • trace()   │        │
│  │ • lookup()  │  │ • suggest() │  │ • impact()  │        │
│  │ • similar() │  │ • enforce() │  │ • rank()    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      CODEBASE                               │
│  (1000s of files - Python, TypeScript, SQL, etc.)          │
└─────────────────────────────────────────────────────────────┘
```

## How It Transforms Agent Behavior

| Without Oracle | With Oracle |
|----------------|-------------|
| `grep "calculate"` → 500 results | `trace_lineage("cost_impact")` → 3 relevant files |
| Writes `utils.format_date()` (doesn't exist) | `verify_symbol("format_date")` → "Did you mean `date_utils.format_iso()`?" |
| Creates new pattern for logging | `get_pattern("logging")` → Returns existing `logger.info()` convention |
| Edits file, breaks 5 others | `predict_impact("06_prepare.py")` → "Warning: 3 downstream scripts depend on this" |

---

## PILLAR 1: Symbol Registry (Anti-Hallucination)

### Problem
Agent writes `from utils import calculate_tax` but `calculate_tax` doesn't exist. Or it calls `df.merge(on="po_id")` but the column is actually `PO Line ID`.

### Solution
A **verified symbol index** that the agent MUST query before referencing any symbol.

### Implementation

#### 1.1 Symbol Index Structure

```python
# pipeline-context/registry/symbols.json
{
  "functions": {
    "filter_valuation_classes": {
      "file": "scripts/stage1_clean/01_po_line_items.py",
      "line": 42,
      "signature": "def filter_valuation_classes(df: pd.DataFrame) -> pd.DataFrame",
      "docstring": "Remove rows with excluded PO Valuation Classes.",
      "calls": ["pd.to_numeric", "isin"],
      "called_by": ["main"]
    },
    "calculate_gr_amount": {
      "file": "scripts/stage1_clean/02_gr_postings.py",
      "line": 43,
      "signature": "def calculate_gr_amount(df: pd.DataFrame) -> pd.DataFrame",
      "docstring": "Calculate GR Amount based on unit price from PO Line Items.",
      "calls": ["pd.read_csv", "merge"],
      "called_by": ["main"]
    }
  },
  "columns": {
    "PO Line ID": {
      "sources": ["data/raw/po line items.csv", "data/raw/gr table.csv"],
      "dtype": "object",
      "used_in": ["01_po_line_items.py", "02_gr_postings.py", "03_ir_postings.py"]
    },
    "cost_impact_amount": {
      "sources": ["data/intermediate/cost_impact.csv"],
      "dtype": "float64",
      "created_by": "05_calculate_cost_impact.py:159"
    }
  },
  "constants": {
    "EXCLUDED_VALUATION_CLASSES": {
      "file": "scripts/config/column_mappings.py",
      "line": 164,
      "value": "[7800, 7900, 5008]"
    }
  },
  "tables": {
    "po_line_items": {
      "file": "src/schema/po-line-items.ts",
      "columns": ["id", "poLineId", "poNumber", "..."]
    }
  }
}
```

#### 1.2 MCP Tools

```typescript
// Tool: verify_symbol
// CRITICAL: Agent should call this BEFORE writing any code that references a symbol
interface VerifySymbolParams {
  name: string;           // Symbol to verify
  type?: string;          // "function" | "column" | "constant" | "table" | "any"
}

interface VerifySymbolResponse {
  exists: boolean;
  location?: string;      // "file:line"
  signature?: string;
  suggestion?: string;    // If not found, suggest similar symbols
}

// Example usage by agent:
// Before writing: df.merge(on="po_id")
// Agent calls: verify_symbol({name: "po_id", type: "column"})
// Response: {exists: false, suggestion: "Did you mean 'PO Line ID'?"}

// Tool: lookup_signature
// Get full signature before calling a function
interface LookupSignatureParams {
  function_name: string;
}

interface LookupSignatureResponse {
  signature: string;
  docstring: string;
  file: string;
  line: number;
  example_call?: string;
}

// Tool: find_similar
// Fuzzy search when agent isn't sure of exact name
interface FindSimilarParams {
  query: string;
  type?: string;
  limit?: number;
}
```

#### 1.3 Validation Gate

```python
# The agent's workflow MUST include verification
class AgentWorkflow:
    def before_write(self, code: str) -> ValidationResult:
        """Validate code before writing to file."""
        # Extract all symbol references from code
        symbols = self.extract_symbols(code)
        
        errors = []
        for symbol in symbols:
            result = self.oracle.verify_symbol(symbol)
            if not result.exists:
                errors.append(f"Unknown symbol: {symbol}. {result.suggestion}")
        
        if errors:
            return ValidationResult(valid=False, errors=errors)
        return ValidationResult(valid=True)
```

---

## PILLAR 2: Pattern Library (Anti-Drift)

### Problem
Agent creates new code that works but doesn't follow existing patterns:
- Uses `print()` instead of project's logging pattern
- Creates a new schema file with different structure than existing ones
- Writes data cleaning code differently from existing pipeline scripts

### Solution
A **pattern matching system** that finds existing code similar to what the agent is about to write.

### Implementation

#### 2.1 Pattern Index Structure

```python
# pipeline-context/patterns/index.json
{
  "patterns": {
    "pipeline_script": {
      "description": "Pattern for data pipeline transformation scripts",
      "template": "scripts/stage1_clean/01_po_line_items.py",
      "structure": [
        "Module docstring with Dependencies/Input/Output",
        "Constants at top",
        "load_data() function",
        "transformation functions",
        "save_data() function", 
        "main() orchestrator",
        "if __name__ == '__main__' guard"
      ],
      "examples": [
        "scripts/stage1_clean/01_po_line_items.py",
        "scripts/stage1_clean/02_gr_postings.py",
        "scripts/stage2_transform/04_enrich_po_line_items.py"
      ]
    },
    "drizzle_schema": {
      "description": "Pattern for Drizzle ORM table definitions",
      "template": "src/schema/po-line-items.ts",
      "structure": [
        "Import devV3Schema from ./_schema",
        "Export const tableName = devV3Schema.table('snake_case', {...})",
        "Use uuid().primaryKey().defaultRandom() for id",
        "Add createdAt/updatedAt timestamps",
        "Export type TableName = typeof tableName.$inferSelect"
      ],
      "examples": [
        "src/schema/po-line-items.ts",
        "src/schema/po-transactions.ts",
        "src/schema/projects.ts"
      ]
    },
    "column_mapping": {
      "description": "Pattern for CSV to DB column mappings",
      "template": "scripts/config/column_mappings.py",
      "structure": [
        "Dict with CSV column name as key, snake_case DB column as value",
        "Group by category with comments",
        "Include commented-out columns for future reference"
      ]
    },
    "data_filtering": {
      "description": "Pattern for filtering DataFrame rows",
      "template_code": """
def filter_{what}(df: pd.DataFrame) -> pd.DataFrame:
    \"\"\"Remove rows with {condition}.\"\"\"
    initial_count = len(df)
    mask = {mask_expression}
    df_filtered = df[mask].copy()
    removed_count = initial_count - len(df_filtered)
    print(f"  Removed {removed_count:,} rows with {reason}")
    return df_filtered
""",
      "examples": [
        "01_po_line_items.py:filter_valuation_classes",
        "01_po_line_items.py:filter_nis_levels",
        "02_gr_postings.py:filter_zero_quantity"
      ]
    }
  }
}
```

#### 2.2 MCP Tools

```typescript
// Tool: get_pattern
// Agent calls this BEFORE writing new code to get the established pattern
interface GetPatternParams {
  task: string;           // "add_pipeline_script" | "add_schema_table" | "filter_data" | etc.
  context?: string;       // Additional context about what agent is doing
}

interface GetPatternResponse {
  pattern_name: string;
  description: string;
  template_code?: string;
  structure: string[];
  examples: Array<{
    file: string;
    relevant_lines: string;  // The actual code to follow
  }>;
  conventions: string[];    // Specific rules to follow
}

// Tool: find_similar_code
// Find existing code similar to what agent wants to write
interface FindSimilarCodeParams {
  description: string;    // "function that filters rows based on column value"
  code_snippet?: string;  // Optional: code agent is about to write
}

interface FindSimilarCodeResponse {
  matches: Array<{
    file: string;
    function_name: string;
    similarity_score: number;
    code: string;
  }>;
  recommendation: string;  // "Follow the pattern in 01_po_line_items.py:filter_valuation_classes"
}

// Tool: validate_consistency
// Check if new code follows established patterns
interface ValidateConsistencyParams {
  file_path: string;
  new_code: string;
}

interface ValidateConsistencyResponse {
  consistent: boolean;
  violations: Array<{
    rule: string;
    expected: string;
    actual: string;
    suggestion: string;
  }>;
}
```

#### 2.3 Pattern Enforcement Example

```python
# Agent wants to add a new pipeline script
# BEFORE writing, agent calls:
pattern = oracle.get_pattern(task="add_pipeline_script")

# Response includes:
{
  "pattern_name": "pipeline_script",
  "structure": ["Module docstring...", "Constants...", "load_data()...", ...],
  "examples": [
    {
      "file": "scripts/stage1_clean/01_po_line_items.py",
      "relevant_lines": """
\"\"\"
Stage 1: Clean PO Line Items

Dependencies: None (first script in pipeline)
Input: data/raw/po line items.csv
Output: data/intermediate/po_line_items.csv
\"\"\"

from pathlib import Path
import pandas as pd
...
"""
    }
  ],
  "conventions": [
    "Use PROJECT_ROOT for all file paths",
    "Print progress messages with emoji-free format",
    "Return DataFrame from transformation functions",
    "Use .copy() when filtering to avoid SettingWithCopyWarning"
  ]
}
```

---

## PILLAR 3: Lineage Oracle (Guided Search + Impact Analysis)

### Problem
- Agent runs `ripgrep "cost"` → gets 500 results, wastes tokens reading irrelevant files
- Agent modifies `05_calculate_cost_impact.py` without knowing it breaks `06_prepare_po_line_items.py`
- Agent doesn't know which files to edit for "fix the open PO value calculation"

### Solution
A **data lineage graph** that traces how data flows through the system and predicts impact of changes.

### Implementation

#### 3.1 Lineage Graph Structure

```python
# pipeline-context/lineage/graph.json
{
  "nodes": {
    "raw:po_line_items.csv": {
      "type": "file",
      "stage": "raw",
      "columns": ["PO Line ID", "PO Number", "Purchase Value USD", "..."]
    },
    "script:01_po_line_items": {
      "type": "script",
      "stage": "stage1_clean",
      "file": "scripts/stage1_clean/01_po_line_items.py"
    },
    "column:open_po_value": {
      "type": "column",
      "dtype": "float64",
      "created_in": "script:06_prepare_po_line_items",
      "formula": "po_value_usd - sum(cost_impact_amount)"
    },
    "table:po_line_items": {
      "type": "db_table",
      "schema": "src/schema/po-line-items.ts"
    }
  },
  "edges": [
    {
      "from": "raw:po_line_items.csv",
      "to": "script:01_po_line_items",
      "type": "INPUT"
    },
    {
      "from": "script:01_po_line_items",
      "to": "intermediate:po_line_items.csv",
      "type": "OUTPUT"
    },
    {
      "from": "column:Purchase Value USD",
      "to": "column:po_value_usd",
      "type": "RENAMED",
      "location": "script:06_prepare_po_line_items:95"
    },
    {
      "from": "column:po_value_usd",
      "to": "column:open_po_value",
      "type": "DERIVED",
      "operation": "po_value_usd - cost_impact_sum",
      "location": "script:06_prepare_po_line_items:78"
    },
    {
      "from": "column:open_po_value",
      "to": "table:po_line_items.openPoValue",
      "type": "MAPS_TO"
    }
  ]
}
```

#### 3.2 MCP Tools

```typescript
// Tool: trace_lineage
// Trace how a column/value flows through the pipeline
interface TraceLineageParams {
  target: string;         // Column name, file, or concept
  direction: "upstream" | "downstream" | "both";
}

interface TraceLineageResponse {
  target: string;
  upstream: Array<{
    node: string;
    relationship: string;
    location: string;
    operation?: string;
  }>;
  downstream: Array<{
    node: string;
    relationship: string;
    location: string;
  }>;
  critical_files: string[];  // Files agent MUST read/modify
}

// Example:
// Agent: "I need to fix how open_po_value is calculated"
// Agent calls: trace_lineage({target: "open_po_value", direction: "upstream"})
// Response:
{
  "target": "open_po_value",
  "upstream": [
    {"node": "po_value_usd", "relationship": "DERIVED", "location": "06_prepare_po_line_items.py:78", "operation": "po_value_usd - cost_impact_sum"},
    {"node": "cost_impact_amount", "relationship": "AGGREGATED", "location": "06_prepare_po_line_items.py:65"},
    {"node": "Purchase Value USD", "relationship": "SOURCE", "location": "raw/po line items.csv"}
  ],
  "critical_files": [
    "scripts/stage3_prepare/06_prepare_po_line_items.py",
    "scripts/stage2_transform/05_calculate_cost_impact.py"
  ]
}

// Tool: predict_impact
// Before modifying a file, predict what else might break
interface PredictImpactParams {
  file_path: string;
  change_description?: string;
}

interface PredictImpactResponse {
  direct_dependents: string[];     // Files that import/use this file
  data_dependents: string[];       // Files that use data produced by this file
  affected_columns: string[];      // Columns that might be affected
  affected_tables: string[];       // DB tables that might be affected
  risk_level: "low" | "medium" | "high";
  recommendation: string;
}

// Example:
// Agent calls: predict_impact({file_path: "scripts/stage2_transform/05_calculate_cost_impact.py"})
// Response:
{
  "direct_dependents": [],
  "data_dependents": [
    "scripts/stage3_prepare/06_prepare_po_line_items.py",
    "scripts/stage3_prepare/07_prepare_po_transactions.py"
  ],
  "affected_columns": ["cost_impact_qty", "cost_impact_amount", "open_po_value", "open_po_qty"],
  "affected_tables": ["po_line_items", "po_transactions"],
  "risk_level": "high",
  "recommendation": "Changes to cost impact calculation affect 4 columns and 2 DB tables. Test thoroughly."
}

// Tool: smart_search (replaces blind grep)
// Search with context awareness
interface SmartSearchParams {
  query: string;
  search_type: "exact" | "semantic" | "lineage";
}

interface SmartSearchResponse {
  results: Array<{
    file: string;
    line: number;
    code: string;
    relevance: "high" | "medium" | "low";
    reason: string;  // Why this is relevant
  }>;
  suggested_reading_order: string[];  // Optimal order to read files
}
```

---

## Phase 1: Code Skeletonization (Week 1)

### Objective
Generate compressed code representations that retain 100% of interface information while reducing token usage by 5-10x.

### Implementation

#### 1.1 Skeleton Generator (`scripts/generate_skeletons.py`)

```python
"""
Generates skeletonized versions of Python files.
Preserves: function signatures, class definitions, docstrings, type hints
Removes: implementation bodies (replaced with `...`)
"""

import ast
from pathlib import Path

class SkeletonTransformer(ast.NodeTransformer):
    """Transform AST to skeleton form."""
    
    def visit_FunctionDef(self, node):
        """Keep signature and docstring, replace body with `...`"""
        # Preserve decorators, name, args, returns, docstring
        new_body = []
        
        # Keep docstring if present
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            new_body.append(node.body[0])
        
        # Add ellipsis as body
        new_body.append(ast.Expr(value=ast.Constant(value=...)))
        
        node.body = new_body
        return node
    
    def visit_ClassDef(self, node):
        """Keep class structure, skeletonize methods."""
        self.generic_visit(node)
        return node

def generate_skeleton(source_code: str) -> str:
    """Generate skeleton from source code."""
    tree = ast.parse(source_code)
    transformer = SkeletonTransformer()
    skeleton_tree = transformer.visit(tree)
    return ast.unparse(skeleton_tree)
```

#### 1.2 Output Structure

```
pipeline-context/
├── skeletons/
│   ├── stage1_clean/
│   │   ├── 01_po_line_items.skeleton.py
│   │   ├── 02_gr_postings.skeleton.py
│   │   └── 03_ir_postings.skeleton.py
│   ├── stage2_transform/
│   │   └── ...
│   └── stage3_prepare/
│       └── ...
├── summaries/
│   ├── root.json          # Project-level summary
│   ├── stage1_clean.json  # Stage-level summary
│   └── ...
└── index/
    ├── symbols.json       # All function/class definitions
    └── dependencies.json  # Import/call relationships
```

#### 1.3 Example Output

**Original** (`01_po_line_items.py` - 173 lines):
```python
def filter_valuation_classes(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with excluded PO Valuation Classes."""
    initial_count = len(df)
    valuation_class = pd.to_numeric(df["PO Valuation Class"], errors="coerce")
    mask = ~valuation_class.isin(EXCLUDED_VALUATION_CLASSES)
    df_filtered = df[mask].copy()
    removed_count = initial_count - len(df_filtered)
    print(f"  Removed {removed_count:,} rows with Valuation Classes {EXCLUDED_VALUATION_CLASSES}")
    return df_filtered
```

**Skeleton** (`01_po_line_items.skeleton.py` - ~40 lines):
```python
def filter_valuation_classes(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with excluded PO Valuation Classes."""
    ...
```

#### 1.4 Integration with Pipeline Map

Add to `pipeline-map.json`:
```json
{
  "scripts": [{
    "name": "01_po_line_items",
    "skeleton_path": "pipeline-context/skeletons/stage1_clean/01_po_line_items.skeleton.py",
    "skeleton_tokens": 450,
    "full_tokens": 2100,
    "compression_ratio": 4.7
  }]
}
```

### Deliverables
- [ ] `scripts/generate_skeletons.py` - Skeleton generator
- [ ] `pipeline-context/skeletons/` - Generated skeletons
- [ ] Updated `generate_pipeline_map.py` to include skeleton metadata
- [ ] Pre-commit hook to regenerate skeletons on change

---

## Phase 2: Hierarchical Summaries (Week 2)

### Objective
Create multi-level summaries that allow agents to "zoom in" from project overview to specific code.

### Implementation

#### 2.1 Summary Levels

| Level | Scope | Token Budget | Content |
|-------|-------|--------------|---------|
| L0 | Project | ~200 | Project purpose, tech stack, entry points |
| L1 | Stage/Module | ~100 each | Stage purpose, script list, data flow |
| L2 | Script | ~50 each | Script purpose, key functions, I/O |
| L3 | Function | ~30 each | Signature + docstring + semantic flags |
| L4 | Code | Full | Actual implementation |

#### 2.2 Summary Generator (`scripts/generate_summaries.py`)

```python
"""
Generates hierarchical summaries for the codebase.
Uses LLM for semantic summarization (optional) or rule-based extraction.
"""

from dataclasses import dataclass
from typing import List, Dict

@dataclass
class ProjectSummary:
    """Level 0: Project overview"""
    name: str
    description: str
    tech_stack: List[str]
    entry_points: List[str]
    total_scripts: int
    total_lines: int

@dataclass  
class StageSummary:
    """Level 1: Stage/module overview"""
    name: str
    purpose: str
    scripts: List[str]
    inputs: List[str]
    outputs: List[str]
    
@dataclass
class ScriptSummary:
    """Level 2: Script overview"""
    name: str
    purpose: str  # First line of docstring
    functions: List[str]
    key_operations: List[str]  # e.g., ["filters rows", "joins data", "calculates values"]
    inputs: List[str]
    outputs: List[str]

@dataclass
class FunctionSummary:
    """Level 3: Function overview"""
    name: str
    signature: str
    docstring: str
    semantic_flags: Dict[str, bool]  # filters_data, joins_data, etc.
    line_number: int

def generate_project_summary(pipeline_map: dict) -> ProjectSummary:
    """Generate L0 summary from pipeline map."""
    return ProjectSummary(
        name=pipeline_map["project"],
        description=pipeline_map["description"],
        tech_stack=["Python", "Pandas", "Drizzle ORM", "PostgreSQL"],
        entry_points=["scripts/pipeline.py"],
        total_scripts=len(pipeline_map["scripts"]),
        total_lines=sum(s["line_count"] for s in pipeline_map["scripts"])
    )

def generate_stage_summaries(pipeline_map: dict) -> List[StageSummary]:
    """Generate L1 summaries for each stage."""
    stages = {}
    for script in pipeline_map["scripts"]:
        stage = script["stage"]
        if stage not in stages:
            stages[stage] = {
                "scripts": [],
                "inputs": set(),
                "outputs": set()
            }
        stages[stage]["scripts"].append(script["name"])
        stages[stage]["inputs"].update(script["inputs"])
        stages[stage]["outputs"].update(script["outputs"])
    
    return [
        StageSummary(
            name=stage,
            purpose=pipeline_map["pipeline_stages"][i]["description"] if i < len(pipeline_map["pipeline_stages"]) else "",
            scripts=data["scripts"],
            inputs=list(data["inputs"]),
            outputs=list(data["outputs"])
        )
        for i, (stage, data) in enumerate(stages.items())
    ]
```

#### 2.3 Output Format

**`pipeline-context/summaries/root.json`** (L0):
```json
{
  "level": 0,
  "name": "cost-management-db",
  "description": "Data pipeline for transforming raw PO/GR/IR data into PostgreSQL",
  "tech_stack": ["Python 3.11", "Pandas", "Drizzle ORM", "PostgreSQL"],
  "stages": ["stage1_clean", "stage2_transform", "stage3_prepare"],
  "entry_point": "python3 scripts/pipeline.py",
  "total_scripts": 7,
  "total_lines": 1100,
  "children": ["stage1_clean.json", "stage2_transform.json", "stage3_prepare.json"]
}
```

**`pipeline-context/summaries/stage1_clean.json`** (L1):
```json
{
  "level": 1,
  "name": "stage1_clean",
  "purpose": "Clean and filter raw CSV data, remove invalid rows, standardize formats",
  "scripts": [
    {"name": "01_po_line_items", "purpose": "Filter valuation classes, map vendors/locations"},
    {"name": "02_gr_postings", "purpose": "Calculate GR amounts from unit prices"},
    {"name": "03_ir_postings", "purpose": "Calculate invoice amounts from unit prices"}
  ],
  "data_flow": {
    "inputs": ["data/raw/*.csv"],
    "outputs": ["data/intermediate/*.csv"]
  },
  "children": ["01_po_line_items.json", "02_gr_postings.json", "03_ir_postings.json"]
}
```

### Deliverables
- [ ] `scripts/generate_summaries.py` - Summary generator
- [ ] `pipeline-context/summaries/` - Generated summaries at all levels
- [ ] Agent instruction: "Start with root.json, zoom into children as needed"

---

## Phase 3: MCP Query Tools (Week 3-4)

### Objective
Replace static context injection with dynamic query tools that agents can call on-demand.

### Implementation

#### 3.1 Tool Definitions

```typescript
// MCP Tool: search_codebase
interface SearchCodebaseParams {
  query: string;           // Natural language or code pattern
  scope?: string;          // "all" | "stage1" | "stage2" | "stage3" | file path
  search_type?: string;    // "semantic" | "keyword" | "hybrid"
  max_results?: number;    // Default 10
}

interface SearchResult {
  file: string;
  line_start: number;
  line_end: number;
  code_snippet: string;
  relevance_score: number;
  context: string;         // Function/class name containing this code
}

// MCP Tool: get_context_level
interface GetContextLevelParams {
  path: string;            // "root" | "stage1_clean" | "stage1_clean/01_po_line_items"
  level: number;           // 0-4, where 4 is full code
}

// MCP Tool: trace_data_lineage
interface TraceDataLineageParams {
  column_name: string;     // e.g., "open_po_value"
  direction: string;       // "forward" | "backward" | "both"
}

interface LineageNode {
  location: string;        // "script:line"
  operation: string;       // "created" | "modified" | "read" | "written"
  code_snippet: string;
  upstream: LineageNode[];
  downstream: LineageNode[];
}

// MCP Tool: get_symbol_info
interface GetSymbolInfoParams {
  symbol: string;          // Function/class/variable name
}

interface SymbolInfo {
  type: string;            // "function" | "class" | "variable" | "constant"
  defined_at: string;      // "file:line"
  signature?: string;
  docstring?: string;
  references: string[];    // List of "file:line" where used
  calls?: string[];        // For functions: what it calls
  called_by?: string[];    // For functions: what calls it
}

// MCP Tool: get_file_skeleton
interface GetFileSkeletonParams {
  path: string;
  include_private?: boolean;  // Include _underscore functions
}

// MCP Tool: read_code_range
interface ReadCodeRangeParams {
  path: string;
  start_line: number;
  end_line: number;
  expand_to_function?: boolean;  // Auto-expand to full function boundary
}
```

#### 3.2 Tool Implementation (`src/mcp-tools/`)

```python
# src/mcp-tools/search.py
"""
Hybrid search implementation combining:
1. BM25 (keyword) - Exact matches
2. Dense vectors (semantic) - Meaning-based
3. Graph queries (structural) - Relationships
"""

from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
import numpy as np

class HybridCodeSearch:
    def __init__(self, index_path: str):
        self.bm25_index = self._load_bm25(index_path)
        self.embedding_model = SentenceTransformer('jinaai/jina-embeddings-v2-base-code')
        self.vector_index = self._load_vectors(index_path)
        self.graph = self._load_graph(index_path)
    
    def search(self, query: str, search_type: str = "hybrid", k: int = 10) -> List[SearchResult]:
        if search_type == "keyword":
            return self._bm25_search(query, k)
        elif search_type == "semantic":
            return self._vector_search(query, k)
        else:  # hybrid
            bm25_results = self._bm25_search(query, k * 2)
            vector_results = self._vector_search(query, k * 2)
            return self._reciprocal_rank_fusion(bm25_results, vector_results, k)
    
    def _reciprocal_rank_fusion(self, results1, results2, k: int) -> List[SearchResult]:
        """Combine rankings using RRF formula: 1/(rank + 60)"""
        scores = {}
        for rank, result in enumerate(results1):
            scores[result.id] = scores.get(result.id, 0) + 1 / (rank + 60)
        for rank, result in enumerate(results2):
            scores[result.id] = scores.get(result.id, 0) + 1 / (rank + 60)
        
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [self._get_result(id) for id in sorted_ids[:k]]
```

#### 3.3 MCP Server (`src/mcp-server/index.ts`)

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server({
  name: "pipeline-context",
  version: "2.0.0",
}, {
  capabilities: {
    tools: {},
  },
});

// Register tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "search_codebase",
      description: "Search for code using natural language or patterns. Use this first to find relevant files.",
      inputSchema: {
        type: "object",
        properties: {
          query: { type: "string", description: "Search query" },
          scope: { type: "string", default: "all" },
          search_type: { type: "string", enum: ["semantic", "keyword", "hybrid"], default: "hybrid" },
          max_results: { type: "number", default: 10 }
        },
        required: ["query"]
      }
    },
    {
      name: "get_context_level",
      description: "Get summary at specified detail level. Start at level 0 (project), zoom to level 4 (full code).",
      inputSchema: {
        type: "object",
        properties: {
          path: { type: "string" },
          level: { type: "number", minimum: 0, maximum: 4 }
        },
        required: ["path", "level"]
      }
    },
    {
      name: "trace_data_lineage",
      description: "Trace how a data column flows through the pipeline. Essential for understanding transformations.",
      inputSchema: {
        type: "object",
        properties: {
          column_name: { type: "string" },
          direction: { type: "string", enum: ["forward", "backward", "both"], default: "both" }
        },
        required: ["column_name"]
      }
    },
    {
      name: "get_symbol_info",
      description: "Get detailed information about a function, class, or variable including all references.",
      inputSchema: {
        type: "object",
        properties: {
          symbol: { type: "string" }
        },
        required: ["symbol"]
      }
    },
    {
      name: "get_file_skeleton",
      description: "Get compressed view of a file showing only signatures and docstrings.",
      inputSchema: {
        type: "object",
        properties: {
          path: { type: "string" },
          include_private: { type: "boolean", default: false }
        },
        required: ["path"]
      }
    },
    {
      name: "read_code_range",
      description: "Read specific lines from a file. Use after search to get full implementation.",
      inputSchema: {
        type: "object",
        properties: {
          path: { type: "string" },
          start_line: { type: "number" },
          end_line: { type: "number" },
          expand_to_function: { type: "boolean", default: true }
        },
        required: ["path", "start_line", "end_line"]
      }
    }
  ]
}));
```

### Deliverables
- [ ] `src/mcp-tools/` - Tool implementations
- [ ] `src/mcp-server/` - MCP server
- [ ] `opencode.json` - MCP server configuration
- [ ] Documentation for agent usage patterns

---

## Phase 4: Code Knowledge Graph (Week 5-6)

### Objective
Build a queryable graph capturing all relationships in the codebase.

### Implementation

#### 4.1 Graph Schema

```
Nodes:
  - File(path, type, lines, last_modified)
  - Function(name, file, line, signature, docstring)
  - Class(name, file, line, docstring)
  - Column(name, source_file, dtype)
  - Table(name, schema_file)
  - Constant(name, value, file)

Edges:
  - DEFINES: File -> Function/Class/Constant
  - CALLS: Function -> Function
  - IMPORTS: File -> File
  - INHERITS: Class -> Class
  - TRANSFORMS: Column -> Column (with operation metadata)
  - READS: Function -> File
  - WRITES: Function -> File
  - MAPS_TO: Column -> Table.Column
  - REFERENCES: Function -> Column
```

#### 4.2 Graph Builder (`scripts/build_knowledge_graph.py`)

```python
"""
Builds a code knowledge graph using NetworkX for storage
and supports export to Neo4j/Memgraph for production.
"""

import ast
import networkx as nx
from pathlib import Path
from dataclasses import dataclass
from typing import Set, Dict, List

@dataclass
class GraphNode:
    id: str
    type: str
    properties: Dict

@dataclass
class GraphEdge:
    source: str
    target: str
    type: str
    properties: Dict

class CodeKnowledgeGraphBuilder:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.column_operations = []  # Track column transformations
    
    def add_file(self, path: Path):
        """Parse file and add all nodes/edges."""
        content = path.read_text()
        tree = ast.parse(content)
        
        file_id = f"file:{path}"
        self.graph.add_node(file_id, type="File", path=str(path), lines=len(content.splitlines()))
        
        # Extract all definitions and relationships
        self._extract_imports(tree, file_id)
        self._extract_functions(tree, file_id, content)
        self._extract_classes(tree, file_id)
        self._extract_column_operations(tree, file_id, content)
    
    def _extract_column_operations(self, tree: ast.AST, file_id: str, content: str):
        """Track column transformations: df['new'] = df['old'] * df['other']"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                # Check for df['col'] = ... pattern
                for target in node.targets:
                    if isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant):
                        target_col = target.slice.value
                        source_cols = self._find_source_columns(node.value)
                        
                        for source_col in source_cols:
                            self.graph.add_edge(
                                f"column:{source_col}",
                                f"column:{target_col}",
                                type="TRANSFORMS",
                                file=file_id,
                                line=node.lineno,
                                operation=ast.unparse(node.value)[:100]
                            )
    
    def _find_source_columns(self, node: ast.AST) -> Set[str]:
        """Find all column references in an expression."""
        columns = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Subscript) and isinstance(child.slice, ast.Constant):
                columns.add(child.slice.value)
        return columns
    
    def query_lineage(self, column: str, direction: str = "both") -> Dict:
        """Trace column lineage through the graph."""
        column_id = f"column:{column}"
        
        result = {"column": column, "upstream": [], "downstream": []}
        
        if direction in ["backward", "both"]:
            result["upstream"] = self._trace_upstream(column_id)
        
        if direction in ["forward", "both"]:
            result["downstream"] = self._trace_downstream(column_id)
        
        return result
    
    def _trace_upstream(self, node_id: str, visited: Set = None) -> List[Dict]:
        """Recursively find all upstream transformations."""
        if visited is None:
            visited = set()
        
        if node_id in visited:
            return []
        visited.add(node_id)
        
        upstream = []
        for pred in self.graph.predecessors(node_id):
            edge_data = self.graph.edges[pred, node_id]
            upstream.append({
                "source": pred,
                "operation": edge_data.get("operation"),
                "location": f"{edge_data.get('file')}:{edge_data.get('line')}",
                "upstream": self._trace_upstream(pred, visited)
            })
        
        return upstream
    
    def export_json(self, path: Path):
        """Export graph to JSON for embedding in pipeline-map."""
        data = nx.node_link_data(self.graph)
        path.write_text(json.dumps(data, indent=2))
    
    def export_cypher(self, path: Path):
        """Export to Cypher for Neo4j import."""
        statements = []
        for node, attrs in self.graph.nodes(data=True):
            props = ", ".join(f'{k}: "{v}"' for k, v in attrs.items())
            statements.append(f'CREATE (:{attrs["type"]} {{id: "{node}", {props}}})')
        
        for source, target, attrs in self.graph.edges(data=True):
            props = ", ".join(f'{k}: "{v}"' for k, v in attrs.items() if k != "type")
            statements.append(f'MATCH (a {{id: "{source}"}}), (b {{id: "{target}"}}) CREATE (a)-[:{attrs["type"]} {{{props}}}]->(b)')
        
        path.write_text(";\n".join(statements))
```

#### 4.3 Example Queries

```python
# Query: "What affects the open_po_value column?"
graph.query_lineage("open_po_value", direction="backward")
# Returns:
{
  "column": "open_po_value",
  "upstream": [
    {
      "source": "column:po_value_usd",
      "operation": "po_value_usd - cost_impact_sum",
      "location": "scripts/stage3_prepare/06_prepare_po_line_items.py:78",
      "upstream": [
        {
          "source": "column:Purchase Value USD",
          "operation": "direct mapping",
          "location": "scripts/stage1_clean/01_po_line_items.py:42"
        }
      ]
    },
    {
      "source": "column:cost_impact_sum",
      "operation": "aggregation from cost_impact",
      "location": "scripts/stage3_prepare/06_prepare_po_line_items.py:65"
    }
  ]
}

# Query: "What functions call calculate_gr_amount?"
graph.query_callers("calculate_gr_amount")
# Returns locations in main() functions that invoke it

# Query: "What files are affected if I change column_mappings.py?"
graph.query_dependents("scripts/config/column_mappings.py")
# Returns all files that import from it
```

### Deliverables
- [ ] `scripts/build_knowledge_graph.py` - Graph builder
- [ ] `pipeline-context/graph/` - Serialized graph
- [ ] `trace_data_lineage` MCP tool implementation
- [ ] Graph visualization export (Mermaid/D3.js)

---

## Phase 5: Embedding Index (Week 7-8)

### Objective
Enable semantic code search using code-specific embeddings.

### Implementation

#### 5.1 Chunking Strategy

```python
"""
AST-based chunking that preserves semantic boundaries.
Each chunk is a complete function, class, or logical block.
"""

from dataclasses import dataclass
from typing import List
import ast

@dataclass
class CodeChunk:
    id: str
    file: str
    start_line: int
    end_line: int
    content: str
    type: str  # "function" | "class" | "module_level"
    context: str  # Parent class/module name
    tokens: int

class ASTChunker:
    MAX_CHUNK_TOKENS = 512
    
    def chunk_file(self, path: str, content: str) -> List[CodeChunk]:
        """Chunk file by AST boundaries."""
        chunks = []
        tree = ast.parse(content)
        lines = content.splitlines()
        
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                chunks.append(self._create_chunk(path, node, lines, "function"))
            
            elif isinstance(node, ast.ClassDef):
                # Add class-level chunk (signature + docstring)
                chunks.append(self._create_chunk(path, node, lines, "class"))
                
                # Add each method as separate chunk
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        chunks.append(self._create_chunk(
                            path, child, lines, "method",
                            context=node.name
                        ))
        
        return chunks
    
    def _create_chunk(self, path, node, lines, chunk_type, context="") -> CodeChunk:
        start = node.lineno - 1
        end = node.end_lineno
        content = "\n".join(lines[start:end])
        
        # If chunk too large, create skeleton version
        tokens = self._count_tokens(content)
        if tokens > self.MAX_CHUNK_TOKENS:
            content = self._skeletonize(node)
            tokens = self._count_tokens(content)
        
        return CodeChunk(
            id=f"{path}:{start+1}-{end}",
            file=path,
            start_line=start + 1,
            end_line=end,
            content=content,
            type=chunk_type,
            context=context,
            tokens=tokens
        )
```

#### 5.2 Embedding Pipeline

```python
"""
Generate and index embeddings for code chunks.
Uses Jina Code Embeddings for best code understanding.
"""

from sentence_transformers import SentenceTransformer
import numpy as np
import faiss

class CodeEmbeddingIndex:
    def __init__(self, model_name: str = "jinaai/jina-embeddings-v2-base-code"):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.chunks = []
    
    def build_index(self, chunks: List[CodeChunk]):
        """Build FAISS index from code chunks."""
        self.chunks = chunks
        
        # Generate embeddings
        texts = [self._prepare_text(chunk) for chunk in chunks]
        embeddings = self.model.encode(texts, show_progress_bar=True)
        
        # Build FAISS index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
    
    def _prepare_text(self, chunk: CodeChunk) -> str:
        """Prepare chunk text for embedding with context."""
        context_prefix = f"# File: {chunk.file}\n"
        if chunk.context:
            context_prefix += f"# Context: {chunk.context}\n"
        return context_prefix + chunk.content
    
    def search(self, query: str, k: int = 10) -> List[tuple[CodeChunk, float]]:
        """Search for similar code chunks."""
        query_embedding = self.model.encode([query])
        faiss.normalize_L2(query_embedding)
        
        scores, indices = self.index.search(query_embedding, k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.chunks):
                results.append((self.chunks[idx], float(score)))
        
        return results
    
    def save(self, path: str):
        """Save index and metadata."""
        faiss.write_index(self.index, f"{path}/index.faiss")
        with open(f"{path}/chunks.json", "w") as f:
            json.dump([asdict(c) for c in self.chunks], f)
    
    def load(self, path: str):
        """Load index and metadata."""
        self.index = faiss.read_index(f"{path}/index.faiss")
        with open(f"{path}/chunks.json") as f:
            self.chunks = [CodeChunk(**c) for c in json.load(f)]
```

#### 5.3 Hybrid Search

```python
"""
Combines BM25 (keyword) + Vector (semantic) search with RRF fusion.
"""

from rank_bm25 import BM25Okapi
import re

class HybridSearch:
    def __init__(self, chunks: List[CodeChunk], embedding_index: CodeEmbeddingIndex):
        self.chunks = chunks
        self.embedding_index = embedding_index
        
        # Build BM25 index
        tokenized = [self._tokenize(c.content) for c in chunks]
        self.bm25 = BM25Okapi(tokenized)
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize code for BM25."""
        # Split on whitespace and punctuation, keep identifiers
        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*|[0-9]+', text.lower())
        return tokens
    
    def search(self, query: str, k: int = 10, alpha: float = 0.5) -> List[tuple[CodeChunk, float]]:
        """
        Hybrid search with tunable alpha.
        alpha=1.0: pure semantic, alpha=0.0: pure keyword
        """
        # BM25 search
        tokenized_query = self._tokenize(query)
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_ranking = np.argsort(bm25_scores)[::-1][:k*2]
        
        # Vector search
        vector_results = self.embedding_index.search(query, k*2)
        vector_ranking = [self.chunks.index(chunk) for chunk, _ in vector_results]
        
        # RRF fusion
        rrf_scores = {}
        for rank, idx in enumerate(bm25_ranking):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + (1 - alpha) / (rank + 60)
        for rank, idx in enumerate(vector_ranking):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + alpha / (rank + 60)
        
        # Sort by RRF score
        sorted_indices = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:k]
        
        return [(self.chunks[idx], rrf_scores[idx]) for idx in sorted_indices]
```

### Deliverables
- [ ] `scripts/build_embedding_index.py` - Index builder
- [ ] `pipeline-context/embeddings/` - FAISS index + metadata
- [ ] `search_codebase` MCP tool with hybrid search
- [ ] Benchmark against pure keyword search

---

## Phase 6: Integration & Testing (Week 9-10)

### Objective
Integrate all components and validate with real agent workflows.

### 6.1 Updated File Structure

```
cost-management-db/
├── pipeline-context/           # NEW: All generated context
│   ├── skeletons/             # Phase 1: Compressed code
│   ├── summaries/             # Phase 2: Hierarchical summaries
│   ├── graph/                 # Phase 4: Knowledge graph
│   │   ├── nodes.json
│   │   ├── edges.json
│   │   └── graph.cypher       # Neo4j export
│   ├── embeddings/            # Phase 5: Vector index
│   │   ├── index.faiss
│   │   └── chunks.json
│   └── config.json            # Index configuration
├── src/
│   └── mcp-server/            # Phase 3: MCP tools
│       ├── index.ts
│       ├── tools/
│       │   ├── search.ts
│       │   ├── context.ts
│       │   ├── lineage.ts
│       │   └── symbols.ts
│       └── package.json
├── scripts/
│   ├── generate_pipeline_map.py    # Existing (enhanced)
│   ├── generate_skeletons.py       # Phase 1
│   ├── generate_summaries.py       # Phase 2
│   ├── build_knowledge_graph.py    # Phase 4
│   └── build_embedding_index.py    # Phase 5
├── pipeline-map.json          # Existing (links to new context)
└── opencode.json              # MCP server config
```

### 6.2 Generation Pipeline

```python
# scripts/generate_all_context.py
"""Master script to generate all context artifacts."""

def main():
    print("=" * 60)
    print("Generating Pipeline Context v2")
    print("=" * 60)
    
    # Phase 1: Skeletons
    print("\n[1/5] Generating code skeletons...")
    from generate_skeletons import generate_all_skeletons
    generate_all_skeletons()
    
    # Phase 2: Summaries
    print("\n[2/5] Generating hierarchical summaries...")
    from generate_summaries import generate_all_summaries
    generate_all_summaries()
    
    # Phase 3: Pipeline Map (existing, enhanced)
    print("\n[3/5] Generating pipeline map...")
    from generate_pipeline_map import generate_pipeline_map
    generate_pipeline_map()
    
    # Phase 4: Knowledge Graph
    print("\n[4/5] Building knowledge graph...")
    from build_knowledge_graph import build_graph
    build_graph()
    
    # Phase 5: Embedding Index
    print("\n[5/5] Building embedding index...")
    from build_embedding_index import build_index
    build_index()
    
    print("\n" + "=" * 60)
    print("Context Generation Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

### 6.3 Agent Workflow Example

```
User: "Fix the bug where open_po_value is negative for some rows"

Agent Workflow:
1. search_codebase("open_po_value negative calculation")
   → Returns: 06_prepare_po_line_items.py:78 (calculate_open_values function)

2. trace_data_lineage("open_po_value", direction="backward")
   → Returns: Graph showing po_value_usd - cost_impact_sum path

3. get_context_level("stage3_prepare/06_prepare_po_line_items", level=2)
   → Returns: Script summary with key operations

4. read_code_range("scripts/stage3_prepare/06_prepare_po_line_items.py", 65, 90)
   → Returns: Full implementation of calculate_open_values

5. Agent identifies bug: missing abs() or floor at 0

6. Makes targeted edit with full context
```

### 6.4 Benchmarks

| Metric | Current | Target |
|--------|---------|--------|
| Initial context tokens | 15,000 | 500 |
| Search latency (p50) | N/A | <100ms |
| Search relevance (MRR) | N/A | >0.7 |
| Lineage query time | N/A | <50ms |
| Context accuracy | 85% | 98% |

### Deliverables
- [ ] `scripts/generate_all_context.py` - Master generator
- [ ] Updated pre-commit hooks
- [ ] Agent workflow documentation
- [ ] Benchmark test suite
- [ ] Performance monitoring

---

## Summary: Implementation Timeline

| Week | Phase | Key Deliverable |
|------|-------|-----------------|
| 1 | Skeletonization | 5x token reduction |
| 2 | Hierarchical Summaries | Zoomable context |
| 3-4 | MCP Tools | Query-based retrieval |
| 5-6 | Knowledge Graph | Data lineage tracing |
| 7-8 | Embedding Index | Semantic search |
| 9-10 | Integration | Production-ready system |

## Success Criteria

1. **Scale**: Handle 100K+ file repositories without degradation
2. **Latency**: All queries return in <100ms
3. **Relevance**: >70% MRR on code search benchmarks
4. **Token Efficiency**: 95% reduction in initial context size
5. **Agent Success**: >90% task completion on SWE-bench style tasks

---

# REVISED TIMELINE: The Context Oracle (4 Weeks)

Based on the architectural shift to the three-pillar "Context Oracle" system:

## Week 1: Symbol Registry + Skeletons

**Goal**: Zero hallucinations on symbol references

### Deliverables
- [ ] `scripts/build_symbol_registry.py` - Extract all functions, columns, constants, tables
- [ ] `pipeline-context/registry/symbols.json` - Canonical symbol index
- [ ] `scripts/generate_skeletons.py` - Compressed code views
- [ ] MCP Tool: `verify_symbol(name)` - Returns exists/location/suggestion
- [ ] MCP Tool: `lookup_signature(function)` - Returns full signature + docstring
- [ ] MCP Tool: `find_similar(query)` - Fuzzy symbol search

### Agent Workflow Change
```
BEFORE: Agent writes code → Hallucinated imports/calls
AFTER:  Agent calls verify_symbol() → Agent writes verified code
```

### Validation Test
- Give agent task: "Call the function that filters valuation classes"
- Without registry: Agent might write `filter_valuations()` (doesn't exist)
- With registry: Agent verifies → finds `filter_valuation_classes` → correct call

---

## Week 2: Pattern Library

**Goal**: Zero code drift, 100% convention compliance

### Deliverables
- [ ] `scripts/extract_patterns.py` - Identify code patterns from existing files
- [ ] `pipeline-context/patterns/index.json` - Pattern definitions + examples
- [ ] MCP Tool: `get_pattern(task)` - Returns template + examples for task type
- [ ] MCP Tool: `find_similar_code(description)` - Find existing similar implementations
- [ ] MCP Tool: `validate_consistency(file, code)` - Check if code follows patterns

### Agent Workflow Change
```
BEFORE: Agent writes new code → Inconsistent style/structure
AFTER:  Agent calls get_pattern() → Agent follows existing conventions
```

### Validation Test
- Give agent task: "Add a new pipeline script for cleaning reservations data"
- Without patterns: Agent creates random structure
- With patterns: Agent follows exact structure of existing pipeline scripts

---

## Week 3: Lineage Oracle

**Goal**: Guided search, impact awareness, zero blind grepping

### Deliverables
- [ ] `scripts/build_lineage_graph.py` - Data flow graph from pipeline map
- [ ] `pipeline-context/lineage/graph.json` - Node/edge representation
- [ ] MCP Tool: `trace_lineage(target, direction)` - Trace data flow
- [ ] MCP Tool: `predict_impact(file)` - Predict downstream effects
- [ ] MCP Tool: `smart_search(query)` - Context-aware search (replaces blind grep)

### Agent Workflow Change
```
BEFORE: Agent greps "cost" → 500 results → reads wrong files
AFTER:  Agent calls trace_lineage("cost_impact") → 3 relevant files
```

### Validation Test
- Give agent task: "Fix the calculation of open_po_value"
- Without lineage: Agent searches randomly, might miss critical files
- With lineage: Agent traces upstream → finds exact files + line numbers

---

## Week 4: Integration + Validation Gate

**Goal**: Production-ready system with mandatory verification

### Deliverables
- [ ] `src/mcp-server/` - Complete MCP server with all tools
- [ ] `scripts/generate_context_oracle.py` - Master generation script
- [ ] Validation gate in agent workflow (verify before write)
- [ ] Benchmark test suite
- [ ] Documentation + agent usage examples

### The Validation Gate
```python
# Agent MUST pass through this before any write operation
class ContextOracle:
    def validate_before_write(self, file_path: str, new_code: str) -> ValidationResult:
        errors = []
        
        # 1. Verify all symbol references exist
        symbols = self.extract_symbols(new_code)
        for symbol in symbols:
            if not self.registry.verify(symbol):
                errors.append(f"Unknown symbol: {symbol}")
        
        # 2. Check pattern consistency
        pattern_check = self.patterns.validate(file_path, new_code)
        if not pattern_check.consistent:
            errors.extend(pattern_check.violations)
        
        # 3. Warn about impact
        impact = self.lineage.predict_impact(file_path)
        if impact.risk_level == "high":
            errors.append(f"High-risk change: affects {impact.affected_columns}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=impact.recommendations
        )
```

---

## Summary: Before vs After

| Aspect | Before (Raw Tools) | After (Context Oracle) |
|--------|-------------------|------------------------|
| **Symbol References** | Guessing, hallucinating | Verified from registry |
| **Code Style** | Inconsistent, drifting | Pattern-enforced |
| **Search Strategy** | Blind grep, 500 results | Lineage-guided, 3 files |
| **Change Safety** | Unknown impact | Predicted dependencies |
| **Token Usage** | Read everything | Read only relevant |
| **Error Rate** | High (hallucinations) | Near-zero (verified) |

## The "Best in World" Differentiator

Most AI coding systems give agents tools and hope for the best.

**The Context Oracle** gives agents:
1. **A source of truth** (Registry) - Can't hallucinate what's verified
2. **Institutional knowledge** (Patterns) - Follows conventions automatically  
3. **A map of the territory** (Lineage) - Knows exactly where to go

This is the difference between giving someone a machete (raw tools) vs giving them a GPS + local guide (Context Oracle).
