# Agentic Coding Guardrails: Final Architecture

## Multi-Agent Review Synthesis

This final architecture incorporates insights from:
- **Apex**: Architectural validation, pattern analysis, feasibility review
- **Prism**: Contrarian critique, alternative approaches, failure mode analysis

---

## Key Design Decisions (Post-Review)

### What We're Keeping (Validated)

| Component | Validation | Source |
|-----------|------------|--------|
| Layered pre-commit (ruff → Oracle) | Sound fail-fast escalation | Apex |
| Oracle-centric JSON outputs | Agent-optimized consumption | Both |
| Schema lock concept | Proven pattern (like package-lock) | Apex |
| Golden set testing | Runtime truth > static guessing | Prism |

### What We're Changing (Critique-Driven)

| Original Plan | Problem | New Approach |
|---------------|---------|--------------|
| Custom complexity validator | Reinventing wheel | Use `ruff` built-in C901 + cognitive |
| AST fingerprint duplicates | Slow, noisy | Use `pylint --enable=similarities` |
| Static idempotency regex | False positives galore | Runtime `freezegun` tests instead |
| External YAML contracts | Manual sync burden | **In-code Pandera schemas** |
| Custom ledger.jsonl | Duplicates git history | **Use git log + structured commits** |
| Complex post-commit | Failure-prone | Simplified, optional |

### What We're Removing (Over-Engineered)

| Removed | Reason | Alternative |
|---------|--------|-------------|
| Custom duplicate detector | Use existing pylint | `pylint --enable=similarities` |
| Idempotency regex scanner | Too many false positives | Runtime tests |
| Custom complexity.py | ruff does this better | `ruff --select=C901` |
| Parallel ledger.jsonl | Git log is the ledger | Structured commit messages |

---

## Refined Architecture: "Pragmatic Guardrails"

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PRAGMATIC AGENTIC GUARDRAILS                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PRE-COMMIT (Fast, <5 seconds)                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ LAYER 1: Standard Tools (ruff + mypy)                                  │ │
│  │   • ruff: lint + format + complexity (C901)                            │ │
│  │   • mypy: type safety                                                  │ │
│  │   • pylint: similarity detection (duplicates)                          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ LAYER 2: Oracle Essentials (Changed files only)                        │ │
│  │   • Schema lock check (hash comparison)                                │ │
│  │   • Pipeline order validation (DAG check)                              │ │
│  │   • Symbol verification (anti-hallucination)                           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ LAYER 3: Oracle Regeneration (If source changed)                       │ │
│  │   • Incremental update only                                            │ │
│  │   • Hash-based change detection                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  CI/CD (Thorough, minutes OK)                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ LAYER 4: Runtime Validation                                            │ │
│  │   • Golden Set pipeline execution                                      │ │
│  │   • Pandera schema validation                                          │ │
│  │   • Contract snapshot comparison                                       │ │
│  │   • Integration tests with freezegun (idempotency)                     │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  CONTEXT ORACLE (Pre-computed Intelligence)                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │   • Symbol Registry: Anti-hallucination                                │ │
│  │   • Lineage Graph: Impact prediction                                   │ │
│  │   • Pattern Library: Convention templates                              │ │
│  │   • Code Skeletons: Token compression                                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Pre-Commit Configuration (Final)

### `.pre-commit-config.yaml`

```yaml
# Pragmatic Agentic Guardrails
# Target: <5 second pre-commit, comprehensive CI

default_stages: [pre-commit]

repos:
  # ============================================
  # LAYER 1: Standard Tools (Battle-Tested)
  # ============================================
  
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.9
    hooks:
      - id: ruff
        name: "Ruff: Lint + Complexity"
        args: [
          "--fix",
          "--select=E,F,I,B,UP,C901",  # C901 = complexity
          "--max-complexity=15"         # Prism: 15 not 10 for ETL
        ]
        files: "^scripts/.*\\.py$"
      
      - id: ruff-format
        files: "^scripts/.*\\.py$"

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        args: ["--ignore-missing-imports"]
        files: "^scripts/.*\\.py$"
        additional_dependencies: [pandas-stubs]

  # Duplicate detection via pylint (Prism suggestion)
  - repo: local
    hooks:
      - id: pylint-duplicates
        name: "Pylint: Duplicate Detection"
        entry: pylint
        args: [
          "--disable=all",
          "--enable=similarities",
          "--min-similarity-lines=10"  # Prism: 95% = ~10 lines
        ]
        language: system
        files: "^scripts/stage.*\\.py$"

  # ============================================
  # LAYER 2: Oracle Essentials (Fast Checks)
  # ============================================
  
  - repo: local
    hooks:
      # Schema lock - fast hash comparison
      - id: schema-lock-check
        name: "Schema: Lock Verification"
        entry: python3 scripts/validators/schema_lock.py --check
        language: system
        files: "^scripts/stage3_.*\\.py$|^src/schema/.*\\.ts$"
        pass_filenames: false

      # Pipeline DAG validation
      - id: pipeline-order
        name: "Pipeline: DAG Validation"
        entry: python3 scripts/ask_oracle.py validate pipeline-order
        language: system
        files: "^scripts/stage.*\\.py$"
        pass_filenames: false

      # Symbol verification (anti-hallucination)
      - id: oracle-verify
        name: "Oracle: Symbol Verification"
        entry: python3 scripts/ask_oracle.py validate symbols --changed-only
        language: system
        files: "^scripts/.*\\.py$"
        pass_filenames: false

  # ============================================
  # LAYER 3: Oracle Regeneration (Conditional)
  # ============================================
  
  - repo: local
    hooks:
      - id: update-context-oracle
        name: "Oracle: Incremental Update"
        entry: python3 scripts/generate_context_oracle.py --incremental
        language: system
        files: "^scripts/(stage[123]_|config/).*\\.py$|^src/schema/.*\\.ts$"
        pass_filenames: false
        stages: [pre-commit]
```

---

## Part 2: Runtime Validation (CI/CD)

### Pandera Schemas (In-Code Contracts)

**Prism's key insight**: External YAML contracts create sync burden. Define contracts IN the code.

**`scripts/contracts/po_line_items_schema.py`**:

```python
"""
Data Contract: PO Line Items Output Schema

This schema is the single source of truth for the output format.
Validated at runtime, not statically.
"""
import pandera as pa
from pandera.typing import DataFrame, Series

class POLineItemsSchema(pa.DataFrameModel):
    """Contract for data/intermediate/po_line_items.csv"""
    
    # Required columns with types
    po_number: Series[str] = pa.Field(nullable=False)
    po_line_id: Series[str] = pa.Field(nullable=False, unique=True)
    unit_price: Series[float] = pa.Field(ge=0, nullable=False)
    quantity: Series[int] = pa.Field(gt=0, nullable=False)
    
    # Optional columns
    notes: Series[str] = pa.Field(nullable=True)
    
    class Config:
        strict = True  # Fail on extra columns
        coerce = True  # Allow type coercion


# Usage in pipeline script:
# @pa.check_output(POLineItemsSchema)
# def process_po_line_items(df: pd.DataFrame) -> pd.DataFrame:
#     ...
```

### Golden Set Testing

**`tests/test_pipeline_golden_set.py`**:

```python
"""
Golden Set Tests: Runtime truth for pipeline behavior.

Run in CI, not pre-commit (too slow).
"""
import pandas as pd
import pytest
from freezegun import freeze_time
from pathlib import Path

GOLDEN_INPUT = Path("golden_set/input")
GOLDEN_EXPECTED = Path("golden_set/expected_output")

@freeze_time("2025-01-01 12:00:00")  # Idempotency via time freeze
class TestPipelineGoldenSet:
    """Verify pipeline produces expected outputs from golden inputs."""
    
    def test_stage1_po_line_items(self):
        """Test 01_po_line_items.py produces expected output."""
        from scripts.stage1_clean import process_01_po_line_items
        
        # Run with golden input
        input_df = pd.read_csv(GOLDEN_INPUT / "po_details.csv")
        output_df = process_01_po_line_items(input_df)
        
        # Compare to expected
        expected_df = pd.read_csv(GOLDEN_EXPECTED / "po_line_items.csv")
        pd.testing.assert_frame_equal(
            output_df.reset_index(drop=True),
            expected_df.reset_index(drop=True),
            check_dtype=False  # Allow minor type differences
        )
    
    def test_schema_match(self):
        """Verify output schema matches Pandera contract."""
        from scripts.contracts.po_line_items_schema import POLineItemsSchema
        
        output_df = pd.read_csv(GOLDEN_EXPECTED / "po_line_items.csv")
        POLineItemsSchema.validate(output_df)  # Raises on mismatch
    
    def test_idempotency(self):
        """Verify running twice produces identical output."""
        from scripts.stage1_clean import process_01_po_line_items
        
        input_df = pd.read_csv(GOLDEN_INPUT / "po_details.csv")
        
        output1 = process_01_po_line_items(input_df.copy())
        output2 = process_01_po_line_items(input_df.copy())
        
        pd.testing.assert_frame_equal(output1, output2)
```

---

## Part 3: Simplified Oracle Validators

### Oracle Fact Access Layer (Apex suggestion)

**`scripts/validators/oracle_client.py`**:

```python
"""
Oracle Client: Clean interface to Oracle artifacts.

Provides dependency injection for testing and graceful degradation.
"""
import json
from pathlib import Path
from typing import Dict, Optional, Set

class OracleClient:
    """Unified access to Context Oracle artifacts."""
    
    def __init__(self, context_dir: Optional[Path] = None):
        self.context_dir = context_dir or Path("pipeline-context")
        self._registry = None
        self._lineage = None
        self._patterns = None
    
    @property
    def is_available(self) -> bool:
        """Check if Oracle artifacts exist."""
        return (self.context_dir / "registry/symbols.json").exists()
    
    def get_functions(self) -> list:
        """Get all registered functions."""
        return self._load_registry().get("functions", [])
    
    def get_columns(self) -> Dict[str, dict]:
        """Get all tracked columns."""
        return self._load_registry().get("columns", {})
    
    def get_column_writers(self, column: str) -> Set[str]:
        """Get scripts that write to a column."""
        lineage = self._load_lineage()
        writers = set()
        for access in lineage.get("column_access", {}).get(column, []):
            if access.get("type") == "WRITES":
                writers.add(access.get("script", ""))
        return writers
    
    def get_script_outputs(self, script: str) -> Set[str]:
        """Get files output by a script."""
        lineage = self._load_lineage()
        outputs = set()
        script_id = f"script:{script}"
        for edge in lineage.get("edges", []):
            if edge["source"] == script_id and edge["type"] == "OUTPUT":
                outputs.add(edge["target"].replace("file:", ""))
        return outputs
    
    def _load_registry(self) -> dict:
        if self._registry is None:
            path = self.context_dir / "registry/symbols.json"
            self._registry = json.loads(path.read_text()) if path.exists() else {}
        return self._registry
    
    def _load_lineage(self) -> dict:
        if self._lineage is None:
            path = self.context_dir / "lineage/graph.json"
            self._lineage = json.loads(path.read_text()) if path.exists() else {}
        return self._lineage
```

### Schema Lock (Refined)

**`scripts/validators/schema_lock.py`** (simplified):

```python
#!/usr/bin/env python3
"""
Schema Lock: Track output schema changes.

Uses inverted contract generation (Prism idea):
- Code generates schema, we track changes via diff
- No manual YAML sync needed
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from oracle_client import OracleClient

PROJECT_ROOT = Path(__file__).parent.parent.parent
LOCK_FILE = PROJECT_ROOT / "schema_lock.json"

def compute_schema_hash(columns: list) -> str:
    """Deterministic hash of column list."""
    normalized = sorted([c.lower().strip() for c in columns])
    return hashlib.sha256(json.dumps(normalized).encode()).hexdigest()[:16]

def get_current_schemas(oracle: OracleClient) -> dict:
    """Extract current schemas from Oracle lineage."""
    schemas = {}
    
    # Get all scripts and their output columns
    for func in oracle.get_functions():
        script = Path(func.get("file", "")).stem
        if not script.startswith(("01_", "02_", "03_", "04_", "05_", "06_", "07_", "08_", "09_")):
            continue
        
        # Find columns written by this script
        columns = []
        for col_name, col_data in oracle.get_columns().items():
            if col_data.get("created_by", "").endswith(f"{script}.py"):
                columns.append(col_name)
        
        if columns:
            schemas[script] = {
                "columns": sorted(columns),
                "hash": compute_schema_hash(columns),
                "count": len(columns)
            }
    
    return schemas

def check_lock() -> bool:
    """Check if current schemas match lock file."""
    oracle = OracleClient()
    
    if not oracle.is_available:
        print("Warning: Oracle not available, skipping schema check")
        return True  # Graceful degradation (Apex suggestion)
    
    current = get_current_schemas(oracle)
    
    if not LOCK_FILE.exists():
        print("schema_lock.json not found. Run with --update to create.")
        return False
    
    locked = json.loads(LOCK_FILE.read_text())
    
    mismatches = []
    for script, schema in current.items():
        if script not in locked.get("schemas", {}):
            mismatches.append(f"NEW: {script} ({schema['count']} columns)")
        elif schema["hash"] != locked["schemas"][script]["hash"]:
            old_cols = set(locked["schemas"][script]["columns"])
            new_cols = set(schema["columns"])
            added = new_cols - old_cols
            removed = old_cols - new_cols
            mismatches.append(
                f"CHANGED: {script} (+{len(added)} -{len(removed)} columns)"
            )
    
    if mismatches:
        print("Schema changes detected:")
        for m in mismatches:
            print(f"  {m}")
        print("\nRun: python scripts/validators/schema_lock.py --update")
        return False
    
    return True

def update_lock():
    """Update lock file with current schemas."""
    oracle = OracleClient()
    current = get_current_schemas(oracle)
    
    lock_data = {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schemas": current,
        "total_scripts": len(current),
        "total_columns": sum(s["count"] for s in current.values())
    }
    
    LOCK_FILE.write_text(json.dumps(lock_data, indent=2))
    print(f"Schema lock updated: {len(current)} scripts, "
          f"{lock_data['total_columns']} columns")

if __name__ == "__main__":
    if "--update" in sys.argv:
        update_lock()
    elif "--check" in sys.argv:
        sys.exit(0 if check_lock() else 1)
    else:
        sys.exit(0 if check_lock() else 1)
```

### Pipeline Order Validator (Simplified)

**`scripts/validators/pipeline_order.py`**:

```python
#!/usr/bin/env python3
"""
Pipeline Order: Validate script DAG has no cycles.

Uses explicit manifest approach (Prism suggestion) combined with
Oracle lineage for verification.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

from oracle_client import OracleClient

def build_dependency_graph(oracle: OracleClient) -> Dict[str, Set[str]]:
    """Build script dependency graph from Oracle lineage."""
    graph = {}  # script -> set of dependencies
    
    lineage = oracle._load_lineage()
    edges = lineage.get("edges", [])
    
    # Find INPUT edges (script depends on file)
    file_producers = {}  # file -> producing script
    file_consumers = {}  # file -> consuming scripts
    
    for edge in edges:
        if edge["type"] == "OUTPUT" and edge["source"].startswith("script:"):
            script = edge["source"].replace("script:", "")
            file = edge["target"].replace("file:", "")
            file_producers[file] = script
        
        elif edge["type"] == "INPUT" and edge["target"].startswith("script:"):
            script = edge["target"].replace("script:", "")
            file = edge["source"].replace("file:", "")
            if file not in file_consumers:
                file_consumers[file] = set()
            file_consumers[file].add(script)
    
    # Build dependency graph
    for file, consumers in file_consumers.items():
        producer = file_producers.get(file)
        if producer:
            for consumer in consumers:
                if consumer not in graph:
                    graph[consumer] = set()
                graph[consumer].add(producer)
    
    return graph

def detect_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """Detect cycles using DFS."""
    cycles = []
    visited = set()
    rec_stack = set()
    path = []
    
    def dfs(node):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                # Found cycle
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])
        
        path.pop()
        rec_stack.remove(node)
    
    for node in graph:
        if node not in visited:
            dfs(node)
    
    return cycles

def validate_ordering(graph: Dict[str, Set[str]]) -> List[str]:
    """Check if numeric prefixes match topological order."""
    issues = []
    
    for script, deps in graph.items():
        script_num = int(script.split("_")[0]) if script[0].isdigit() else 999
        for dep in deps:
            dep_num = int(dep.split("_")[0]) if dep[0].isdigit() else 999
            if dep_num >= script_num:
                issues.append(
                    f"{script} depends on {dep}, but {dep} has higher/equal prefix"
                )
    
    return issues

def main():
    oracle = OracleClient()
    
    if not oracle.is_available:
        print('{"passed": true, "warning": "Oracle not available"}')
        return 0
    
    graph = build_dependency_graph(oracle)
    cycles = detect_cycles(graph)
    ordering_issues = validate_ordering(graph)
    
    passed = len(cycles) == 0 and len(ordering_issues) == 0
    
    result = {
        "passed": passed,
        "cycles": cycles,
        "ordering_issues": ordering_issues,
        "scripts_analyzed": len(graph)
    }
    
    print(json.dumps(result))
    return 0 if passed else 1

if __name__ == "__main__":
    sys.exit(main())
```

---

## Part 4: Implementation Phases (Revised)

### Phase 1: Foundation (3 days)
**Scope**: Minimal viable guardrails

- [x] Configure ruff with complexity (C901, max=15)
- [ ] Configure pylint for duplicate detection
- [ ] Create `scripts/validators/` directory
- [ ] Implement `oracle_client.py` (fact access layer)
- [ ] Update `.pre-commit-config.yaml` with Layer 1

**Exit Criteria**: Pre-commit runs <5 seconds, catches complexity violations

### Phase 2: Schema Tracking (3 days)
**Scope**: Change detection

- [ ] Implement `schema_lock.py`
- [ ] Generate initial `schema_lock.json`
- [ ] Add schema lock to pre-commit
- [ ] Document schema update workflow

**Exit Criteria**: Schema changes require explicit acknowledgment

### Phase 3: Pipeline Validation (2 days)
**Scope**: DAG integrity

- [ ] Implement `pipeline_order.py`
- [ ] Add pipeline order to pre-commit
- [ ] Verify no cycles in current codebase

**Exit Criteria**: Circular dependencies blocked

### Phase 4: Runtime Contracts (5 days)
**Scope**: CI/CD validation

- [ ] Install Pandera
- [ ] Create schema contracts for all stage outputs
- [ ] Create golden set (10-20 rows)
- [ ] Implement golden set tests with freezegun
- [ ] Add to CI pipeline

**Exit Criteria**: CI catches schema drift and non-idempotent code

### Phase 5: Polish (2 days)
**Scope**: DX improvements

- [ ] Add `ask_oracle.py health` command
- [ ] Add `ask_oracle.py validate --changed-only`
- [ ] Performance optimization (target <5s pre-commit)
- [ ] Documentation and onboarding guide

**Exit Criteria**: <5s pre-commit, comprehensive CI

---

## Part 5: What We Removed (Scope Control)

Based on Prism's "over-engineering" critique:

| Removed | Reason | Alternative |
|---------|--------|-------------|
| Custom complexity.py | ruff C901 does this | Use ruff |
| Custom duplicates.py | pylint does this | Use pylint similarities |
| Idempotency regex scanner | Too many false positives | freezegun in tests |
| ledger.jsonl | Duplicates git history | Use git log |
| post-commit hook | Failure-prone, optional | CI generates artifacts |
| External YAML contracts | Sync burden | Pandera in-code |

---

## Part 6: Final Success Metrics

| Metric | Target | How |
|--------|--------|-----|
| Pre-commit time | <5 seconds | Scope to changed files |
| False positive rate | <5% | Tune thresholds, add noqa |
| Schema drift detection | 100% | Golden set + schema lock |
| Complexity violations | 0 at commit | ruff C901 blocks |
| CI pass rate | >95% | Comprehensive tests |
| Developer bypass rate | <10% | Fast pre-commit |

---

## Part 7: Open Questions Resolved

| Question | Decision | Rationale |
|----------|----------|-----------|
| Complexity threshold | **15** | ETL has flat long transforms (Prism) |
| Duplicate sensitivity | **10 lines** | 95% similarity = ~10 lines (Prism) |
| Contract strictness | **Strict (errors)** | Warnings become prod bugs (Prism) |
| Golden set size | **10-20 rows** | Perfect balance (Both) |
| Ledger retention | **Use git log** | Don't duplicate (Prism) |
| Cross-repo sync | **No** | Different domains (Prism) |

---

## Appendix: Agent Feedback Summary

### Apex Key Points
1. Add Oracle client abstraction layer
2. Scope validators to changed files for speed
3. Add graceful degradation when Oracle unavailable
4. Test validators with sample artifacts
5. Define performance budget (<5s)

### Prism Key Points  
1. Static analysis of dynamic Python is limited
2. Use existing tools (ruff, pylint) not custom
3. Runtime validation > static guessing
4. Git log IS the ledger
5. Pandera in-code > YAML contracts
6. Complexity 15 not 10 for ETL
7. LLM-as-validator for intelligent checks (future)

---

*Final architecture reviewed and approved by Apex and Prism agents.*
*Ready for implementation.*
