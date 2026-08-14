# Phased Engineering Roadmap

> Phase 9 deliverable — gated milestone schedule for implementing mined strategy improvements.

---

## Pipeline Overview

```
Phase A: Telemetry & Logging
      └──► Phase B: Freeze & Benchmark Control Baseline
                 └──► Phase C: High-Confidence Parameter Tuning  ← START HERE
                            └──► Phase D: Routing & Operational Logic
                                       └──► Phase E: Market & Liquidation
                                                  └──► Phase F: Full Validation & Promotion
```

---

## Gate Definitions

| Gate | Condition | Status |
|---|---|---|
| Gate 1 | ≥300 parsed games | ✅ **PASSED** — 147,600 turns / 205 unique episodes |
| Gate 2 | Phase2_v1 baselined on 16 games | ⏳ TODO |
| Gate 3 | Each PR evaluated with `--games 8` | ⏳ Per experiment |
| Gate 4 | Promotion: p < 0.05, Δmean > 0, 16 games | ⏳ Per experiment |

---

## Phase A: Telemetry (COMPLETE)

All analysis infrastructure is in place:
- ✅ `data/processed/canonical_turns.csv` — 147,600 rows, 205 episodes
- ✅ `data/processed/dataset_inventory.csv` — full corpus inventory
- ✅ `data/processed/player_summaries.json` — per-player aggregates
- ✅ `src/replay_analysis/` — parser, schema, feature extractor, statistics, rule miner
- ✅ `docs/analysis/` — replay schema, player deep-dives, cross-player matrix, decision rules, strategy model
- ✅ `docs/architecture/` — agent audit, replay system, integration guide
- ✅ `docs/strategy/` — gap analysis, baseline description

---

## Phase B: Freeze & Benchmark Control Baseline

**Action**: Run baseline evaluation before any code changes.

```bash
python evaluate.py policy.py versions/Phase2_v1_policy.py --games 8
```

**Acceptance**: Records mean scores and t-stat for `policy.py == Phase2_v1_policy.py` (should be near 0 Δ, p≈1.0 — they are identical files at this point).

**Goal**: Establish the exact numeric baseline for all future comparisons.

---

## Phase C: High-Confidence Parameter Tuning

Apply the four highest-confidence, lowest-cost changes **one at a time**, each gated by a 16-game evaluation.

### C1: Land Unlock Day Correction (GAP-001)
```python
# policy.py
LAND_UNLOCK_DAY = (6, 10)   # was (7, 11)
```
- **Expected impact**: +3,000–6,000 points
- **Confidence**: 1.00 (n=205, zero variance)
- **Test**: `python evaluate.py policy.py versions/Phase2_v1_policy.py --games 8`
- **Gate 4 pass required before proceeding to C2**

### C2: Day 0 Opening Blueprint Correction (GAP-006)
```python
# policy.py R1 block
["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"],   # 4 hires, not 5
```
- **Expected impact**: +200–500 points
- **Confidence**: 0.75

### C3: Pasture Target Ramp to 14 Earlier (GAP-002)
```python
TARGET_PASTURE_BY_DAY = ((10, 14), (7, 9), (0, 6))
```
- **Expected impact**: +2,800–4,200 points
- **Confidence**: 0.87

### C4: TARGET_COW = 9 (GAP-005)
```python
TARGET_COW = 9   # was 8
```
- **Expected impact**: +500–1,500 points
- **Confidence**: 0.85

---

## Phase D: Routing & Operational Logic

After Phase C changes are validated and promoted:

### D1: Labour Schedule Recalibration (GAP-003)
```python
def target_hands(day, total_days):
    if day <= 0:  return 4   # was 5
    if day == 1:  return 1   # was 3
    if day < 7:   return 3
    if day < 11:  return 8
    if day >= total_days - 2: return 12
    return 13
```

### D2: Wheat Buffer Validation (GAP-004)
- Audit whether `min(need, max(0, room), 45)` cap ever blocks a necessary purchase
- Increase cap if needed

### D3: Dead DT Code Removal (GAP-007)
- Remove or fully guard the `DecisionTransformer` block
- Measure per-step execution time before and after

---

## Phase E: Market & Liquidation

### E1: Strawberry Sell Reserve Relaxation (GAP-008)
```python
"STRAWBERRY": 0.40   # was 0.50
```

### E2: Explicit Endgame Sell Ramp
- Implement a day-gated price-floor reduction schedule (see Pillar 9)

---

## Phase F: Full Validation & Promotion

- Run 16 games (`--games 8`) against Phase2_v1 baseline
- Check all Gate 4 criteria: p < 0.05, positive Δmean
- Run submission safety checklist (no prints, no ML imports, <15ms/step)
- Build and verify tarball: `python build_submission.py && tar -ztvf ml_submission.tar.gz`
- Promote to `versions/Phase2_v2_policy.py` if accepted

---

## Estimated Score Potential

| Phase | Changes | Estimated Cumulative Δ |
|---|---|---|
| C1 (land unlock) | GAP-001 | +3,000–6,000 |
| C2–C4 (opening + pastures + cows) | GAP-006, 002, 005 | +5,500–11,700 |
| D (labour + routing) | GAP-003, 004 | +7,000–14,700 |
| E (market) | GAP-008 | +7,300–15,500 |

Starting from Phase2_v1 mean ≈ **111,450** (TBD from Gate 2 benchmark).
Conservative estimated target: **118,000–126,000**.
