# Live Task Tracker

> Last updated: 2026-08-15 (post KaggriRatchet campaigns + health-check cleanup)

---

## Infrastructure (Complete)

- [x] `TASK-INFRA-001`: Canonical replay parser (`src/replay_analysis/parser.py`) — 147,600 turns, 27/27 tests
- [x] `TASK-INFRA-002`: `data/processed/canonical_turns.csv` — 147,600 rows
- [x] `TASK-INFRA-003`: All Phase 0–12 documentation
- [x] `TASK-INFRA-004`: KaggriRatchet autoresearch system (`src/autoresearch/`) — all modules built, 83/83 tests

---

## Strategy Optimization (Complete via KaggriRatchet)

- [x] `TASK-STRAT-001`: Land unlock schedule — SW day 9 via composite mutation (GAP-001 resolved)
- [x] `TASK-STRAT-002`: Day 0 opening — tested, **5 hires is correct** (4 hires = −7,280)
- [x] `TASK-STRAT-003`: Pasture ramp — tested, **current `((11,14),(7,12))` is optimal** (earlier ramp = −6,389)
- [x] `TASK-STRAT-004`: `TARGET_COW` — tested, **8 is optimal** (9 = −1,081)
- [x] `TASK-STRAT-005`: Labour schedule — validated; current schedule is optimal vs all tested variants
- [x] `TASK-STRAT-006`: Wheat buffer — fixed to 2-day tapering (+1,446 vs 3-day)
- [x] `TASK-STRAT-007`: Dead DT/RL code — **removed** in health-check cleanup (880 lines, zero dead code)
- [x] `TASK-STRAT-008`: Sell reserve — **removed entirely** (sell-all +3,457 vs reserve)
- [x] `TASK-STRAT-009`: Dropoff thresholds — 10/6 → 5/3 (+5,707)
- [x] `TASK-STRAT-010`: Fertilize tier 2 → 1 (+2,036)
- [x] `TASK-STRAT-011`: Endgame wheat logic — plant cutoff h22, buffer 20/60, plant tier 1 from day 20

---

## Open / Next

- [ ] `TASK-NEXT-001`: Early cash generation (days 0–5) — see GAP-NEW-001 in `docs/strategy/strategy-gaps.md`
  - **Status**: BACKLOG
  - **Approach**: Run KaggriRatchet with telemetry targeting hours 0–6 on days 1–5
  
- [ ] `TASK-NEXT-002`: Submit champion `EXP-20260815-69` to Kaggle leaderboard
  - **Command**: `python3 build_submission.py && kaggle competitions submit kaggriculture -f ml_submission.tar.gz -m "EXP-20260815-69"`
  - **Status**: READY

---

## How to Run the Next Experiment

```bash
# Automated (preferred)
python3 -m src.autoresearch.controller --loop --max-exp 10

# Manual comparison vs champion
python3 - << 'EOF'
from src.autoresearch.evaluator import _run_games
from src.autoresearch.stats import full_stats
c, b, f = _run_games('policy.py', 'versions/EXP-20260815-69_policy.py', list(range(4000, 4016)), 6)
s = full_stats(c, b)
print(f"Δmean={s['delta_mean']:+,.0f}  p_t={s['p_ttest']:.4f}  d={s['cohens_d']:.3f}  failed={f}")
EOF
```
