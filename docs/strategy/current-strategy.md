# Current Strategy Documentation

> Reflects champion policy `EXP-20260815-69` (current `policy.py`).

The production strategy is fully documented in [`docs/architecture/current-agent.md`](../architecture/current-agent.md).

## Current Constants vs Phase2_v1 Baseline

| Parameter | Phase2_v1 (baseline) | Current Champion | Gap Status |
|---|---|---|---|
| `TARGET_STRAWBERRY` | 42 | **35** | ✅ Optimised (lower = better given farm space) |
| `TARGET_MELON` | 12 | **9** | ✅ Optimised |
| `LAND_UNLOCK_DAY` | (7, 11) | **(7, 9)** | ✅ SW day 9 vs 11 (composite change) |
| `CASH_FLOOR` | 350 | **200** | ✅ Lower floor frees more buying power |
| Wheat feed buffer | 3 days | **2 days (tapering)** | ✅ Freed ~14 wheat units/day mid-game |
| Dropoff thresholds | carry≥10/6 | **carry≥5/3** | ✅ Enables intra-day wool/milk selling |
| Sell price reserve | yes (0.35–0.80) | **none (sell-all)** | ✅ Sell-all always beats holding |
| `TASK_TIER["fertilize"]` | 2 | **1** | ✅ Fertilizer 4.8× more valuable than market price |
| `TARGET_COW` | 8 | 8 | — unchanged |
| `TARGET_SHEEP` | 6 | 6 | — unchanged |
| `TARGET_PASTURE_BY_DAY` | ((11,14),(7,12),(0,6)) | ((11,14),(7,12),(0,6)) | — unchanged |

## Confirmed No-Ops / Regressions (do not re-test)

| Change | Result | Root Cause |
|---|---|---|
| `LAND_UNLOCK_DAY = (6, 10)` | −5,542 | Can't afford NE until day 7–8 regardless |
| `TARGET_PASTURE_BY_DAY = ((10,14),(7,9),(0,6))` | −6,389 | Drops mid-game target to 9 |
| `TARGET_COW = 9` | −1,081 | Leaning negative |
| `target_hands` day 1 = 1 | −11,509 | Labour starvation |
| Price reserve on any product | −3,457 | Shed overflow penalizes holding |
| Wheat buy buffer = 2 days in R5 | −7,426 | Animals starve |
