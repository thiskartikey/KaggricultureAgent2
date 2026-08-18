# Implementation Plan: Subsystem A (Policy Architecture Breakthrough)

> **Owner**: Subsystem A Lead
> **Target Files**: `policy.py`, `tests/test_policy_invariants.py`

---

## 1. Objectives
1. Implement the Dynamic Shop Demand Analyzer in `policy.py` to adapt crop allocations.
2. Synchronize animal feeding and care in single-visit worker routines.
3. Add Endgame Inventory Liquidation starting Day 29.
4. Verify full compliance with `test_policy_invariants.py` and run Opponent Pool Evaluator.

---

## 2. Verification Protocol (Zero-Hallucination)
- Pre-change: Run `pytest tests/test_policy_invariants.py` $\rightarrow$ must pass.
- Post-change: Run `pytest tests/test_policy_invariants.py` $\rightarrow$ must pass.
- Multi-stage gate:
  1. Stage 0: `test_policy_invariants.py`
  2. Stage 1: Fast screen (2 seeds, 4 games vs champion baseline)
  3. Stage 4: Opponent Pool Evaluator (5 historical opponents, 40 games).
