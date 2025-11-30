# Path to 100% Reliable Agentic Development

> A comprehensive plan for achieving near-zero escaped defects in AI-assisted code development, developed through collaboration with Prism and Apex agents.

---

## Executive Summary

### The Problem

During the GRIR feature implementation, an AI agent:
- Successfully used the Context Oracle for symbol verification and pattern compliance
- **Missed a critical edge case**: CLOSED PO status should have been filtered out
- The bug was caught by the user, not the agent

**Root Cause Analysis:**
- The Context Oracle is a **static analysis tool** - it knows code structure but not data values
- The agent had "tunnel vision" on the solution, not edge cases
- No automated validation caught the issue before user review

### The Reframed Goal

> **100% first-attempt correctness is mathematically impossible** due to natural language ambiguity and unknown-unknowns.

**New Definition of Success:**
```
100% Recovery + Near-Zero Escaped Defects
= Agent catches and fixes errors autonomously before user sees them
+ Rollback-safe deployment with containment
```

---

## Gap Analysis (Original Implementation)

| Dimension | Score | Issue |
|-----------|-------|-------|
| Symbol Verification | 8/10 | Used `oracle verify`, worked well |
| Pattern Compliance | 9/10 | Followed patterns correctly |
| Data Validation | 2/10 | **Didn't profile data before assuming** |
| Business Logic | 3/10 | Trusted verbal description without verification |
| Test Coverage | 1/10 | No automated tests created |
| Impact Analysis | 4/10 | Didn't use `oracle impact` or `trace` |
| Observability | 0/10 | No runtime metrics or alerts |
| Change Safety | 0/10 | No rollback path or feature flags |
| Scalability | 3/10 | Would break at 10-20x codebase size |

**Overall: ~33% - Not production-ready for autonomous operation**

---

## Architecture Critique

### Current Context Oracle: Strengths

| Component | Purpose | Effectiveness |
|-----------|---------|---------------|
| Symbol Registry | Verify functions/constants exist | World-class anti-hallucination |
| Pattern Library | Enforce code conventions | Reduces technical debt |
| Lineage Graph | Track data flow | Sophisticated, rare capability |
| Skeletons | Compressed code views | Good overview, 3x compression |

### Current Context Oracle: Fundamental Flaw

> "You have built a fantastic GPS that tells you exactly where the roads are (code structure), but you crashed because you didn't look out the windshield to see the traffic (data values)."
> — Prism Agent

**The Oracle is Static Analysis Only:**
- Knows WHERE code is and HOW it connects
- Knows NOTHING about:
  - What data looks like at runtime
  - What values exist in columns
  - Edge cases in actual data

---

## Implementation Plan

### Phase Overview

| Phase | Name | Timeline | Priority | Status |
|-------|------|----------|----------|--------|
| **0** | Data Profiling MVP | Day 1 | P0 | **COMPLETE** |
| **1** | Contract Testing | Week 1 | P0 | Pending |
| **2** | Enforcement Layer | Week 2 | P1 | Pending |
| **3** | Self-Healing Validation | Week 3 | P1 | Pending |
| **4** | Shadow + Observability | Week 4 | P2 | Pending |
| **5** | Scale Infrastructure | Week 5+ | P3 | Pending |

---

## Phase 0: Data Profiling MVP (COMPLETE)

### Deliverables

1. **`scripts/profile_data.py`** - Column/file profiling tool
2. **Updated `AGENTS.md`** - Mandatory profiling protocol

### Usage

```bash
# Profile a specific column
python3 scripts/profile_data.py data/intermediate/po_line_items.csv "PO Receipt Status"

# Output:
{
  "column": "PO Receipt Status",
  "dtype": "object",
  "total_rows": 57163,
  "null_count": 0,
  "unique_count": 3,
  "value_distribution": {
    "CLOSED PO": 53039,
    "OPEN PO": 3939,
    "PO does not require GR": 185
  }
}
```

### Protocol Added to AGENTS.md

1. **Profile** filter/transform columns before coding
2. **State assumptions** explicitly based on profile
3. **Confidence-based proceeding**:
   - High: Proceed and log
   - Medium: State assumption and proceed
   - Low: **STOP and ask user**

### Impact

This single change would have caught the CLOSED PO bug:
```bash
# Agent would have seen:
# CLOSED PO: 53039 (93% of data)
# 
# And asked: "Should I exclude CLOSED PO from exposure tracking?"
```

---

## Phase 1: Contract Testing

### Rationale

> "Writing assertions BEFORE code is more valuable than complex self-healing pipelines. Contracts are clear, binary, and enforce business logic directly."
> — Prism Agent

### Deliverables

```
tests/
├── contracts/
│   ├── __init__.py
│   ├── po_line_items.py
│   ├── po_transactions.py
│   └── grir_exposures.py
└── fixtures/
    └── golden/
        ├── grir_exposures_sample.csv
        └── ...
```

### Contract Structure

```python
# tests/contracts/grir_exposures.py
"""
Contract tests for GRIR Exposures output.

These tests encode business rules that must ALWAYS be true,
regardless of implementation details.
"""

import pandas as pd
import pytest

VALID_TIME_BUCKETS = [
    "<1 month", 
    "1-3 months", 
    "3-6 months", 
    "6-12 months", 
    ">1 year"
]


def load_grir_with_po_data():
    """Load GRIR exposures joined with PO line items."""
    grir = pd.read_csv("data/import-ready/grir_exposures.csv")
    po = pd.read_csv("data/intermediate/po_line_items.csv")
    return grir.merge(po, left_on="po_line_id", right_on="PO Line ID")


class TestGRIRBusinessRules:
    """Business rule contracts - these define correctness."""
    
    def test_no_closed_po_exposures(self):
        """CLOSED POs cannot have exposure - they're already settled."""
        df = load_grir_with_po_data()
        closed_pos = df[df["PO Receipt Status"] == "CLOSED PO"]
        assert len(closed_pos) == 0, f"Found {len(closed_pos)} CLOSED PO exposures"
    
    def test_grir_qty_is_positive(self):
        """GRIR qty must be positive - negative means GR > IR (no exposure)."""
        df = pd.read_csv("data/import-ready/grir_exposures.csv")
        invalid = df[df["grir_qty"] <= 0]
        assert len(invalid) == 0, f"Found {len(invalid)} non-positive GRIR quantities"
    
    def test_valid_time_buckets(self):
        """Time bucket must be one of the defined categories."""
        df = pd.read_csv("data/import-ready/grir_exposures.csv")
        invalid = df[~df["time_bucket"].isin(VALID_TIME_BUCKETS)]
        assert len(invalid) == 0, f"Invalid time buckets: {invalid['time_bucket'].unique()}"
    
    def test_only_simple_pos(self):
        """GRIR only applies to Simple POs (GLD + K/P/S/V)."""
        df = load_grir_with_po_data()
        
        non_gld = df[df["Main Vendor SLB Vendor Category"] != "GLD"]
        assert len(non_gld) == 0, "Found non-GLD vendor exposures"
        
        invalid_cat = df[~df["PO Account Assignment Category"].isin(["K", "P", "S", "V"])]
        assert len(invalid_cat) == 0, "Found invalid account category exposures"


class TestGRIRDataQuality:
    """Data quality contracts - these define completeness."""
    
    def test_no_null_required_fields(self):
        """Required fields cannot be null."""
        df = pd.read_csv("data/import-ready/grir_exposures.csv")
        
        required = ["po_line_id", "grir_qty", "grir_value", "snapshot_date"]
        for col in required:
            null_count = df[col].isna().sum()
            assert null_count == 0, f"Column {col} has {null_count} nulls"
    
    def test_snapshot_date_is_recent(self):
        """Snapshot date should be within last 7 days."""
        df = pd.read_csv("data/import-ready/grir_exposures.csv")
        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
        
        max_age = (pd.Timestamp.now() - df["snapshot_date"].max()).days
        assert max_age <= 7, f"Snapshot is {max_age} days old"


class TestGRIRGoldenComparison:
    """Golden file comparisons - these detect unexpected changes."""
    
    def test_row_count_stability(self):
        """Row count should not change dramatically without explanation."""
        df = pd.read_csv("data/import-ready/grir_exposures.csv")
        
        # Baseline from initial implementation
        expected_range = (50, 100)  # Adjust based on actual data
        
        assert expected_range[0] <= len(df) <= expected_range[1], \
            f"Row count {len(df)} outside expected range {expected_range}"
```

### Running Contracts

```bash
# Run all contract tests
pytest tests/contracts/ -v

# Run specific contract
pytest tests/contracts/grir_exposures.py -v

# Run as part of pipeline
python3 scripts/pipeline.py && pytest tests/contracts/ -v
```

---

## Phase 2: Enforcement Layer

### Rationale

> "Enforcement without usability will be bypassed. Add fast paths and cached results to avoid developer friction."
> — Apex Agent

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: oracle-compliance
        name: Oracle Compliance Check
        entry: python3 scripts/check_oracle_compliance.py
        language: system
        files: ^scripts/.*\.py$
        pass_filenames: true
```

### Compliance Checker

```python
# scripts/check_oracle_compliance.py
"""
Pre-commit hook to enforce Oracle usage and data profiling.

Checks:
1. oracle verify was run for new symbols
2. oracle impact was run for modified scripts
3. profile_data.py was run for filter columns
4. Test file exists for new scripts

Uses caching to avoid re-running expensive checks.
"""

import sys
import json
import subprocess
from pathlib import Path

CACHE_FILE = Path(".oracle-compliance-cache.json")
ARTIFACTS_DIR = Path("pipeline-context/compliance")


def check_file(filepath: str) -> list[str]:
    """Check a single file for compliance. Returns list of violations."""
    violations = []
    
    # Check 1: If new script, must have corresponding test
    if is_new_file(filepath):
        test_path = get_test_path(filepath)
        if not test_path.exists():
            violations.append(f"Missing test file: {test_path}")
    
    # Check 2: If modifying existing script, must have impact analysis
    if is_modified_file(filepath):
        impact_artifact = get_impact_artifact(filepath)
        if not impact_artifact.exists():
            violations.append(f"Missing impact analysis. Run: oracle impact {filepath}")
    
    # Check 3: If script has filter operations, must have profile artifacts
    filter_columns = extract_filter_columns(filepath)
    for col in filter_columns:
        profile_artifact = get_profile_artifact(col)
        if not profile_artifact.exists():
            violations.append(f"Missing profile for filter column '{col}'")
    
    return violations


def main():
    files = sys.argv[1:]
    all_violations = []
    
    for f in files:
        violations = check_file(f)
        all_violations.extend(violations)
    
    if all_violations:
        print("Oracle Compliance Violations:")
        for v in all_violations:
            print(f"  - {v}")
        print("\nRun missing commands or use --no-verify to bypass (not recommended)")
        sys.exit(1)
    
    print("Oracle compliance: PASSED")
    sys.exit(0)
```

### Compliance Artifacts

```
pipeline-context/
├── compliance/
│   ├── impacts/
│   │   └── 06_calculate_grir.json    # Output of oracle impact
│   ├── profiles/
│   │   └── PO_Receipt_Status.json    # Output of profile_data.py
│   └── verifications/
│       └── session_2024-11-30.json   # Symbols verified this session
```

### Fast Path Helpers

```bash
# Record all compliance artifacts for current changes
python3 scripts/record_compliance.py

# This runs:
# 1. oracle impact for each modified script
# 2. profile_data.py for each filter column
# 3. oracle verify for each new symbol
# 4. Saves all outputs to compliance/ folder
```

---

## Phase 3: Self-Healing Validation

### Rationale

> "One-shot perfection is brittle. Self-healing is anti-fragile. Reliability comes from RECOVERY capability, not initial guess."
> — Prism Agent

### The Intent Flag (Critical Addition)

Without this, the agent would try to "fix" intentional changes:

```python
# Agent commits expected impact BEFORE running validation
# File: pipeline-context/intents/06_calculate_grir.json
{
    "script": "06_calculate_grir.py",
    "timestamp": "2024-11-30T15:00:00Z",
    "expected_impacts": {
        "row_count": {
            "direction": "decrease",
            "range": [-30, -10],  # Expect 10-30% decrease
            "reason": "Filtering out CLOSED PO status"
        },
        "null_rate": {
            "column": "first_exposure_date",
            "max_allowed": 5.0,
            "reason": "Some POs may have concurrent GR/IR"
        }
    }
}
```

### Validation Pipeline

```python
# scripts/validate_pipeline.py
"""
Self-healing validation pipeline.

1. Runs pipeline stage with sample data
2. Compares against golden baseline OR intent flags
3. Reports semantic diffs
4. Agent can self-correct without user input (if within intent bounds)
"""

def validate_stage(stage_name: str, intent_file: Path = None):
    """Validate a pipeline stage output."""
    
    # Load baseline and current output
    baseline = load_baseline(stage_name)
    current = load_current_output(stage_name)
    intent = load_intent(intent_file) if intent_file else None
    
    # Calculate diffs
    diffs = calculate_semantic_diff(baseline, current)
    
    # Check against intent
    violations = []
    for diff in diffs:
        if intent and is_within_intent(diff, intent):
            print(f"EXPECTED: {diff}")
        else:
            violations.append(diff)
            print(f"UNEXPECTED: {diff}")
    
    return violations


def calculate_semantic_diff(baseline: pd.DataFrame, current: pd.DataFrame) -> list:
    """Calculate meaningful differences, not just line changes."""
    diffs = []
    
    # Row count change
    row_diff = len(current) - len(baseline)
    row_pct = (row_diff / len(baseline)) * 100
    if abs(row_pct) > 1:
        diffs.append({
            "type": "row_count",
            "change": row_diff,
            "pct": row_pct,
            "message": f"Row count changed by {row_pct:.1f}%"
        })
    
    # Null rate changes
    for col in current.columns:
        if col in baseline.columns:
            old_null = baseline[col].isna().mean()
            new_null = current[col].isna().mean()
            if abs(new_null - old_null) > 0.01:
                diffs.append({
                    "type": "null_rate",
                    "column": col,
                    "old": old_null,
                    "new": new_null,
                    "message": f"Null rate for {col} changed from {old_null:.1%} to {new_null:.1%}"
                })
    
    # Value distribution changes (for categoricals)
    for col in current.select_dtypes(include=['object']).columns:
        if col in baseline.columns:
            old_dist = baseline[col].value_counts(normalize=True)
            new_dist = current[col].value_counts(normalize=True)
            # ... compare distributions
    
    return diffs
```

### Self-Correction Loop

```python
def self_healing_loop(script_path: str, max_iterations: int = 3):
    """
    Agent attempts to fix validation failures automatically.
    
    Loop:
    1. Run script
    2. Validate output
    3. If violations found, analyze and fix
    4. Repeat until clean or max iterations
    """
    for i in range(max_iterations):
        print(f"\n=== Iteration {i+1}/{max_iterations} ===")
        
        # Run the script
        run_script(script_path)
        
        # Validate
        violations = validate_stage(get_stage_name(script_path))
        
        if not violations:
            print("Validation PASSED")
            return True
        
        print(f"Found {len(violations)} violations")
        
        # Attempt self-correction
        for v in violations:
            fix = suggest_fix(v, script_path)
            if fix:
                print(f"Applying fix: {fix['description']}")
                apply_fix(fix)
            else:
                print(f"Cannot auto-fix: {v['message']}")
                return False  # Need human intervention
    
    print(f"Max iterations reached. Human review required.")
    return False
```

---

## Phase 4: Shadow Deployment + Observability

### Shadow Deployment

> "Use PostgreSQL Transactional DDL. Run in transaction, validate, then ROLLBACK (testing) or COMMIT (deployment). Zero schema pollution."
> — Prism Agent

```python
# scripts/shadow_deploy.py
"""
Shadow deployment using PostgreSQL transactions.

1. Begin transaction
2. Run all migrations/changes
3. Execute validation queries
4. If valid: COMMIT
5. If invalid: ROLLBACK
"""

async def shadow_deploy(changes: list[Change]) -> DeployResult:
    async with db.transaction() as tx:
        # Apply changes
        for change in changes:
            await tx.execute(change.sql)
        
        # Run validations
        validations = await run_validations(tx)
        
        if all(v.passed for v in validations):
            await tx.commit()
            return DeployResult(success=True, validations=validations)
        else:
            await tx.rollback()
            return DeployResult(success=False, validations=validations)
```

### Observability Stack

```python
# scripts/observability/metrics.py
"""
Pipeline observability metrics.

Tracks:
- Row counts per stage
- Null rates per column
- Filter drop attribution
- Runtime per stage
- Error rates
"""

@dataclass
class PipelineMetrics:
    stage: str
    timestamp: datetime
    
    # Volume metrics
    input_rows: int
    output_rows: int
    rows_dropped: int
    drop_rate: float
    
    # Quality metrics
    null_rates: dict[str, float]
    
    # Performance metrics
    runtime_seconds: float
    
    # Attribution
    drop_attribution: dict[str, int]  # {filter_name: rows_dropped}
    
    # Lineage
    commit_hash: str
    pipeline_version: str


def collect_metrics(stage: str, before: pd.DataFrame, after: pd.DataFrame) -> PipelineMetrics:
    """Collect metrics for a pipeline stage."""
    return PipelineMetrics(
        stage=stage,
        timestamp=datetime.now(),
        input_rows=len(before),
        output_rows=len(after),
        rows_dropped=len(before) - len(after),
        drop_rate=(len(before) - len(after)) / len(before),
        null_rates={col: after[col].isna().mean() for col in after.columns},
        runtime_seconds=get_stage_runtime(stage),
        drop_attribution=get_drop_attribution(before, after),
        commit_hash=get_current_commit(),
        pipeline_version=get_pipeline_version()
    )
```

### Alerting

```yaml
# config/alerts.yaml
alerts:
  - name: high_drop_rate
    condition: drop_rate > 0.5
    severity: critical
    message: "Stage {stage} dropped {drop_rate:.0%} of rows"
    
  - name: null_spike
    condition: null_rate_change > 0.1
    severity: warning
    message: "Column {column} null rate increased by {null_rate_change:.0%}"
    
  - name: row_count_anomaly
    condition: abs(row_count_change) > 0.2
    severity: warning
    message: "Stage {stage} row count changed by {row_count_change:.0%}"

routing:
  critical: ["#alerts-critical", "oncall@company.com"]
  warning: ["#alerts-pipeline"]
```

---

## Phase 5: Scale Infrastructure

### Problem at 20x Scale

| Artifact | Current | At 20x | Issue |
|----------|---------|--------|-------|
| Skeleton Index | 81 lines | ~1,600 lines | Exceeds context window |
| Pipeline Map | 1,400 lines | ~28K lines | Can't read fully |
| Symbol Registry | 58 functions | ~1,160 functions | Search returns too many |
| Lineage Graph | 214 nodes | ~4,280 nodes | Impact prediction noisy |

### Solution: Semantic Search

```python
# scripts/oracle_search.py
"""
Semantic search over codebase using embeddings.

Instead of: "Read all skeletons to find relevant code"
Now: "Find scripts that filter POs" -> Returns top 3 matches
"""

from sentence_transformers import SentenceTransformer

class SemanticOracle:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = self.load_or_build_index()
    
    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Search codebase by semantic meaning."""
        query_embedding = self.model.encode(query)
        
        # Search index
        results = self.index.search(query_embedding, top_k)
        
        return [
            SearchResult(
                file=r.file,
                function=r.function,
                snippet=r.snippet,
                relevance=r.score
            )
            for r in results
        ]
    
    def build_index(self):
        """Build searchable index from codebase."""
        documents = []
        
        # Index functions with their docstrings
        for func in self.registry.functions:
            doc = f"{func.name}: {func.docstring}"
            documents.append(Document(
                text=doc,
                file=func.file,
                function=func.name,
                embedding=self.model.encode(doc)
            ))
        
        # Index columns with their usage context
        for col in self.registry.columns:
            doc = f"Column {col.name} used in {col.scripts}"
            documents.append(Document(
                text=doc,
                type="column",
                name=col.name,
                embedding=self.model.encode(doc)
            ))
        
        return VectorIndex(documents)
```

### Incremental Oracle Updates

```python
# scripts/oracle_watcher.py
"""
File watcher for incremental Oracle regeneration.

Instead of: Full regeneration on every change
Now: Partial regeneration only for changed files
"""

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class OracleWatcher(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            # Only regenerate affected artifacts
            self.update_symbol_registry(event.src_path)
            self.update_lineage_graph(event.src_path)
            # Don't regenerate skeletons for unchanged files
    
    def update_symbol_registry(self, changed_file: str):
        """Update only the symbols from the changed file."""
        # Remove old symbols from this file
        self.registry.remove_file(changed_file)
        
        # Extract and add new symbols
        new_symbols = extract_symbols(changed_file)
        self.registry.add_symbols(new_symbols)
        
        # Save incrementally
        self.registry.save()
```

### Domain Partitioning

```
pipeline-context/
├── domains/
│   ├── procurement/           # PO, GR, IR related
│   │   ├── skeletons/
│   │   ├── symbols.json
│   │   └── lineage.json
│   ├── finance/               # Cost impact, GRIR, budgets
│   │   ├── skeletons/
│   │   ├── symbols.json
│   │   └── lineage.json
│   └── inventory/             # Reservations, stock
│       ├── skeletons/
│       ├── symbols.json
│       └── lineage.json
├── global/
│   ├── patterns/              # Shared patterns
│   └── cross-domain-lineage.json
└── search-index/              # Semantic search index
    └── embeddings.bin
```

---

## Success Metrics

### Reliability SLOs

| Metric | Target | Measurement |
|--------|--------|-------------|
| User corrections needed | < 5% | Corrections / Total implementations |
| Edge cases caught proactively | > 95% | Profiled issues / Total issues |
| Test coverage on new features | 100% | New features with tests / Total new |
| Mean time to rollback | < 5 min | Measured from detection |
| Escaped defects | < 1/month | Bugs found in production |

### Phase Completion Criteria

| Phase | Complete When |
|-------|---------------|
| 0 | `profile_data.py` used in every implementation |
| 1 | Contract tests exist for all output files |
| 2 | Pre-commit hook blocks non-compliant changes |
| 3 | Self-healing catches 80%+ of validation failures |
| 4 | All stages have observability dashboards |
| 5 | Search returns relevant results in < 1 second |

---

## Appendix A: Decision Log

### Why "Recovery" over "Perfection"

**Input from Prism:**
> "100% correct on first attempt is mathematically impossible due to the ambiguity of natural language. If a user says 'clean the data,' and the agent removes rows the user wanted to keep, the agent was 'logical' but 'wrong'."

**Decision:** Target 100% recovery capability, not 100% accuracy.

### Why Contracts Before Self-Healing

**Input from Prism:**
> "Skip to Contract Testing. Writing assertions BEFORE code is more valuable than complex self-healing pipelines. Contracts are clear, binary, and enforce business logic directly."

**Decision:** Phase 1 is contracts, Phase 3 is self-healing.

### Why PostgreSQL Transactions over Shadow Tables

**Input from Prism:**
> "Maintaining parallel schema definitions is a nightmare for Drizzle/Migrations. Use PostgreSQL Transactional DDL instead."

**Decision:** Use `BEGIN/ROLLBACK` for shadow testing, not `_shadow` table suffix.

---

## Appendix B: Agent Collaboration Credits

This plan was developed through structured collaboration:

- **Prism Agent**: Provided "Data Archaeologist" workflow, self-healing paradigm, intent flags, confidence thresholds, and the critical insight about static vs. dynamic analysis
- **Apex Agent**: Provided enforcement specifics, observability requirements, compliance artifacts, and scalability concerns

Both agents reviewed and validated the final plan.

---

## Appendix C: Quick Reference

### Daily Workflow Checklist

```markdown
## Before Implementing Any Feature

- [ ] Profile relevant columns: `python3 scripts/profile_data.py <file> <col>`
- [ ] State assumptions explicitly with confidence level
- [ ] Run impact analysis: `python3 scripts/ask_oracle.py impact <script>`
- [ ] Check column usage: `python3 scripts/ask_oracle.py who <col>`
- [ ] If Low Confidence: STOP and ask user

## During Implementation

- [ ] Follow patterns: `python3 scripts/ask_oracle.py pattern <type>`
- [ ] Verify symbols: `python3 scripts/ask_oracle.py verify <name>`
- [ ] Read full source before editing (not just skeleton)

## After Implementation

- [ ] Run type-check: `npm run type-check`
- [ ] Run pipeline: `python3 scripts/pipeline.py`
- [ ] Run contracts: `pytest tests/contracts/ -v`
- [ ] Commit with compliance artifacts
```

---

*Last Updated: November 2024*
*Version: 1.0*
