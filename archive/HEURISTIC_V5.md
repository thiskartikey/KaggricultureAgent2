# Heuristic Agent Archive — v5 (DT Hybrid)

> **Status: ARCHIVED.** Do not import directly. This documents the full heuristic engine
> that was replaced by the pure Decision Transformer `policy.py`.
> Read this file only when explicitly asked to reference the heuristic.

---

## Overview

`heuristic_policy_v5.py` is the full source of the v5 heuristic-DT hybrid agent.
Strategy mined from 72 leaderboard replays (top scores 100k–158k).

**Best score achieved:** ~70k (pure heuristic mode), ~62k (DT hybrid).
**Theoretical ceiling:** ~150–158k (market price saturation).

---

## Architecture

The policy was a **hybrid**: the Decision Transformer (DT) set a macro-task priority for the
farmer, while the full heuristic engine (`_assign_tasks`, `_build_tasks`, `_make_market_orders`)
still drove the hands and market independently. This caused misalignment between DT macro-decisions
and the heuristic's spending/hiring logic, leading to poor real-world performance.

---

## Key Components

### Market Primitives (Lines 40–151)
- `price(resource, inv)` — mirrors the engine's `market_price()` exactly
- `buy_cost`, `sell_revenue`, `marginal_revenue`, `units_sellable_above`
- `should_plant`, `plant_expected_profit`, `should_buy_animal`
- `plan_sells` — greedy sell planner respecting feed hold

### Constants (Lines 154–189)
```python
TARGET_WHEAT = 8
TARGET_STRAWBERRY = 30
TARGET_MELON = 62
TARGET_COW = 8
TARGET_SHEEP = 6
LAND_UNLOCK_DAY = (7, 11, 15)
SHED_CAP = 100
CASH_FLOOR = 350
```

### Scanning (Lines 334–392)
- `_scan(me, day, total_days)` — classifies every tile into task buckets:
  `feed`, `service`, `service_soon`, `harvest_crop`, `water`, `water_soon`,
  `weeds`, `plant`, `build_pasture`, `build_coop`, `fertilize`, `place_animal`

### Task System (Lines 670–862)
- `TASK_TIER` dict — strict priority ordering (0 = emergency, 3 = low)
- `_build_tasks` — converts scan results into a flat task list
- `_assign_tasks(positions, tasks, invs, board, claims, feed_cells, custom_tier)`
  — tier-by-tier greedy nearest-pair matching with sticky claims

### Market Orders (Lines 539–665)
Order of priority (after fix applied in session):
1. R1: Day 0 opening (hardcoded blueprint)
2. R2: Sell produce
3. **R7 (moved up): Buy seeds first**
4. **R5 (moved up): Buy wheat feed reserve**
5. R3: Hire workers (`target_hands` schedule)
6. R4: Buy land (day 7 → NE, day 11 → SW)
7. R6: Buy animals

### DT Integration (Lines 1081–1187, `_agent`)
The DT predicts an `act_id` (0–7), which is translated to a boosted `TASK_TIER` priority:
```python
custom_tier = dict(TASK_TIER)
if dt_assigned_task:
    custom_tier[dt_task_type] = 0.5  # between Tier 0 (emergency) and Tier 1 (high)
```
The farmer executes the DT task; the hands follow the boosted tier via `_assign_tasks`.

---

## Known Issues (Why It Was Replaced)

1. **Market over-hiring:** Before the fix, hiring (R3) ran before seeds (R7) and feed (R5),
   draining the budget before survival needs were met → animal starvation and zero seeds.
2. **Crop target mismatch:** `TARGET_STRAWBERRY = 20, TARGET_MELON = 65` vs top-player
   blueprint of `42 STRAWBERRY, 12 MELON` (ongoing vs one-shot economics).
3. **Partial DT control:** DT only directed the farmer; hands continued under heuristic
   priorities, creating strategy divergence.
4. **New-land neglect:** Empty tiles in new quadrants were sorted by shed distance,
   meaning far tiles never received plant tasks when seeds were scarce.

---

## Full Source

See [`heuristic_policy_v5.py`](./heuristic_policy_v5.py) in this directory.
