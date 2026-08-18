# Implementation Plan: Subsystem B (Evaluation & Benchmark Harness Repair)

> **Owner**: Subsystem B Lead
> **Target Files**: `eval_seeds.py`, `evaluate.py`, `src/autoresearch/pool_evaluator.py`

---

## 1. Objectives
1. Make `eval_seeds.py` fully robust, accepting custom candidate paths, custom opponent paths (or built-in `"starter"`), executing dual-seat games per seed, and producing statistically rigorous output.
2. Upgrade `evaluate.py` to support `--debug` (full error tracebacks on agent failure) and `--pool` (running a benchmark match against the 5 historical champion pool).
3. Validate all changes with zero broken tests.

---

## 2. Detailed Technical Specifications

### 2.1 Refactor `eval_seeds.py`
- **CLI Syntax**:
  ```bash
  python eval_seeds.py [candidate_policy] [opponent] [--seeds N] [--workers W] [--single-seat]
  ```
- **Defaults**:
  - `candidate_policy`: `policy.py`
  - `opponent`: `starter`
  - `seeds`: 10 seeds `[7, 42, 101, 202, 303, 404, 505, 606, 707, 808]`
- **Behavior**:
  - Automatically resolves relative paths or built-ins.
  - Plays each seed in both seats by default (20 games for 10 seeds).
  - Calculates paired delta: $\Delta = \text{Score}_{\text{cand}} - \text{Score}_{\text{opp}}$.
  - Outputs summary table with mean, median, min, max, std dev, win rate, and tie count.

### 2.2 Upgrade `evaluate.py`
- Add `--debug` argument. In debug mode, exceptions raised in `kaggle_environments` print the complete traceback and step metadata instead of returning `(None, None)`.
- Support built-in agent names (e.g. `"starter"`) without requiring `os.path.exists()`.
- Add `--pool` mode to trigger `src.autoresearch.pool_evaluator`.

---

## 3. Verification Steps
1. Run `python eval_seeds.py policy.py starter --seeds 4` $\rightarrow$ Confirm execution of 8 games (2 seats $\times$ 4 seeds) with complete score table.
2. Run `python evaluate.py policy.py versions/Phase2_v1_policy.py --games 4 --debug` $\rightarrow$ Confirm clean completion with paired t-test output.
3. Run `pytest tests/` $\rightarrow$ Confirm 105+ tests pass.
