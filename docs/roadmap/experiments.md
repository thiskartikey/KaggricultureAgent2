# Experiment Log

> Phase 11 deliverable — formal A/B experiment records with hypotheses, results, and verdicts.
>
> Format follows the scientific experiment template from `instructions/replay_intelligence.md`.

---

## EXP-20260814-01: Wheat Buy Batching Fix (R5 oscillation bug)
- **Hypothesis**: Fixing the R5 `need >= fed_animals` threshold (was `need > 0`) will free 4–6 market order slots per day currently wasted on single-unit wheat top-ups, allowing SELL orders to fire and generate earlier cash for land unlocks.
- **Baseline**: `versions/Phase2_v1_policy.py` (Mean: 67,432 in this run)
- **Mutation**: `policy.py` R5 block — `need > 0` → `need >= fed_animals`
- **Test Protocol**: 16 seeds × 2 seats = 32 games
- **Results**:
  - Policy Mean: 67,871 | Baseline Mean: 67,432 | ΔMean: +439
  - Paired t-stat: +0.47, p=0.638 — NOISE in self-play
  - Win Rate: 16/32 (50%)
- **Verdict**: ACCEPTED (no regression; structurally correct). Self-play variance masks the benefit. Real gains expected on leaderboard where freed slots enable SELL orders against real opponents.
- **Evidence**: Wheat buy orders days 0–9 dropped from ~35 to 13. Batch sizes increased from 1 to 4–11.

---

## Gate 2 Benchmark (2026-08-13)

**Phase2_v1 baseline established**:
- `python evaluate.py policy.py versions/Phase2_v1_policy.py --games 8` (policy == baseline)
- **Mean**: 68,689 | **Median**: 66,538 | n=16 games (8 seeds × 2 seats)
- Note: Phase2_v1 and current policy.py are identical, so Δ=0 as expected.

---

## Completed Experiments

### EXP-20260813-01: Land Unlock Day Correction (GAP-001) — CLOSED / ROOT CAUSE FOUND
- **Hypothesis**: Correcting land unlock to NE day 6 / SW day 10 will increase mean score.
- **Baseline**: `versions/Phase2_v1_policy.py`
- **Mutation**: `LAND_UNLOCK_DAY = (6, 10)`
- **Test Protocol (final)**: 16 seeds × 2 seats = 32 games
- **Results**:
  - Policy Mean: 69,251 | Baseline Mean: 69,693 | ΔMean: -441
  - Paired t-stat: -0.55, p=0.582 — NOISE
  - Win Rate: 11/32 (8 ties)
- **Verdict**: REJECTED (confirmed no-op / marginally negative).
- **Root Cause (confirmed by instrumentation)**: The NE unlock at day 6 **never fires** — money at day 6 hour 0 is only ~$220, far below the $1,350 threshold (`LAND_UNLOCK_DAY[0]` cost + `CASH_FLOOR`). The constant change was a no-op for NE. The only real effect was SW unlocking at day 10 instead of day 11 with only ~$379–663 in cash, which hurt liquidity during the critical crop-planting window.
- **Key Insight**: Top players unlock NE on day 6 because they generate ~$1,350 by then — a consequence of **better early cash efficiency**, not a configurable constant. To unlock NE on day 6 our agent must earn more in days 0–5, which requires fixing the early-game revenue generation (routing, watering, seed coverage) rather than adjusting the unlock threshold.
- **GAP-001 revised**: The unlock *day* is not the lever. The lever is **early cash generation (days 0–5)**. This is a deeper fix belonging in Phase D/E, not Phase C.

### EXP-20260813-02: Opening Blueprint Change (GAP-006) — REJECTED
- **Hypothesis**: Changing day-0 from 5 HIRE + 2 COW + 2 SHEEP to 4 HIRE + 1 COW + 4 SHEEP would match top-player opening.
- **Results**: -12,693 mean vs baseline (p=0.000). LARGE REGRESSION.
- **Verdict**: REJECTED.
- **Root Cause**: 4 SHEEP at 500 each = 2,000. This consumes almost all opening budget, leaving only ~593 for seeds. The original `2 COW + 2 SHEEP` (1,800 total) buys 11 melon seeds (880) + 7 wheat seeds (70) for strong day-0 crop coverage. The observed top-player replay opening `1 COW + 4 SHEEP + 5 melon + 5 wheat + 5 feed` is budget-correct for day 0 but the reduced melon seed count (-6 tiles) costs too much midgame revenue.
- **Learning**: The replays show `1 COW + 4 SHEEP` with smaller seed purchases because they continue buying seeds in subsequent turns. The hard-coded R1 block needs to account for the multi-turn buying pattern, not just replicate the single-turn action.

### EXP-20260813-03: target_hands Day-1 Reduction — REJECTED
- **Hypothesis**: Reducing day-1 hands to 1 (matching HealthStone's observed 0 hands on day 1) saves cost.
- **Results**: -11,509 mean vs baseline. LARGE REGRESSION.
- **Verdict**: REJECTED.
- **Root Cause**: Day 1 with only 3 hands (original policy) already runs lean; reducing to 1 starves the farm of labour needed to water new plants and tend livestock.

---

## Pending Experiments (Queued)

### EXP-TBD-04: Combined Land Unlock + More Games
- **Hypothesis**: `LAND_UNLOCK_DAY = (6, 10)` with 32+ games will show significant positive Δ.
- **Mutation**: `LAND_UNLOCK_DAY = (6, 10)`
- **Status**: QUEUED — needs more game budget to detect small effects

### EXP-TBD-05: Pasture Ramp to 14 Earlier (GAP-002)
- **Mutation**: `TARGET_PASTURE_BY_DAY = ((10, 14), (7, 9), (0, 6))`
- **Status**: QUEUED

---

## Template

```markdown
## EXP-YYYYMMDD-NN: Short Description
- **Hypothesis**: ...expected improvement and magnitude...
- **Baseline**: `versions/Phase2_vN_policy.py` (Mean: XXX)
- **Mutation Diff**: Modified `function_name` in `policy.py` lines X–Y.
- **Test Protocol**: 8 seeds × 2 seats = 16 games head-to-head.
- **Command**: `python evaluate.py policy.py versions/Phase2_vN_policy.py --games 8`
- **Results**:
  - Policy Mean: XXX
  - Baseline Mean: YYY
  - ΔMean: +ZZZ
  - Paired t-stat: T.TT, p-value: 0.XXXX (p < 0.05 ✓/✗)
  - Win Rate: W/16 (WW%)
- **Verdict**: ACCEPT / REJECT
- **Notes**: ...
```
