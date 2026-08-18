# Agent Policy — Champion Heuristic (current: EXP-20260815-69)

This document describes the strategy implemented in [`policy.py`](../policy.py).

## Current State: Pure Heuristic Blueprint Engine (880 lines)

`policy.py` is a **pure heuristic strategy** mined from top-player leaderboard replays. It scores
roughly **65k–72k** in self-play against Phase2_v1 (Δmean ≈ +17k vs v1 baseline). The champion
version is archived at `versions/EXP-20260815-69_policy.py`.

### Strategy Blueprint
- **Land:** 3 quadrants only (NE day 7, SW day 9; never the 4th at 4000). `LAND_UNLOCK_DAY = (7, 9)`.
- **Labor:** 5 hands day 0, 3 days 1–4, 8 days 5–8, 13 from day 9, 10 in final 2 days. Daily re-hire (fib cost).
- **Animals:** 14 PASTURE (8 COW + 6 SHEEP), all fed and cared daily. `TARGET_PASTURE_BY_DAY = ((11,14),(7,12),(0,6))`.
- **Crops:** 35 STRAWBERRY, 9 MELON, ~7 WHEAT (2-day cycle filler and feed).
- **Market:** Sell all produce every turn (no price reserve). Wheat held for feed buffer = 2-day supply. Buffer tapers to 0 on final day.
- **Fertilize:** Applied to ongoing crops (STRAWBERRY) at tier 1 priority (same urgency as harvest).
- **Tactics:** Tier-based task assignment (service → water → harvest/fertilize/place_animal → build → plant → weed); sticky claims to prevent oscillation; separate feed-carriers; CARE on all animals daily; shed-proximity ordering of free cells; endgame plant promotion (day ≥ 20: plant tier raised to 1).

### Key Constants (current champion values)

| Constant | Value |
|---|---|
| `TARGET_COW` | 8 |
| `TARGET_SHEEP` | 6 |
| `TARGET_STRAWBERRY` | 35 |
| `TARGET_MELON` | 9 |
| `LAND_UNLOCK_DAY` | (7, 9) |
| `CASH_FLOOR` | 200 |
| `SHED_CAP` | 100 |
| `target_hands` returns | 5 / 3 / 8 / 13 / 10 (by phase) |

### Dead Code Removed

All DT/RL dead code (`DecisionTransformer`, `obs_to_vec`, `get_dt_task`, `macro_to_farmer_op`,
`resolve_farmer_op`, `DT_MODEL`, `STATE_HISTORY`, etc.) was removed in the health-check cleanup.
`policy.py` is now 880 lines with zero dead code.

### Previously Discarded Experiments (do not retry)

| Change | Result | Notes |
|---|---|---|
| `LAND_UNLOCK_DAY = (6, 10)` | −5,542 (p=0.000) | Agent can't afford NE unlock until day 7–8 regardless |
| Day-0 `4 HIRE + 1 COW + 4 SHEEP` | −9,401 (p=0.000) | Budget overrun, starves melon seed coverage |
| `target_hands` day 1 = 1 | −11,509 (p=0.000) | Labour starvation on day 1 |
| Goose/COOP setup | −7,085 | Egg revenue can't recover build cost |
| Crew 15 vs 13 | −22,138 (p=0.000) | Fib cost explodes past 13 |
| `TARGET_PASTURE_BY_DAY = ((10,14),(7,9),(0,6))` | −6,389 (p=0.000) | Drops mid-game target to 9 |
| Price reserve on sells | −3,457 vs no-reserve | Sell-all every turn is always better |
