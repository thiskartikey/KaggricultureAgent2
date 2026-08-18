# Kaggriculture Agent — Resume Checkpoint

> **Updated**: 2026-08-16 (Master Codebase Audit & Infrastructure Rebuild: 5 Subsystems Defined, Evaluation Harness Repaired, Opponent Pool Benchmark Verified at 88,662 Mean, 87.5% WR, Subagent Runbooks & Research Docs Created)
> **Status**: Champion = `EXP-20260815-69`. Autoresearch & Pool Evaluator fully operational. 105/105 tests pass.

---

## 0. Repository Architecture (5 Subsystems)

- **Subsystem A (Policy)**: `policy.py`, `ml_main.py`
- **Subsystem B (Evaluation)**: `eval_seeds.py`, `evaluate.py`, `src/autoresearch/pool_evaluator.py`
- **Subsystem C (Replay Intelligence)**: `parse_replays.py`, `src/replay_analysis/`
- **Subsystem D (Ratchet Autoresearch)**: `src/autoresearch/` (Tier 1/2/3 search space)
- **Subsystem E (Submissions & Grounding)**: `README.md`, `instructions/`, `docs/`, `build_submission.py`

---

## 1. Current Champion

| Metric | Value |
|---|---|
| Champion archive | `versions/EXP-20260815-69_policy.py` |
| Live policy | `policy.py` (identical to champion, dead code removed) |
| Pool mean score | **88,662** (87.5% overall win rate vs pool) |
| Δ vs Phase2_v1 baseline | +17,859 mean (p=0.000, Cohen's d ≈ 1.1) |
| Self-play comparison | Δ = 0, p = 1.000 (perfect match — dead code had zero effect) |
| Key improvements vs v1 | R5 wheat fix, dropoff 3/5, STRAW=35, MELON reserve removed, wheat buffer taper, fertilize tier 1, TARGET_MELON=9, LAND_UNLOCK_DAY=(7,9) composite |

---

## 2. Evaluation Tooling Status (Verified)

- `eval_seeds.py`: Dual-seat balanced, arbitrary path resolution, full statistical reporting (`python eval_seeds.py policy.py starter --seeds 10`).
- `evaluate.py`: `--debug` traceback logging, `--pool` 5-opponent tournament mode (`python evaluate.py policy.py --pool`).
- `src/autoresearch/pool_evaluator.py`: 5 historical checkpoints (`Phase2_v1`, `Phase2_v7`, `Phase2_v11`, `EXP-20260814-12`, `EXP-20260815-69`). All tested and operational.

---

## 2. Autoresearch System (KaggriRatchet)

All components in `src/autoresearch/` are fully implemented and tested:

### Stage 4 — Opponent Pool Evaluator (NEW)

`src/autoresearch/pool_evaluator.py` — addresses the self-play blind spot.
Evaluates candidate against 5 historical champion checkpoints (and any clones
in `opponent_clones/`). Reports mean_score, win_rate_overall, win_rate_vs_strong.

**Current champion pool baseline** (seeds 6000-6003, 8 games/opponent):

| Opponent | Δmean | Win rate |
|---|---|---|
| Phase2_v1_policy | +15,763 | 100% |
| Phase2_v7_policy | +11,897 | 100% (strong) |
| Phase2_v11_policy | +5,654 | 100% |
| EXP-20260814-12_policy | +42,388 | 100% |
| EXP-20260815-69_policy (self) | 0 | 38% |
| **Pool mean score** | **88,662** | **87.5% overall, 68.8% vs strong** |

Usage: `python3 -m src.autoresearch.pool_evaluator policy.py`

---

### Flaw-Fix Experiment Results (2026-08-16)

Attempted 4 changes from `docs/roadmap/flaw-fix-roadmap-plan.md`. All tested against
`EXP-20260815-69` baseline using 32 seeds (64 games).

| Change | Δmean | p | d | Verdict |
|---|---|---|---|---|
| ST-1: CARE before COLLECT_FERT in `_animal_pending` | **−1,791** | **<0.0001** | **−0.95** | ❌ REJECTED — original order is correct |
| ST-2: Fertilizer tier-boost for carrying workers | ±0 | 1.000 | 0.00 | ⚠ Self-play blind spot — no signal |
| ST-3: Endgame threshold day>=18 (was 20) | +244 | 0.42 | 0.10 | ⚠ Self-play blind spot — no signal |
| ST-6: Day-0 place_animal Tier 0 | ±0 | 1.000 | 0.00 | ⚠ Self-play blind spot — no signal |

**Key finding**: ST-2, ST-3, ST-6 improvements are invisible to self-play because both
agents benefit equally. These changes must be re-evaluated via the opponent pool
(Stage 4) once opponent clones are built. ST-1 genuinely regresses — do not retry.

---


| Module | Status |
|---|---|
| `controller.py` | Autonomous loop: `--step`, `--loop --max-exp N`, `--test-ratchet` |
| `evaluator.py` | 4-stage adaptive cascade (Stage 0 invariant → Stage 3 champion gate) |
| `mutator.py` | Tier 1/2/3 mutations + AST linter |
| `hypothesis.py` | Hypothesis generator with failure-memory deduplication |
| `memory.py` | JSONL experiment ledger (138 records: 13 KEEP, 125 REJECT) |
| `stats.py` | Paired t-test, Wilcoxon, Cohen's d, bootstrap CI |
| `telemetry.py` | Simulation telemetry extractor |

---

## 3. Test Suite

```
83 passed in 0.5s
tests/test_memory.py           16 passed
tests/test_mutator.py          18 passed
tests/test_policy_invariants.py 9 passed
tests/test_replay_parser.py    27 passed
tests/test_stats.py            13 passed
```

---

## 4. Strategy Blueprint (Champion)

| Dimension | Value |
|---|---|
| **Land** | NE day 7 ($1k), SW day 9 ($2k); SE never |
| **Labor** | 5/3/8/13/10 by phase (re-hire every morning) |
| **Animals** | 14 PASTURE (8 COW + 6 SHEEP); fed + cared daily |
| **Crops** | 35 STRAWBERRY, 9 MELON, ~7 WHEAT |
| **Market** | Sell-all every turn (no reserve). Wheat buffer = 2 days, tapers to 0 at end |
| **Fertilizer** | Applied to producing strawberries at tier-1 priority |
| **Endgame** | Plant promoted to tier 1 from day 20; wheat planting allowed until 3 days left |

---

## 5. Confirmed-Rejected Experiments (do not re-run)

| Change | Δ mean | Notes |
|---|---|---|
| `LAND_UNLOCK_DAY = (6, 10)` | −5,542 | Agent can't afford NE until day 7–8 |
| `target_hands` day 1 = 1 | −11,509 | Labour starvation |
| 4 HIRE + 1 COW + 4 SHEEP opening | −9,401 | Budget overrun |
| `TARGET_COW = 9` | −1,081 | Leaning negative |
| `TARGET_PASTURE_BY_DAY = ((10,14),(7,9),(0,6))` | −6,389 | Drops mid-game to 9 |
| Price reserve on any product | −3,457 | Sell-all always wins |
| `feed_hold` buffer = 3 days | −1,446 vs 2-day | Over-reserves wheat |
| Wheat buy target 2 days | −7,426 | Animals starve |
| `target_hands` = 14 | −4,507 | Fib cost too high |

---

## 6. Next Steps

1. **Run more KaggriRatchet campaigns** to find further improvements:
   ```bash
   python3 -m src.autoresearch.controller --loop --max-exp 10
   ```
2. **Submit current champion** to Kaggle leaderboard:
   ```bash
   python3 build_submission.py
   kaggle competitions submit kaggriculture -f ml_submission.tar.gz -m "EXP-20260815-69 champion"
   ```
3. **Quick smoke test** before any work:
   ```bash
   python3 -m pytest tests/ -q
   ```

---

## 7. Constraints to Never Break

1. **Hands wiped nightly** — always re-hire every morning.
2. **Feed routing** — only wheat-carrying workers → hungry animals.
3. **Sticky claims** — workers hold a task until it disappears.
4. **Planting day = unwatered** — sow ≤ hour 20 or crop dies tonight.
5. **Shed cap = 100** — overflow discarded at end-of-day.
6. **10 market orders/turn** — extras silently dropped.
7. **`policy.py` must pass `tests/test_policy_invariants.py`** before any evaluation.
