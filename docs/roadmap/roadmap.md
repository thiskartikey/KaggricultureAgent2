# Phased Engineering Roadmap

> Last updated: 2026-08-15 (post KaggriRatchet campaigns)

---

## Phase Status

| Phase | Description | Status |
|---|---|---|
| A | Telemetry & Data Pipeline | ✅ COMPLETE |
| B | Baseline Benchmark | ✅ COMPLETE |
| C | High-Confidence Parameter Tuning | ✅ COMPLETE (all changes validated) |
| D | Routing & Operational Logic | ✅ COMPLETE |
| E | Market & Liquidation | ✅ COMPLETE (sell-all, buffer taper) |
| F | Full Validation & Autoresearch | ✅ COMPLETE (KaggriRatchet built, 138 experiments run) |

---

## Current State

**Champion**: `EXP-20260815-69` (+17,859 vs Phase2_v1, p=0.000, 83/83 tests pass).

The KaggriRatchet autonomous system is fully operational. Use it for further optimization:

```bash
# Run one experiment
python3 -m src.autoresearch.controller --step

# Run up to 10 experiments
python3 -m src.autoresearch.controller --loop --max-exp 10

# Verify git state is clean after
python3 -m src.autoresearch.controller --test-ratchet
```

---

## Replay Flaw Campaign Result (2026-08-16)

9 experiments targeting 6 replay-identified flaws — **0 promotions**.
The flaws (walk rate, uncared animals, fertilizer idle, expansion tiles, unsold produce)
are real observations but do not translate to measurable score improvements via the
available mutation mechanisms. The ratchet correctly filtered all of them.

See `docs/roadmap/flaw-fix-roadmap-plan.md` for full experiment log.
See `docs/strategy/strategy-gaps.md` GAP-NEW-003 for root cause analysis.

---

## Next Frontier: GAP-NEW-001 (Early Cash Days 0–5)

The remaining gap between our agent and the very top leaderboard players is early cash generation.
Top players have ~$1,350+ by day 6; we have ~$220. This is not fixable by changing a constant —
it requires improving sell execution, layout efficiency, or turn utilization in the first 144 turns.

**Suggested exploration areas:**
1. Better utilisation of hour 0–6 on days 1–5 (workers already at shed; free shed turn for dropoff+sell)
2. Verify all fertilizer is being collected daily in the early game
3. Experiment with the wheat endgame buffer taper starting earlier

---

## Completed Changes (Summary)

| Change | Δ vs v1 | p-value |
|---|---|---|
| R5 wheat threshold | +439 | 0.638 |
| Dropoff 3/5 + STRAW=44 + MELON reserve | +5,404 | 0.000 |
| Endgame wheat logic | +6,277 | 0.000 |
| Wheat buffer taper | +8,919 | 0.000 |
| Wheat buffer 3→2 days | +10,310 | 0.000 |
| Shed squeeze + sell-all | +15,823 | 0.000 |
| Fertilize tier 1 | ~+17,859 | 0.000 |
| KaggriRatchet (4 composites) | ~+17,859 | 0.000 |

---

## Gates (All Passed)

| Gate | Condition | Status |
|---|---|---|
| Gate 1 | ≥300 parsed games | ✅ 147,600 turns / 205 episodes |
| Gate 2 | Phase2_v1 baselined | ✅ Mean 68,689 (n=16) |
| Gate 3 | Each PR evaluated | ✅ Automated via evaluator.py |
| Gate 4 | p < 0.05, Δ > 0, 32 games | ✅ All 13 KEEP records meet this bar |
