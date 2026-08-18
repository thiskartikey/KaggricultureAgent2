# Implementation Plan: Subsystem D (Pool-Backed Autonomous Ratchet Engine)

> **Owner**: Subsystem D Lead
> **Target Files**: `src/autoresearch/controller.py`, `src/autoresearch/hypothesis.py`, `src/autoresearch/evaluator.py`, `src/autoresearch/pool_evaluator.py`

---

## 1. Objectives
1. Connect `src/autoresearch/controller.py` directly to `pool_evaluator.py` for all Tier 2 / Tier 3 structural candidate evaluations.
2. Expand `src/autoresearch/hypothesis.py` with structured Tier 2 blocks targeting shop adaptation and compound animal servicing.
3. Verify that `python -m src.autoresearch.controller --test-ratchet` passes with zero regressions.

---

## 2. Technical Roadmap

1. **Evaluator Cascade**:
   - Stage 0: `test_policy_invariants.py` (0.5s)
   - Stage 1: Fast screen vs baseline (2 seeds, 4 games)
   - Stage 4: Opponent Pool Evaluator (5 opponents, 40 games)
   - Decision Engine: Multi-metric evaluation (Pool Mean $\Delta > 0$ and Win Rate $\ge 50\%$).
2. **Safety & Git Integrity**:
   - Atomic git branching per experiment (`experiment/EXP-YYYYMMDD-XX`).
   - Hard rollback (`git reset --hard HEAD` and `git clean -fd`) upon rejection.
   - Automatic champion tagging upon promotion.
