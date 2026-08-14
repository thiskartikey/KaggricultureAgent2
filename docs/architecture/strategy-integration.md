# Strategy Integration Architecture

> Phase 0 deliverable — how mined rules from replay analysis plug into the production agent.

---

## 1. Integration Points in `policy.py`

The production heuristic has five well-defined extension points where replay-derived rules can be inserted with minimal refactoring risk:

| Integration Point | Function | What to Change |
|---|---|---|
| **Blueprint Constants** | Module-level (`TARGET_COW`, etc.) | Adjust numeric targets based on empirical evidence |
| **Labour Schedule** | `target_hands(day, total_days)` | Tune crew size per phase |
| **Land Unlock Schedule** | `_make_market_orders` R4 / `LAND_UNLOCK_DAY` | Change NE/SW unlock days |
| **Market Order Logic** | `_make_market_orders` | Add/modify sell timing, wheat-buy triggers, animal purchase gates |
| **Task Prioritisation** | `TASK_TIER` dict + `_build_tasks` | Add new task types or change tier assignments |

---

## 2. Rule Insertion Pattern

For each extracted decision rule, the implementation follows this pattern:

```python
# Example: adjust TARGET_COW / TARGET_SHEEP from empirical evidence
# Before (Phase2_v1):
TARGET_COW   = 8
TARGET_SHEEP = 6

# After (evidence: 96% of wins have 9+ cows when HealthStone plays):
TARGET_COW   = 9    # RULE-LIVESTOCK-001
TARGET_SHEEP = 5    # RULE-LIVESTOCK-002
```

For conditional rules that depend on game state:

```python
# Inside _make_market_orders:
# RULE-LAND-003: Delay NE unlock to day 8 if money < 1500 at day 6
if quads - 1 < len(LAND_UNLOCK_DAY) and day >= LAND_UNLOCK_DAY[quads - 1]:
    if day == 6 and money_left < 1500:
        pass  # delay
    elif money_left >= cost + CASH_FLOOR and len(orders) < 10:
        orders.append(["BUY_LAND"])
```

---

## 3. Gating Protocol

**No rule touches `policy.py` until it passes all gates:**

```
Gate 1: n ≥ 300 parsed games complete           [PASSED — 147,600 turns / 205 episodes]
Gate 2: Phase2_v1_policy.py baselined 16 games  [TODO — run before Phase 9C]
Gate 3: Each PR evaluated with --games 8        [TODO — per experiment]
Gate 4: Promotion requires p < 0.05, Δmean > 0 [TODO — per experiment]
```

---

## 4. Versioning Convention

| File | Role |
|---|---|
| `policy.py` | **HEAD** — always the latest experiment under test |
| `versions/Phase2_v1_policy.py` | **Frozen baseline** — never modified |
| `versions/Phase2_v2_policy.py` | First promoted improvement (once Gate 4 cleared) |

Every accepted experiment is tagged as `Phase2_vN_policy.py` and becomes the new baseline for the next experiment.

---

## 5. Submission Safety Checklist

Before any `policy.py` commit:
1. `grep -n 'import torch\|import tensorflow\|import gym' policy.py` → 0 matches
2. `grep -n '^\s*print(' policy.py` → 0 unshielded prints
3. Single-step execution time < 15 ms (check with `debug_policy.py`)
4. `python evaluate.py policy.py versions/Phase2_v1_policy.py --games 2` completes without errors
