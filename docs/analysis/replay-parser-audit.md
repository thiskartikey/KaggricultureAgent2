# Replay Parser Audit & Improvement Plan

## Summary

The original `parse_replays.py` had **6 correctness bugs** and **7 missing feature groups**
that made the extracted trajectories unsuitable for any downstream ML use.
All issues are fixed in the new version.

---

## Bugs Fixed

| # | Bug | Impact | Fix |
|---|-----|--------|-----|
| 1 | `min_score=100_000` excluded ~80% of replays | Only ~20 trajectories from 914 replays would be used | Changed default to `0` |
| 2 | `returns_to_go[t] = final_score - current_money[t]` — **wrong formula** | RTG was measuring gap-to-target, not future reward. Early steps had huge RTG even for losses. Negative when money briefly exceeded final score. | RTG is now `sum of future per-step rewards`: `RTG[t] = Σ_{s=t}^{T-1} Δmoney[s]` |
| 3 | Final reward extracted from `steps[-1][p].get("reward")` | Fragile; last step reward can be `None` or 0 on early termination | Use top-level `data["rewards"]` (always set at episode end) |
| 4 | Hardcoded path `"downloads/training"` doesn't exist | Script would crash on any machine | Default paths now point to `replays/` subdirectories |
| 5 | Only player 0 was extracted from each replay | Missing 50% of training data | Both players extracted as separate trajectories |
| 6 | No episode metadata on trajectories | Cannot trace a trajectory back to its source | Added `episode_id`, `player`, `source` fields |

---

## Feature Improvements (OBS_DIM: 107 → 145)

### New per-PLANT features (+3 per crop, +15 total)

| Feature | Why it matters |
|---------|----------------|
| `consecutive_unwatered / 3` | Urgency signal: 2+ = crop dies tomorrow |
| `fertilized_until_day >= day` | Binary: doubles strawberry/tomato yield |
| `near_death` (lifespan ≤ 48 steps) | Harvest-now vs plant-new trade-off |

### New per-PASTURE features (+3 per animal type, +9 total)

| Feature | Why it matters |
|---------|----------------|
| `uncared_today` count | CARE drives `pending_care_bonus` |
| `fertilizer_available` count | Triggers COLLECT_FERTILIZER priority |
| `pending_care_bonus / 5` | Accumulated bonus — crucial for yield prediction |

### Unit inventories (+9 total)

`private.inventories[0..n]` — items carried by farmer and all hands.  
Previously invisible: workers carrying wheat to feed animals was a blind spot.

### Tile type counts (+3 total)

`weed_count`, `free_tile_count`, `locked_tile_count` — 
free tiles drive planting decisions; weeds trigger DIG priority.

### Opponent features (+2 total)

`opp_money / 50000` and `opp_quadrant_count / 4` — basic competitive context.

---

## Feature Vector Layout (OBS_DIM = 145)

```
[0:4]    time context     (day, hour, my_money, my_quads)
[4:39]   my crops         (5 crops × 7 features)
[39:57]  my animals       (3 animal types × 6 features)
[57:59]  farmer position  (fx, fy)
[59:68]  market prices    (9 products)
[68:77]  market inventory (9 products)
[77:86]  shed products    (9 products)
[86:89]  shed animals     (3 types)
[89:94]  seeds            (5 crop types)
[94:102] shops unlocked   (8 shops, binary)
[102:111] unit inventories (9 products, total across farmer+hands)
[111:114] tile counts      (weed, free, locked)
[114:134] opp crops        (5 crops × 4 features)
[134:143] opp animals      (3 animal types × 3 features)
[143]    opp money
[144]    opp quadrants
```

---

## Returns-to-Go Semantics

**Old (wrong):**
```
RTG[t] = final_score - money[t]
```
This is the **deficit** to the final score, not future reward. It's negative if money
temporarily dips, and doesn't represent what the agent *will earn*.

**New (correct):**
```
rewards[t] = max(0, money[t] - money[t-1])   # money gained at this step
RTG[t] = sum(rewards[t:])                      # total future earnings from step t
```
RTG[0] ≈ total money earned during the game (~$55k typical).
RTG[-1] = 0 exactly (no more future reward at the last step).
RTG is guaranteed non-increasing — a prerequisite for Decision Transformer conditioning.

---

## Data Coverage (after fix)

| Metric | Before | After |
|--------|--------|-------|
| Trajectories extracted from 914 replays | ~20 (only high scorers) | **1,828** |
| Score range | 100k–183k | **1k–183k** |
| Mean score | ~120k | 86k |
| OBS_DIM | 107 | **145** |
| Missing PLANT urgency signals | ✗ | ✓ |
| Missing PASTURE care/fert signals | ✗ | ✓ |
| Missing unit inventories | ✗ | ✓ |
| Missing tile type counts | ✗ | ✓ |
| Missing opponent money | ✗ | ✓ |
| RTG formula correct | ✗ | ✓ |

---

## Usage

```bash
# Self-test (verifies shapes, invariants, RTG monotonicity on 1 file)
python3 parse_replays.py --selftest

# Parse all local replays
python3 parse_replays.py --output parsed_trajectories.pkl

# Only include high-quality trajectories (top half)
python3 parse_replays.py --min-score 80000 --output parsed_expert.pkl

# Custom directories
python3 parse_replays.py --dirs replays/champion_v2_20260815 replays/Ezzzzzekki
```
