# Live Task Tracker

> Phase 10 deliverable — state-machine task tracker for all engineering work.
>
> States: BACKLOG → READY → IN_PROGRESS → VALIDATING → DONE / REJECTED

---

## Analysis & Infrastructure (Complete)

- [x] `TASK-INFRA-001`: Build canonical replay parser (`src/replay_analysis/parser.py`)
  - **Status**: DONE
  - **Evidence**: 147,600 turns parsed from 205 episodes, 25/25 tests passing

- [x] `TASK-INFRA-002`: Generate `data/processed/canonical_turns.csv`
  - **Status**: DONE
  - **Evidence**: 110,160 → 147,600 rows after ThunderThunder alias fix

- [x] `TASK-INFRA-003`: Author all Phase 0–12 documentation
  - **Status**: DONE
  - **Evidence**: 15 markdown files across `docs/`

---

## Phase B: Baseline Benchmarking

- [ ] `TASK-BENCH-001`: Run baseline evaluation Phase2_v1 vs Phase2_v1 (smoke test)
  - **Phase**: Phase B
  - **Reason**: Confirm evaluate.py works and establishes numeric anchor.
  - **Files**: `evaluate.py`
  - **Command**: `python evaluate.py policy.py versions/Phase2_v1_policy.py --games 2`
  - **Priority**: CRITICAL (blocks all Phase C experiments)
  - **Status**: READY

- [ ] `TASK-BENCH-002`: Full 16-game baseline benchmark
  - **Phase**: Phase B
  - **Reason**: Establish mean score for Gate 2.
  - **Command**: `python evaluate.py policy.py versions/Phase2_v1_policy.py --games 8`
  - **Acceptance**: Record exact mean and std for Phase2_v1.
  - **Status**: BACKLOG (after TASK-BENCH-001)

---

## Phase C: High-Confidence Parameter Tuning

- [ ] `TASK-STRAT-001`: Land unlock day correction (GAP-001)
  - **Phase**: Phase C1
  - **Reason**: NE d6 and SW d10 observed in 100% of 205 episodes; current policy uses d7/d11.
  - **Evidence**: `docs/analysis/cross-player-matrix.md` §2, n=205, p≈0
  - **Files**: `policy.py` line ~147 (`LAND_UNLOCK_DAY`)
  - **Change**: `LAND_UNLOCK_DAY = (6, 10)`
  - **Acceptance Criteria**: `Δmean > 0`, `p < 0.05` over 16 games vs Phase2_v1
  - **Test Command**: `python evaluate.py policy.py versions/Phase2_v1_policy.py --games 8`
  - **Priority**: HIGH (Score: 5000)
  - **Status**: READY (pending Gate 2)

- [ ] `TASK-STRAT-002`: Day 0 opening blueprint correction (GAP-006)
  - **Phase**: Phase C2
  - **Reason**: All 4 players hire 4 hands on day 0; current policy hires 5.
  - **Evidence**: `docs/analysis/decision-rules.md` RULE-OPEN-001, n=205
  - **Files**: `policy.py` R1 block (~line 508)
  - **Change**: Remove one `["HIRE"]` from day-0 hard-coded block
  - **Priority**: MEDIUM (Score: 263)
  - **Status**: BACKLOG

- [ ] `TASK-STRAT-003`: Pasture target ramp to 14 by day 10 (GAP-002)
  - **Phase**: Phase C3
  - **Reason**: HealthStone/ThunderThunder (91.7%/96.2% win rate) reach 14 pastures by day 10–11.
  - **Evidence**: `docs/analysis/cross-player-matrix.md` §5, n=113
  - **Files**: `policy.py` line ~140 (`TARGET_PASTURE_BY_DAY`)
  - **Change**: `TARGET_PASTURE_BY_DAY = ((10, 14), (7, 9), (0, 6))`
  - **Priority**: HIGH (Score: 3045)
  - **Status**: BACKLOG

- [ ] `TASK-STRAT-004`: TARGET_COW = 9 (GAP-005)
  - **Phase**: Phase C4
  - **Reason**: HealthStone 8.98, ThunderThunder 8.68 cows at day 15.
  - **Evidence**: `docs/analysis/cross-player-matrix.md` §6, n=113
  - **Files**: `policy.py` line ~143 (`TARGET_COW`)
  - **Change**: `TARGET_COW = 9`
  - **Priority**: MEDIUM (Score: 850)
  - **Status**: BACKLOG

---

## Phase D: Routing & Operational Logic

- [ ] `TASK-STRAT-005`: Labour schedule recalibration (GAP-003)
  - **Phase**: Phase D1
  - **Files**: `policy.py` `target_hands()` function (~line 165)
  - **Priority**: MEDIUM (Score: 1013)
  - **Status**: BACKLOG

- [ ] `TASK-STRAT-006`: Wheat buffer audit and fix (GAP-004)
  - **Phase**: Phase D2
  - **Files**: `policy.py` R5 block (~line 546)
  - **Priority**: MEDIUM (Score: 1350)
  - **Status**: BACKLOG

- [ ] `TASK-STRAT-007`: Remove dead DT/RL code (GAP-007)
  - **Phase**: Phase D3
  - **Files**: `policy.py` lines ~870–1286
  - **Priority**: LOW (safety/cleanup)
  - **Status**: BACKLOG

---

## Phase E: Market & Liquidation

- [ ] `TASK-STRAT-008`: Strawberry sell reserve relaxation (GAP-008)
  - **Phase**: Phase E1
  - **Files**: `policy.py` `_RESERVE_FRAC` dict (~line 193)
  - **Priority**: LOW (Score: 193)
  - **Status**: BACKLOG

---

## Phase F: Final Validation

- [ ] `TASK-FINAL-001`: 16-game validation of promoted policy vs Phase2_v1
  - **Phase**: Phase F
  - **Command**: `python evaluate.py policy.py versions/Phase2_v1_policy.py --games 8`
  - **Status**: BACKLOG

- [ ] `TASK-FINAL-002`: Submission safety checklist
  - **Phase**: Phase F
  - **Checks**: no prints, no ML imports, <15ms/step, tarball builds cleanly
  - **Status**: BACKLOG

- [ ] `TASK-FINAL-003`: Submit to Kaggle leaderboard
  - **Phase**: Phase F
  - **Command**: `python build_submission.py && kaggle competitions submit kaggriculture -f ml_submission.tar.gz -m "Phase2_v2"`
  - **Status**: BACKLOG
