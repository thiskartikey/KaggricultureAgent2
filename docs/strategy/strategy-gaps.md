# Strategy Gap Analysis

> Phase 8 deliverable — audit of current `policy.py` against the 10-Pillar Strategy Model.
>
> Priority Score = (Expected Impact × Evidence Confidence) / Implementation Cost
> Cost scale: 1 = change one constant, 3 = edit one function, 5 = major refactor

---

## Summary Table

| ID | Gap | Impact (pts) | Conf | Cost | **Priority** |
|---|---|---|---|---|---|
| GAP-001 | Land unlock 1 day late (NE d7→d6, SW d11→d10) | +3,000–6,000 | 1.00 | 1 | **5000** |
| GAP-002 | Pasture target 12→14 | +2,800–4,200 | 0.87 | 1 | **3045** |
| GAP-003 | `target_hands` schedule miscalibrated | +1,500–3,000 | 0.90 | 2 | **1013** |
| GAP-004 | Wheat buffer undersize | +800–2,000 | 0.90 | 1 | **1350** |
| GAP-005 | TARGET_COW 8→9 | +500–1,500 | 0.85 | 1 | **850** |
| GAP-006 | Day 0 opening: 5 HIRE → 4 HIRE | +200–500 | 0.75 | 1 | **263** |
| GAP-007 | Dead DT/RL code adds latency risk | 0 (safety) | 1.00 | 2 | cleanup |
| GAP-008 | Sell-batch size for strawberry too conservative | +300–800 | 0.70 | 2 | **193** |
| GAP-009 | Melon cutoff not enforced (no explicit stop day) | +200–600 | 0.85 | 2 | **170** |
| GAP-010 | CASH_FLOOR 350 — may block necessary hires | +0 (safety) | 0.80 | 2 | review |

---

## GAP-001: Land Unlock Schedule Off by 1 Day

**Current behaviour** (`policy.py` line 540):
```python
LAND_UNLOCK_DAY = (7, 11)   # NE on day 7, SW on day 11
```

**Observed behaviour** (n=205, 100% consistency):
- NE unlocked on **day 6** in all 205 winning episodes
- SW unlocked on **day 10** in all 205 winning episodes

**Delta**: Each unlocked day earlier = 24 extra turns × 25 tiles. One earlier NE unlock = 24 turns × 25 tiles ≈ compounded strawberry/melon/pasture revenue.

**Fix**:
```python
LAND_UNLOCK_DAY = (6, 10)   # ← change from (7, 11)
```

**Files**: `policy.py` line ~147
**Confidence**: 1.00 (n=205, zero variance, p<0.0001)
**Expected Score Impact**: +3,000 to +6,000 (compounded crop + animal revenue over extra days)

---

## GAP-002: Pasture Target Capped at 12 (Should Be 14)

**Current behaviour** (`policy.py`):
```python
TARGET_PASTURE_BY_DAY = ((11, 14), (7, 12), (0, 6))
```
This correctly targets 14 from day 11 — but the midgame ramp only goes to 12 at day 7.

**Observed behaviour**: HealthStone and ThunderThunder (the two highest win-rate players) reach 13–14 pastures between day 10–11, with build starting earlier (day 7–8 instead of day 11).

**Actual needed change**: The `(7, 12)` entry means only 12 are targeted days 7–10. Change to ramp to 14 earlier:
```python
TARGET_PASTURE_BY_DAY = ((10, 14), (7, 9), (0, 6))
```

**Expected Score Impact**: +2 pastures × 1 fertilizer/day × 100 base × 12 days + milk/wool over 15 days ≈ +2,800 to +4,200.
**Confidence**: 0.87 (correlational — high-win-rate players have this; not a controlled experiment yet)

---

## GAP-003: `target_hands` Schedule Miscalibrated

**Current behaviour** (`policy.py`):
```python
def target_hands(day, total_days):
    if day <= 0: return 5      # too many on day 0
    if day < 7:  return 3
    if day < 11: return 8
    if day >= total_days - 2: return 10
    return 13
```

**Observed behaviour**:
- Day 0: 4 hands (not 5) — all 4 players
- Day 1: 0–1 hands (HealthStone: 0, others: 1) — current returns 3, over-hires
- Days 7–10: 7–9 hands — current returns 8, close but slightly high
- Day 20+: 12–14 hands — current returns 13, approximately correct

**Fix**:
```python
def target_hands(day, total_days):
    if day <= 0:  return 4
    if day == 1:  return 1      # save cost on lightest workday
    if day < 7:   return 3
    if day < 11:  return 8
    if day >= total_days - 2: return 12
    return 13
```

**Expected Score Impact**: +1,500 to +3,000 (compounded over 29 days of slightly better labour allocation)

---

## GAP-004: Wheat Buffer Too Tight

**Current behaviour** (`policy.py` R5):
```python
need = fed_animals * 3 - have   # targets 3-day buffer
```
But in practice, with market order slot competition, the actual wheat in shed is often well below `animals × 3`. HealthStone (highest win rate) maintains `shed.WHEAT ≈ 22–24` with 14 animals = 1.7-day buffer. Others run 6–13 with 12 animals.

**Fix**: The target formula is fine at 3 days, but the `min(need, max(0, room), 45)` cap of 45 may be blocking purchases. Ensure wheat can be bought in larger batches when shed has room.

**Expected Score Impact**: +800 to +2,000 (fewer escaped animals)

---

## GAP-005: TARGET_COW Should Be 9

**Current**: `TARGET_COW = 8`
**Observed**: HealthStone 8.98 cows, ThunderThunder 8.68 cows — both consistently closer to 9.
**Fix**: `TARGET_COW = 9` (also requires `TARGET_PASTURE = 14` to have the space)
**Expected Score Impact**: +500 to +1,500 (1 extra cow × milk + fertilizer over 15 days)

---

## GAP-006: Day 0 Opening Hires 5 Instead of 4

**Current** (`policy.py` R1):
```python
["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"],   # 5 hires
```
**Observed**: All 4 players issue exactly 4 hires on day 0. The 5th hire costs `fib(4) = 5` and on day 0 with only 25 NW tiles and 5 animals to place, the 5th worker has nothing productive to do.

**Fix**: Remove one `["HIRE"]` from the day-0 hard-coded block.
**Expected Score Impact**: +200 to +500 (5 coins saved, but also correct behaviour)

---

## GAP-007: Dead DecisionTransformer Code

**Current**: ~400 lines of `DecisionTransformer`, `obs_to_vec`, `macro_to_farmer_op` etc. are executed every turn (module-level globals, history appended, DT query attempted) but always produce no effect since `rl_weights.npz` is absent.

**Risk**: Minor latency overhead; `import numpy as np` inside the agent function every turn; history arrays grow unbounded over 720 turns.

**Fix**: Guard the DT block with an early `if DT_MODEL is not None:` before any array allocations, or remove the dead code entirely.

---

## GAP-008: Strawberry Sell Reserve Too Conservative

**Current** (`_RESERVE_FRAC`): `"STRAWBERRY": 0.50` → sells only when price ≥ 60 (50% of 120 base).

**Observed**: Top players sell in batches of 13–15 units per order consistently. The current logic may under-sell when prices are high (e.g. day 10–20 prices: 178–203) out of excessive caution.

**Fix**: Raise `"STRAWBERRY": 0.50` to `0.40` (allow selling down to 48, which is still above the $1 floor).

---

## GAP-009: No Explicit Melon Planting Cutoff

**Current**: Melon is blocked when `days_left < 13` in `_plant_choice`. This is correct (day 17 = 13 remaining days). Already implemented properly.

**Status**: ✅ Already correct — no change needed.

---

## Prioritised Implementation Order

1. **GAP-001** — `LAND_UNLOCK_DAY = (6, 10)` — 1-line change, highest confidence
2. **GAP-002** — `TARGET_PASTURE_BY_DAY` ramp earlier — 1-line change
3. **GAP-003** — recalibrate `target_hands` — 5-line change
4. **GAP-004** — validate wheat buffer adequacy in practice — review + tune
5. **GAP-005** — `TARGET_COW = 9` — 1-line change
6. **GAP-006** — Day 0 blueprint 5→4 hires — 1-line change
7. **GAP-007** — Guard or remove dead DT code — cleanup
