# Context Oracle: Deep Dive Technical Analysis

A comprehensive technical exploration of the Context Oracle system - an active guidance layer for AI coding agents. This document was created through hands-on experimentation, source code analysis, and multi-agent collaboration.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [The Three Pillars](#3-the-three-pillars)
4. [Generation Pipeline](#4-generation-pipeline)
5. [CLI Query Interface](#5-cli-query-interface)
6. [Hands-On Experimentation](#6-hands-on-experimentation)
7. [Technical Deep Dives](#7-technical-deep-dives)
8. [Multi-Agent Analysis](#8-multi-agent-analysis)
9. [Known Limitations](#9-known-limitations)
10. [Future Improvement Ideas](#10-future-improvement-ideas)

---

## 1. Executive Summary

The Context Oracle is a **pre-computed intelligence layer** designed to solve fundamental problems AI coding agents face:

| Problem | Solution | Technique |
|---------|----------|-----------|
| **Hallucination** | Symbol Registry | Verify any symbol exists before use |
| **Convention Drift** | Pattern Library | Provide templates and established patterns |
| **Blind Changes** | Lineage Oracle | Predict impact before modifying code |
| **Token Bloat** | Code Skeletons | 3.14x compression while retaining interfaces |

The system transforms a sprawling codebase into **queryable, compressed, interconnected JSON artifacts** that agents can consult before writing code.

### Key Metrics (From Actual Generation)

| Artifact | Size | Description |
|----------|------|-------------|
| Symbol Registry | 46 functions, 13 constants, 88 columns, 10 tables | Complete index of all symbols |
| Code Skeletons | 3.14x compression (12,727 → 4,057 tokens) | Compressed code views |
| Pattern Library | 4 patterns with templates | Established conventions |
| Lineage Graph | 79+ nodes, 100+ edges | Data flow dependencies |

---

## 2. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    SOURCE FILES                                  │
│  scripts/stage1_clean/*.py   scripts/stage2_transform/*.py      │
│  scripts/stage3_prepare/*.py  src/schema/*.ts  data/*.csv       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 GENERATION PIPELINE                              │
│  generate_context_oracle.py (orchestrator)                       │
│    ├── generate_pipeline_map.py    → pipeline-map.json          │
│    ├── build_symbol_registry.py    → registry/symbols.json      │
│    ├── generate_skeletons.py       → skeletons/*.skeleton.py    │
│    ├── extract_patterns.py         → patterns/index.json        │
│    └── build_lineage_graph.py      → lineage/graph.json         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 CONTEXT ARTIFACTS                                │
│  pipeline-context/                                               │
│    ├── registry/symbols.json    ← Anti-hallucination             │
│    ├── skeletons/               ← Token compression              │
│    ├── patterns/index.json      ← Convention enforcement         │
│    ├── lineage/graph.json       ← Impact prediction              │
│    └── .manifest.json           ← Freshness tracking             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 QUERY INTERFACE                                  │
│  ask_oracle.py <command>                                         │
│    ├── verify   → Check if symbol exists                         │
│    ├── impact   → Predict change impact                          │
│    ├── who      → Find column readers/writers                    │
│    ├── trace    → Trace data lineage                             │
│    ├── search   → Fuzzy symbol search                            │
│    └── pattern  → Get code templates                             │
└─────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
pipeline-context/
├── .manifest.json              # File hashes for incremental updates
├── registry/
│   └── symbols.json            # Complete symbol index
├── skeletons/
│   ├── index.json              # Compression stats for all scripts
│   ├── config/
│   │   └── column_mappings.skeleton.py
│   ├── stage1_clean/
│   │   ├── 01_po_line_items.skeleton.py
│   │   ├── 02_gr_postings.skeleton.py
│   │   └── 03_ir_postings.skeleton.py
│   ├── stage2_transform/
│   │   ├── 04_enrich_po_line_items.skeleton.py
│   │   ├── 05_calculate_cost_impact.skeleton.py
│   │   └── 06_calculate_grir.skeleton.py
│   └── stage3_prepare/
│       ├── 06_prepare_po_line_items.skeleton.py
│       ├── 07_prepare_po_transactions.skeleton.py
│       └── 08_prepare_grir_exposures.skeleton.py
├── patterns/
│   └── index.json              # Pattern library
└── lineage/
    └── graph.json              # Data flow graph
```

---

## 3. The Three Pillars

### Pillar 1: Symbol Registry (Anti-Hallucination)

**Problem**: AI agents invent plausible-sounding function/column names that don't exist.

**Solution**: A complete index of every symbol in the codebase that agents can verify against.

**What It Tracks**:

```json
{
  "functions": [
    {
      "name": "filter_valuation_classes",
      "file": "scripts/stage1_clean/01_po_line_items.py",
      "line": 42,
      "signature": "def filter_valuation_classes(df: pd.DataFrame) -> pd.DataFrame",
      "docstring": "Remove rows with excluded PO Valuation Classes.",
      "args": ["df"],
      "return_type": "pd.DataFrame",
      "calls": ["copy", "isin", "len", "print", "to_numeric"],
      "called_by": ["main"]
    }
  ],
  "constants": [
    {
      "name": "EXCLUDED_VALUATION_CLASSES",
      "file": "scripts/config/column_mappings.py",
      "line": 170,
      "value_type": "list",
      "value_preview": "[7800, 7900, 5008]"
    }
  ],
  "columns": {
    "Unit Price": {
      "name": "Unit Price",
      "source_type": "script",
      "sources": [],
      "dtype": null,
      "used_in": ["02_gr_postings", "03_ir_postings", "05_calculate_cost_impact"],
      "created_by": "scripts/stage1_clean/03_ir_postings.py:44"
    }
  },
  "tables": [
    {
      "name": "poLineItems",
      "file": "src/schema/po-line-items.ts",
      "columns": ["id", "poLineId", "poNumber", ...],
      "primary_key": "id",
      "foreign_keys": []
    }
  ]
}
```

**Extraction Technique**: Uses Python's `ast` module to parse source files:

```python
# From build_symbol_registry.py:100-160
def extract_functions_from_file(file_path: Path) -> List[FunctionSymbol]:
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Extract signature, docstring, return type
            # Build call graph by walking function body
```

### Pillar 2: Pattern Library (Anti-Drift)

**Problem**: Agents write code that ignores established conventions.

**Solution**: Extracted patterns with templates that define "how we do things here."

**Patterns Defined**:

| Pattern | Description | Key Elements |
|---------|-------------|--------------|
| `pipeline_script` | Data transformation script structure | Docstring template, load/save functions, main() |
| `drizzle_schema` | TypeScript ORM table definition | devV3Schema import, column types, timestamps |
| `data_filtering` | DataFrame row filtering function | .copy(), initial_count, print progress |
| `column_mapping` | CSV→DB column mappings | Dictionary with comments, grouping |

**Example Pattern** (from `patterns/index.json`):

```json
{
  "name": "pipeline_script",
  "structure": [
    "Module docstring with Dependencies/Input/Output",
    "sys.path setup for imports",
    "Import statements (sys, pathlib, pandas)",
    "PROJECT_ROOT and file path constants",
    "load_data() function",
    "transformation functions",
    "save_data() function",
    "main() orchestrator",
    "if __name__ == '__main__' guard"
  ],
  "function_templates": {
    "filter_template": "def filter_{what}(df: pd.DataFrame) -> pd.DataFrame:\n    initial_count = len(df)\n    mask = {mask_expression}\n    df_filtered = df[mask].copy()\n    ..."
  }
}
```

### Pillar 3: Lineage Oracle (Impact Prediction)

**Problem**: Agents don't know what will break when they modify code.

**Solution**: A data flow graph that tracks dependencies and predicts impact.

**Graph Structure**:

- **Nodes**: files, scripts, columns, tables, db_columns
- **Edges**: INPUT, OUTPUT, TRANSFORMS, MAPS_TO, DEPENDS_ON

**Key Innovation - Tiered Impact Classification**:

```json
{
  "script": "05_calculate_cost_impact",
  "columns_modified": ["Posting Date", "Posting Type", "Unit Price"],
  "tiered_impact": {
    "direct_writers": ["02_gr_postings", "03_ir_postings", "06_calculate_grir"],
    "column_readers": ["02_gr_postings", "03_ir_postings", "06_calculate_grir"],
    "file_consumers": ["06_prepare_po_line_items", "07_prepare_po_transactions"]
  },
  "risk_level": "high",
  "recommendation": "High-risk change: 3 scripts also write to same columns..."
}
```

**Variable Tracing** - The lineage builder can trace through intermediate variables:

```python
# Original code:
is_ops_vendor = po_df["Main Vendor SLB Vendor Category"] == "OPS"
output_df["fmt_po"] = is_ops_vendor

# Lineage graph captures:
# "Main Vendor SLB Vendor Category" → "fmt_po" (traced via is_ops_vendor)
```

---

## 4. Generation Pipeline

### Master Orchestrator (`generate_context_oracle.py`)

The master script coordinates all generators in correct order:

```python
def generate_all(skip_pipeline_map=False, incremental=False, force=False):
    # Step 1: Pipeline Map (foundation)
    from generate_pipeline_map import generate_pipeline_map
    run_generator("Pipeline Map", generate_pipeline_map)
    
    # Step 2: Symbol Registry
    from build_symbol_registry import generate_symbol_registry
    run_generator("Symbol Registry", generate_symbol_registry)
    
    # Step 3: Code Skeletons
    from generate_skeletons import generate_all_skeletons
    run_generator("Code Skeletons", generate_all_skeletons)
    
    # Step 4: Pattern Library
    from extract_patterns import build_pattern_library
    run_generator("Pattern Library", build_pattern_library)
    
    # Step 5: Lineage Graph
    from build_lineage_graph import build_lineage_graph
    run_generator("Lineage Graph", build_lineage_graph)
```

### Incremental Update Support

The system tracks file hashes to avoid unnecessary regeneration:

```python
def detect_changes() -> Dict:
    manifest = load_manifest()  # Previous hashes
    source_files = get_source_files()
    current_hashes = {key: compute_file_hash(path) for key, path in source_files.items()}
    
    changed = {k for k, v in current_hashes.items() if v != manifest.get(k)}
    added = {k for k in current_hashes if k not in manifest}
    removed = {k for k in manifest if k not in current_hashes}
    
    return {"changed": changed, "added": added, "removed": removed}
```

### Smart JSON Writes

To prevent git churn from timestamp-only changes:

```python
def smart_write_json(filepath, data, exclude_keys=["generated_at", "last_generated"]):
    # Strip timestamps before comparing
    new_content = strip_excluded(data)
    existing_content = strip_excluded(existing)
    
    if json.dumps(new_content, sort_keys=True) == json.dumps(existing_content, sort_keys=True):
        return False  # No change needed
    
    # Write with timestamps intact
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
```

### Deterministic Timestamps

Uses source file modification times instead of current time:

```python
def get_latest_source_mtime() -> datetime:
    """Prevents pre-commit hook loops by using deterministic timestamps."""
    latest_mtime = 0.0
    for path in get_source_files().values():
        mtime = path.stat().st_mtime
        if mtime > latest_mtime:
            latest_mtime = mtime
    return datetime.fromtimestamp(latest_mtime, tz=timezone.utc)
```

---

## 5. CLI Query Interface

### Overview (`ask_oracle.py`)

The CLI provides JSON output for agent consumption:

```bash
# All output is strict JSON for easy parsing
python3 scripts/ask_oracle.py <command> [args]
```

### Command Reference

#### `verify` - Anti-Hallucination Check

```bash
$ python3 scripts/ask_oracle.py verify filter_valuation_classes
{
  "found": true,
  "type": "function",
  "location": "scripts/stage1_clean/01_po_line_items.py:42",
  "signature": "def filter_valuation_classes(df: pd.DataFrame) -> pd.DataFrame",
  "docstring": "Remove rows with excluded PO Valuation Classes."
}

$ python3 scripts/ask_oracle.py verify nonexistent_function
{
  "found": false,
  "query": "nonexistent_function",
  "suggestion": "Did you mean 'forecast_versions'?",
  "similar": [...]
}
```

#### `impact` - Change Impact Prediction

```bash
$ python3 scripts/ask_oracle.py impact 05_calculate_cost_impact
{
  "script": "05_calculate_cost_impact",
  "outputs": ["data/intermediate/cost_impact.csv", ...],
  "columns_modified": ["Posting Date", "Posting Type", "Unit Price"],
  "tiered_impact": {
    "direct_writers": ["02_gr_postings", "03_ir_postings"],
    "column_readers": ["02_gr_postings", "06_calculate_grir"],
    "file_consumers": ["06_prepare_po_line_items", ...]
  },
  "risk_level": "high",
  "recommendation": "High-risk change: 3 scripts also write..."
}
```

#### `who` - Column Usage Discovery

```bash
$ python3 scripts/ask_oracle.py who "Unit Price"
{
  "found": true,
  "column": "Unit Price",
  "writers": [
    {"script": "02_gr_postings", "location": "scripts/stage1_clean/02_gr_postings.py:53"},
    {"script": "03_ir_postings", "location": "scripts/stage1_clean/03_ir_postings.py:44"}
  ],
  "readers": [
    {"script": "02_gr_postings", "location": "scripts/stage1_clean/02_gr_postings.py:64"}
  ],
  "summary": "4 scripts write, 2 scripts read"
}
```

#### `trace` - Data Lineage Tracing

```bash
$ python3 scripts/ask_oracle.py trace open_po_value --direction both
{
  "target": "open_po_value",
  "node_id": "column:open_po_value",
  "node_type": "column",
  "upstream": [
    {"node": "column:open_po_value", "edge_type": "TRANSFORMS", 
     "operation": "po_df['open_po_value'].round(2)"}
  ],
  "downstream": [...],
  "critical_files": [...]
}
```

#### `search` - Fuzzy Symbol Search

```bash
$ python3 scripts/ask_oracle.py search calculate --limit 5
{
  "query": "calculate",
  "count": 5,
  "results": [
    {"name": "calculate_complex_cost_impact", "type": "function", ...},
    {"name": "calculate_gr_amount", "type": "function", ...},
    {"name": "calculate_grir_exposures", "type": "function", ...}
  ]
}
```

#### `pattern` - Get Code Templates

```bash
$ python3 scripts/ask_oracle.py pattern pipeline_script
{
  "found": true,
  "pattern": {
    "name": "pipeline_script",
    "structure": [...],
    "function_templates": {
      "load_data": "def load_data(filepath: Path) -> pd.DataFrame:...",
      "save_data": "def save_data(df: pd.DataFrame, filepath: Path):..."
    }
  }
}
```

### Freshness Guard

Before any query, the CLI auto-checks for stale artifacts:

```python
def check_and_regenerate_if_stale(silent=False):
    source_mtime = get_latest_source_mtime()
    artifacts_mtime = get_artifacts_mtime()
    
    if source_mtime > artifacts_mtime:
        print("Oracle artifacts are stale. Regenerating...", file=sys.stderr)
        subprocess.run([sys.executable, "generate_context_oracle.py"], check=True)
```

---

## 6. Hands-On Experimentation

### Experiment 1: Verify Function Existence

**Goal**: Test anti-hallucination for real vs. invented functions.

```bash
# Real function
$ python3 scripts/ask_oracle.py verify filter_valuation_classes
→ Found at line 42 with full signature

# Non-existent function  
$ python3 scripts/ask_oracle.py verify calculate_total_cost
→ Not found, suggested similar: "calculate_open_values"
```

**Observation**: The similarity matching uses `SequenceMatcher` with substring boosting (ratio = 0.8 for substring matches).

### Experiment 2: Impact Prediction Accuracy

**Goal**: Verify the tiered impact classification.

```bash
$ python3 scripts/ask_oracle.py impact 05_calculate_cost_impact
```

**Analysis**:
- `Unit Price` is written by 4 scripts (02_gr_postings, 03_ir_postings, 05_calculate_cost_impact, 06_calculate_grir)
- This creates "high" risk because multiple scripts write to the same column
- The recommendation correctly identifies scripts to test

### Experiment 3: Skeleton Compression Ratios

From `pipeline-context/skeletons/index.json`:

| Script | Original Lines | Skeleton Lines | Compression |
|--------|----------------|----------------|-------------|
| 01_po_line_items | 173 | 64 | 2.79x |
| 04_enrich_po_line_items | 201 | 62 | 3.38x |
| 05_calculate_cost_impact | 206 | 59 | 3.71x |
| 06_calculate_grir | 249 | 74 | 3.37x |
| **Total** | **1487** | **488** | **3.14x** |

**Key Observation**: More complex scripts (with larger function bodies) achieve higher compression ratios.

### Experiment 4: Column Annotations in Skeletons

Skeleton files include column annotations in docstrings:

```python
"""
Stage 3: Prepare PO Line Items for Import
...
Column Operations:
  WRITES: fmt_po, open_po_qty, open_po_value
  READS:  Main Vendor SLB Vendor Category, PO Line ID, PO Receipt Status
"""
```

This allows agents to understand I/O without reading full implementations.

---

## 7. Technical Deep Dives

### 7.1 AST-Based Extraction

The system uses Python's `ast` module for static analysis:

**Function Extraction** (`build_symbol_registry.py:100`):
```python
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        # Build signature from args
        arg_strs = [arg.arg + (f": {ast.unparse(arg.annotation)}" if arg.annotation else "")
                    for arg in node.args.args]
        
        # Extract call graph
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                calls.append(child.func.id)
```

**Column Operation Detection** (`build_lineage_graph.py:213`):
```python
# Detect df["column"] = expression
if isinstance(node, ast.Assign):
    for target in node.targets:
        if isinstance(target, ast.Subscript):
            target_col = extract_column_from_subscript(target)
            source_cols = find_source_columns(node.value)
            
            # Create TRANSFORMS edges
            for source_col in source_cols:
                add_edge(source_col, target_col, "TRANSFORMS")
```

### 7.2 Variable Tracing

The lineage builder tracks intermediate variables:

```python
def _build_variable_mapping(self, tree, script_name) -> Dict[str, Set[str]]:
    """Map variables to their source columns."""
    var_to_cols = {}
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_name = target.id
                    cols = find_source_columns(node.value)
                    if cols:
                        var_to_cols[var_name] = cols
    
    return var_to_cols
```

This enables tracing through patterns like:
```python
is_ops = df["Vendor Category"] == "OPS"  # var_to_cols["is_ops"] = {"Vendor Category"}
df["fmt_po"] = is_ops                     # Traces fmt_po ← Vendor Category
```

### 7.3 Skeleton Transformation

The AST transformer removes function bodies while preserving interfaces:

```python
class SkeletonTransformer(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        new_body = []
        
        # Keep docstring if present
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            new_body.append(node.body[0])
        
        # Replace body with ellipsis
        new_body.append(ast.Expr(value=ast.Constant(value=...)))
        
        node.body = new_body
        return node
```

Result:
```python
# Original
def filter_valuation_classes(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with excluded PO Valuation Classes."""
    initial_count = len(df)
    valuation_class = pd.to_numeric(df["PO Valuation Class"], errors="coerce")
    mask = ~valuation_class.isin(EXCLUDED_VALUATION_CLASSES)
    df_filtered = df[mask].copy()
    removed_count = initial_count - len(df_filtered)
    print(f"  Removed {removed_count:,} rows...")
    return df_filtered

# Skeleton
def filter_valuation_classes(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with excluded PO Valuation Classes."""
    ...
```

### 7.4 TypeScript Schema Extraction

Database tables are extracted from Drizzle ORM schemas via a subprocess:

```python
def get_schema_tables() -> List[TableSymbol]:
    result = subprocess.run(
        ["npx", "ts-node", str(TS_EXTRACTOR)],
        capture_output=True,
        cwd=PROJECT_ROOT,
    )
    tables_data = json.loads(result.stdout)
    # Parse into TableSymbol dataclasses
```

---

## 8. Multi-Agent Analysis

### Prism Agent Analysis

#### Strengths Identified

1. **Token-efficient skeletons** - "Agents often suffer from 'Lost in the Middle' phenomena when fed massive files. By stripping implementation details but keeping signatures and docstrings, you provide the structural understanding required for planning."

2. **Tiered impact classification** - "Most 'find references' tools treat all usages equally. In data pipelines, reading a column is vastly different from consuming the output file."

3. **Anti-hallucination registry** - "A hard constraint against a known symbol list effectively grounds the probabilistic model in deterministic reality."

#### Alternative Approaches Suggested

| Approach | Trade-off |
|----------|-----------|
| **LSP-Native Agent** | Zero parsing maintenance, but verbose responses not optimized for LLM context |
| **Runtime Observability** | Captures dynamic columns, but requires runnable pipelines |
| **GraphRAG** | Semantic queries, but higher latency and nondeterministic |

#### Key Concern: Static Analysis Blindspot

> "Python is highly dynamic. AST cannot resolve dynamic attribute access (`getattr`), runtime-constructed column names, or SQL in strings."

**Suggested Mitigation**: Hybrid tracing with manual decorators like `@reads_columns("col_a", "col_b")`.

### Apex Agent Analysis

#### Design Patterns Identified

1. **Facade Pattern** - CLI provides simplified interface to complex artifacts
2. **Builder Pattern** - Orchestrator constructs artifacts in dependency order
3. **Observer Pattern** - Freshness guard monitors file changes
4. **Strategy Pattern** - Tiered impact uses different classification strategies

#### Trade-offs Made

| Sacrificed | Gained |
|------------|--------|
| Runtime accuracy | Instant queries (no execution needed) |
| Dynamic behavior | Deterministic, reproducible results |
| Full code context | Token efficiency (3x compression) |

#### Failure Modes Identified

1. **Dynamic columns** - `df[f"col_{i}"]` not captured
2. **Cross-language drift** - Python/TS analyzers may diverge
3. **Stale context race** - Agent modifies file, queries before regeneration
4. **Call graph incompleteness** - Dynamic dispatch, monkeypatching missed

#### Improvement Suggestions

1. **Confidence scores** - Surface probability that lineage is complete
2. **Delta explanations** - When regeneration happens, summarize what changed
3. **Pattern deviation detector** - Flag code that drifts from patterns
4. **Hybrid runtime signals** - Merge static analysis with runtime traces

---

## 9. Known Limitations

### Static Analysis Constraints

| Limitation | Example | Impact |
|------------|---------|--------|
| Dynamic column names | `df[f"col_{i}"]` | Missed in lineage |
| Runtime dispatch | `getattr(obj, method_name)()` | Call graph incomplete |
| SQL in strings | `conn.execute("SELECT col FROM...")` | Database access invisible |
| Decorators with side effects | `@cache`, `@retry` | Behavior modification missed |

### Python-Specific Gaps

```python
# These patterns are NOT captured:

# 1. Dynamic attribute access
col_name = get_column_name()
df[col_name] = value  # ← col_name is unknown at parse time

# 2. Dictionary unpacking
df.assign(**calculated_columns)  # ← column names in dict

# 3. Method chaining with lambdas
df.pipe(lambda x: x.assign(new_col=x["old"] * 2))  # ← "new_col" not captured
```

### Cross-Language Challenges

The system has separate parsers for Python and TypeScript:
- Python: `ast` module
- TypeScript: `ts-node` subprocess with custom extractor

These may diverge if schemas are renamed or refactored differently.

---

## 10. Future Improvement Ideas

### From Experimentation

1. **Expand Command** - Allow `ask_oracle.py expand <function>` to retrieve full implementation when skeleton isn't enough

2. **Confidence Scores** - Tag lineage edges with confidence (high for direct `df["col"]`, low for variable-traced)

3. **SQL Parser Integration** - Parse SQL strings to capture database dependencies

### From Prism Agent

1. **Self-Healing Oracle** - When runtime errors occur, update lineage from stack traces

2. **Ghost SQL** - Generate virtual representations of database triggers/procedures

3. **Proactive Drift Alerts** - Score new code against patterns, flag deviation risk

### From Apex Agent

1. **On-demand Embeddings** - Use CodeBERT for semantic search alongside symbol registry

2. **Runtime Tracing Hybrid** - Instrument pipelines to capture actual column flow

3. **LSIF/LSP Integration** - Reuse language server data for more accurate cross-refs

### Architecture Enhancements

```
Future Architecture:
┌─────────────────────────────────────────────────────────────────┐
│  Static Analysis (Current)   +   Runtime Tracing (Future)       │
│    AST Parsing                   Instrumented Execution         │
│    Symbol Registry               Actual Column Flow             │
│    Skeleton Generation           Dynamic Behavior               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
               ┌──────────────────────────────────┐
               │  Merged Knowledge Graph           │
               │  with Confidence Scoring          │
               │                                   │
               │  High Confidence: Static matches  │
               │  Medium: Variable-traced          │
               │  Low: Inferred/heuristic          │
               └──────────────────────────────────┘
```

---

## Conclusion

The Context Oracle represents a sophisticated approach to the fundamental challenge of making AI agents reliable on real codebases. Its core innovations:

1. **Pre-computed artifacts** eliminate per-query parsing overhead
2. **Tiered impact classification** provides actionable risk assessment
3. **Skeleton compression** achieves 3x+ token reduction while preserving interfaces
4. **Freshness guards** ensure agents never use stale context

The system's primary limitation - static analysis blindspots in dynamic languages - can be mitigated through hybrid runtime tracing, confidence scoring, and manual annotations. The architecture is well-positioned for these enhancements.

**Key Takeaway**: The Context Oracle transforms a codebase from "a pile of files" into "a queryable knowledge graph optimized for AI consumption."

---

*Document generated through hands-on experimentation and multi-agent collaboration (Prism, Apex) on 2025-12-01.*
