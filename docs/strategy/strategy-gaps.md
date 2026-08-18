# Strategy Gap Analysis

> Last updated against champion `EXP-20260815-69`.
>
> Priority Score = (Expected Impact × Evidence Confidence) / Implementation Cost

---

## Status Summary

| ID | Gap | Status | Notes |
|---|---|---|---|
| GAP-001 | Land unlock schedule | ✅ **RESOLVED** | `(7,9)` — SW moved to day 9 via composite mutation |
| GAP-002 | Pasture target | ✅ **TESTED — NO-OP** | `((10,14),(7,9))` is −6,389; current `((11,14),(7,12))` is optimal |
| GAP-003 | `target_hands` schedule | ✅ **OPTIMISED** | Current schedule validated vs many variants |
| GAP-004 | Wheat buffer | ✅ **FIXED** | 3-day → 2-day tapering buffer (+1,446 vs v7) |
| GAP-005 | `TARGET_COW = 9` | ❌ **REJECTED** | −1,081, leaning negative (p=0.089) |
| GAP-006 | Day 0 hires 5→4 | ❌ **REJECTED** | −7,280 (p=0.000) — 4 hands can't cover day-0 farm |
| GAP-007 | Dead DT/RL code | ✅ **DONE** | Removed in health-check cleanup (880 lines, zero dead code) |
| GAP-008 | Sell reserve | ✅ **FIXED** | Sell-all every turn — no reserve +3,457 vs v9 |
| GAP-009 | Melon planting cutoff | ✅ **CORRECT** | Already enforced by `left >= 13` in `_plant_choice` |
| GAP-010 | `CASH_FLOOR = 350` | ✅ **FIXED** | Lowered to 200 |

---

## Open Gaps (Untested or Partially Explored)

### GAP-NEW-001: Early Cash Generation (Days 0–5)

**Observation**: Top players unlock NE on day 6 because they generate ~$1,350 by then. Our agent
arrives at day 6 with only $198–226. The gap is not a configurable constant — it is a consequence
of better sell execution and layout efficiency in days 0–5.

**What has NOT been tested**:
- Better shed-turn frequency in first 6 hours of each day
- Intra-day fertilizer collection earlier in the season
- Optimising the day-0 seed / animal / hire split within the same budget

**Priority**: HIGH (unlocking NE one day earlier compounds crop+animal revenue significantly)

---

### GAP-NEW-002: Endgame Tile Recycling Efficiency

**Observation**: Top players run 44–57 wheat tiles by day 27 by recycling expired melon/strawberry
tiles. Current champion is improved (endgame plant promotion, wheat min-buffer 20) but may still
lag in tile turnover speed.

**What has NOT been tested**:
- `plant_cutoff` variants beyond 22
- Endgame promotion threshold earlier than day 20

---

## Prioritised Next Experiments

1. Early cash generation improvements (days 0–5 sell efficiency)
2. Endgame tile recycling tuning
3. Animal care bonus optimisation (ensure all animals are CARED every day)

---

## GAP-NEW-003: Replay-Identified Flaws — Campaign Result (2026-08-16)

**Campaign**: 9 experiments (EXP-20260815-88 through EXP-20260816-08) targeting 6 flaws
identified by deep replay analysis of 43 live champion_v2_20260815 episodes.

**Result**: 0 promotions. All 9 experiments rejected.

**Key findings from the campaign**:
- CARE reorder (`_animal_pending` FEED→HARVEST→CARE→COLLECT_FERT): Δ=-1908 — slightly
  negative at Stage 2. The CARE timing in replays is late but the ratchet confirms it
  doesn't affect game score measurably — the care bonus may accrue regardless.
- Fertilizer collect-then-apply routing: Δ=+0. The fertilizer idle seen in replays
  appears to be an observation artefact — fertilizer IS being applied but after
  hour 12 (the probe window), so h=12 snapshots show "idle" but it clears later.
- Expansion planting (T2-P/Q): Δ=-4760 / -521. Feeding animals dominates and correctly
  wins over planting on both variants. The agent already handles this correctly.
- Strawberry sell priority: Δ=+0. Unsold strawberry is shed-capacity-driven, not
  sell-order-driven.
- Day-0 place_animal ordering: Δ=+0. `_assign_tasks` distance+tier scoring already
  routes workers to nearby animals correctly.
- Early PASS probe: 72% of PASS turns are unavoidable (farm full). Only 27.4% have
  free tiles, and those are too few to move the $2k noise floor.

**Interpretation**: The replay metrics (walk%, uncared%, fert idle) measure intermediate
state at specific hours, not final score impact. The policy is already near-optimal
for the structural decisions (crew, animals, layout). The remaining gap vs top opponents
is in the opening economy (GAP-NEW-001) which requires a different campaign.
