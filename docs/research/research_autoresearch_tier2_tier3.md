# Research Report: Autonomous Ratchet Scaling (Tier 2 & Tier 3 Search Space) (Subsystem D)

> **Zero-Hallucination Protocol Compliance**: Verified against `src/autoresearch/hypothesis.py`, `src/autoresearch/mutator.py`, `src/autoresearch/controller.py`, and `src/autoresearch/pool_evaluator.py`.

---

## 1. The Ceiling of Tier 1 Parameter Tuning

Tier 1 mutations modify scalar constants (e.g. `TARGET_STRAWBERRY`, `TARGET_MELON`, `CASH_FLOOR`, `TASK_TIER` weights).
Over 138 experiments in `experiments/experiments.jsonl`, Tier 1 parameter space was systematically explored:
- Early gains: +17,859 vs Phase 2 baseline.
- Subsequent iterations: 125 rejected experiments due to parameter saturation.

To make further leaps (from ~88k to 120k–140k+), the ratchet must explore **structural mutations**:

---

## 2. Structural Mutation Tiers

### Tier 2: Logic Block Mutations (AST Swaps)
Instead of tweaking numeric thresholds, Tier 2 replaces entire semantic functions or conditional blocks in `policy.py`:
1. **Dynamic Shop Response Block**: Replaces static `_seed_targets` with shop-aware dynamic target computation.
2. **Animal Service Routine Block**: Replaces sequential `_unit_op` pasture handling with atomic compound service (Pickup Wheat $\rightarrow$ Walk $\rightarrow$ Harvest $\rightarrow$ Feed $\rightarrow$ Care $\rightarrow$ Collect).
3. **Smart Market Liquidation Block**: Injects Day 29 sell-all orders in `_make_market_orders`.

### Tier 3: Macro-Schedule Mutations
Mutating the timeline coordination rules:
1. **Adaptive Land Purchase Timers**: Modulating `LAND_UNLOCK_DAY` dynamically based on cash velocity rather than fixed days 7 and 9.
2. **Dynamic Labor Sizing**: Sizing daily farm hands based on the active task count rather than fixed day targets.

---

## 3. Eliminating the Self-Play Blind Spot via Stage 4 Pool Evaluation

Previously, the ratchet evaluated candidates using Stage 1 (2 seeds) $\rightarrow$ Stage 2 (8 seeds) $\rightarrow$ Stage 3 (16 seeds) in **self-play**.
When a candidate introduced a macro-economic improvement (like dynamic shop response), both seats played with the new intelligence, leading to symmetric play and $\Delta = 0$ ($p = 1.0$), triggering an automatic rejection!

**The Breakthrough Architecture**:
Every candidate that passes Stage 0 (Invariants) is passed through **Stage 4 (Opponent Pool Evaluator)** against the 5-opponent benchmark pool.
A candidate is promoted if:
1. Pool mean score exceeds current champion pool mean ($\ge 88,662$).
2. Win rate vs strong opponents ($\ge 65k$) is $\ge 50\%$.
3. Stage 0 invariant checks pass with zero warnings and execution speed $< 15$ ms/step.
