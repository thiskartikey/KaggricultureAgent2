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

---

## EXP-20260815-07: Endgame Wheat Buffer Taper (Phase2_v7)

- **Hypothesis**: The `feed_hold` function reserves up to 42 units of wheat (14 animals × 3-day buffer) at game end, including day 29 when animals no longer need feeding. Tapering the buffer to 0 on the final day will release 20–30 wheat units for sale, worth ~$700/game.
- **Baseline**: `versions/Phase2_v6_policy.py` (Mean: ~65,641 vs v1)
- **Mutation**: `policy.py` line 524 — compute `effective_buffer = max(0, min(3, days_left - 1))` and pass to `feed_hold()`
- **Evidence**: Replay analysis (n=50 gytdrop games): WHEAT unsold at game end in 39/50 games, avg 27.7 units (~$693 lost/game)
- **Test Protocol**: 16 seeds × 2 seats = 32 games
- **Results (vs Phase2_v6)**:
  - Policy Mean: 67,508 | Baseline Mean: 65,656 | ΔMean: +1,853
  - Paired t-stat: +3.84, p=0.000 — SIGNIFICANT
  - Win Rate: 24/32 (75%)
- **Results (vs Phase2_v1)**:
  - Policy Mean: 74,864 | Baseline Mean: 65,945 | ΔMean: +8,919
  - Paired t-stat: +8.18, p=0.000 — SIGNIFICANT
  - Win Rate: 31/32 (97%)
- **Verdict**: ACCEPTED — promoted to `versions/Phase2_v7_policy.py`

---

## EXP-20260815-08: Day-0 Opening: 8 MELON + 3 STRAW + 7 WHEAT (no wheat product)
- **Hypothesis**: Plant 3 strawberry on day 0 instead of buying wheat product, to get first straw yield on day 10 (vs day 14).
- **Baseline**: `versions/Phase2_v7_policy.py`
- **Results**: p=0.000, Δ=-5,187, wins 1/16 — CATASTROPHIC
- **Verdict**: REJECTED. No wheat product buy means animals starve early.

---

## EXP-20260815-09: Wheat Feed Buffer 3→2 Days (Phase2_v8)
- **Hypothesis**: Reducing `effective_buffer` from 3 to 2 days frees ~14 wheat units/turn for
  sale in mid-game, since 2 days of feed is sufficient (animals escape only on 2nd consecutive
  unfed day; R5 re-buys proactively).
- **Baseline**: `versions/Phase2_v7_policy.py`
- **Evidence**: Replay analysis: shed holds ~44 wheat on days 10-25; with 3-day buffer (42 units
  held), only 2 units sellable per turn. With 2-day buffer (28 held), 16 units sellable.
- **Test Protocol**: 16 seeds × 2 seats = 32 games
- **Results (vs Phase2_v7)**:
  - Policy Mean: 70,281 | Baseline Mean: 68,835 | ΔMean: +1,446
  - Paired t-stat: +5.08, p=0.000 — SIGNIFICANT
  - Win Rate: 25/32 (78%)
- **Results (vs Phase2_v1)**:
  - Policy Mean: 68,294 | Baseline Mean: 57,984 | ΔMean: +10,310
  - Paired t-stat: +10.47, p=0.000 — SIGNIFICANT
  - Win Rate: 31/32 (97%)
- **Verdict**: ACCEPTED — promoted to `versions/Phase2_v8_policy.py`

---

## EXP-20260815-10: R5 Wheat Buy Target 3→2 Days
- **Hypothesis**: Reduce wheat buy target to 2-day supply to free more wheat for selling.
- **Baseline**: `versions/Phase2_v8_policy.py`
- **Results**: p=0.000, Δ=-7,426, wins 1/16 — CATASTROPHIC
- **Verdict**: REJECTED. Animals starve when buy target too low.

---

## EXP-20260815-11: Plant Cutoff Extended to Hour 22 for All Days
- **Baseline**: `versions/Phase2_v8_policy.py`
- **Results**: p=0.992, Δ+11 — NOISE
- **Verdict**: REJECTED.

---

## EXP-20260815-12: Shed Squeeze Thresholds 85/65→75/50 (Phase2_v9)
- **Hypothesis**: Lowering squeeze thresholds (from 85/65 to 75/50) triggers partial-reserve
  selling earlier, when shed has ≥50 items instead of waiting for ≥65.
- **Evidence**: 94% of sell turns have shed < 65 items (always full reserve). Lowering to 50
  reduces full-reserve turns significantly.
- **Test Protocol**: 16 seeds × 2 seats = 32 games
- **Results (vs Phase2_v8)**:
  - Policy Mean: 71,253 | Baseline Mean: 69,193 | ΔMean: +2,061
  - Paired t-stat: +4.69, p=0.000 — SIGNIFICANT
  - Win Rate: 27/32 (84%)
- **Results (vs Phase2_v1)**:
  - Policy Mean: 69,850 | Baseline Mean: 56,726 | ΔMean: +13,124
  - Paired t-stat: +10.92, p=0.000 — SIGNIFICANT
  - Win Rate: 32/32 (100%)
- **Verdict**: ACCEPTED — promoted to `versions/Phase2_v9_policy.py`

---

## EXP-20260815-13: Shed Squeeze 85/65→75/50 (Phase2_v9) — Squeeze=0.45/1.0
Already logged above.

## EXP-20260815-14: Reserve Price Mechanism Removal (Phase2_v10)

Iterative squeeze sweep vs Phase2_v9:
| squeeze (sparse shed) | Δ | wins/16 | p |
|---|---|---|---|
| 0.7 | +1,259 | 14/16 | 0.000 |
| 0.5 | +1,867 | 15/16 | 0.000 |
| 0.3 | +2,778 | 13/16 | 0.000 |
| 0.0 | +3,586 | 15/16 | 0.000 |

Final: plan_sells simplified to sell-all with no price reserve:
- **Results vs Phase2_v9 (32 games)**: Δ+3,457, 30/32 wins, p=0.000
- **Results vs Phase2_v1 (32 games)**: Δ+15,823, 32/32 wins, p=0.000
- **Verdict**: ACCEPTED — promoted to `versions/Phase2_v10_policy.py`
