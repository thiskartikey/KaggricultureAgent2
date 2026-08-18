# Decision Rule Catalog

> Phase 6 deliverable — empirically-grounded IF-THEN production rules extracted from 205 episodes across 4 top players.

---

### RULE-LAND-001: NE Quadrant Unlock on Day 6

- **ID**: `RULE-LAND-001`
- **Category**: Land Expansion
- **Condition**:
  - `game.day == 6`
  - `farm.unlocked_quadrants == ["NW"]` (only 1 quad)
  - `farm.money >= 1350` (1000 cost + 350 cash floor)
- **Action**: Issue `["BUY_LAND"]`
- **Empirical Evidence**: Observed in **100%** of all 205 winning episodes across all 4 players. Zero variance in unlock day. n=205, p≈0.
- **Confidence**: 100%
- **Implementation Complexity**: Low — `LAND_UNLOCK_DAY = (7, 9)` in current champion. Note: changing NE from day 7 to 6 is a confirmed no-op (−5,542) — agent can't afford the $1k unlock until day 7–8 regardless. SW moving to day 9 was accepted as part of a composite mutation.
- **Expected Score Impact**: Unlocking one day earlier = 24 extra turns on 25 additional tiles. Compounds all downstream farming.

---

### RULE-LAND-002: SW Quadrant Unlock on Day 10

- **ID**: `RULE-LAND-002`
- **Category**: Land Expansion
- **Condition**:
  - `game.day == 10`
  - `farm.unlocked_quadrants == ["NW", "NE"]`
  - `farm.money >= 2350`
- **Action**: Issue `["BUY_LAND"]`
- **Empirical Evidence**: 100% of 205 episodes. Zero variance. n=205, p≈0.
- **Confidence**: 100%
- **Implementation Complexity**: Low — same as RULE-LAND-001, change `LAND_UNLOCK_DAY[1]` from 11 to 10.
- **Expected Score Impact**: One full day earlier = 24 more turns on 50 tiles. Compounds livestock/strawberry revenue.

---

### RULE-LAND-003: SE Quadrant Never Purchased

- **ID**: `RULE-LAND-003`
- **Category**: Land Expansion
- **Condition**: Always
- **Action**: Never issue `["BUY_LAND"]` when already at 3 quadrants
- **Empirical Evidence**: 0/205 episodes purchase SE. Cost is 4,000 on day ~14+; remaining season is too short to amortise. n=205.
- **Confidence**: 100%
- **Implementation Complexity**: Low — already enforced in current `policy.py`.

---

### RULE-OPEN-001: Day 0 Opening Blueprint

- **ID**: `RULE-OPEN-001`
- **Category**: Opening
- **Condition**: `game.day == 0 AND game.hour == 0`
- **Action** (Ezzzzzekki/GiovanniCR/ThunderThunder variant — 75% of corpus):
  ```
  HIRE × 4
  BUY_ANIMAL COW 1
  BUY_ANIMAL SHEEP 4
  BUY_SEED MELON
  BUY_SEED WHEAT
  BUY_PRODUCT WHEAT (feed reserve)
  ```
- **Alternative Action** (HealthStone variant — 29% / highest win rate):
  ```
  HIRE × 3
  BUY_ANIMAL COW 1
  BUY_ANIMAL SHEEP 4
  BUY_SEED MELON (more seeds)
  BUY_SEED WHEAT
  (NO feed purchase — buy wheat later)
  ```
- **Empirical Evidence**: 100% of 205 episodes follow one of these two exact blueprints. n=205.
- **Confidence**: 100%
- **Implementation Complexity**: Low — current `policy.py` R1 uses 5 HIRE which differs from both. Needs correction.

---

### RULE-PASTURE-001: 6 Pastures by Day 5

- **ID**: `RULE-PASTURE-001`
- **Category**: Infrastructure / Livestock
- **Condition**: `game.day <= 5 AND farm.pasture_count < 6 AND free_tiles > 0`
- **Action**: Build pasture on nearest-shed free tile
- **Empirical Evidence**: All 4 players have exactly 6 pastures by day 5. n=205, 100%.
- **Confidence**: 100%
- **Implementation Complexity**: Low — `target_pastures` function already handles this.

---

### RULE-PASTURE-002: 14 Pastures by Day 11

- **ID**: `RULE-PASTURE-002`
- **Category**: Infrastructure / Livestock
- **Condition**: `game.day >= 10 AND farm.pasture_count < 14 AND free_tiles > 0 AND game.day < 22`
- **Action**: Build pasture on nearest-shed free tile
- **Empirical Evidence**: HealthStone (n=60, 91.7% win rate) and ThunderThunder (n=53, 96.2%) both reach 14 pastures by day 11. Ezzzzzekki/GiovanniCR cap at 12. The +2 pasture players have **+4.7–9.8% higher win rates**.
- **Confidence**: 85% (correlational — both high-win-rate players share this trait)
- **Implementation Complexity**: Low — change `TARGET_PASTURE_BY_DAY = ((11, 14), (7, 12), (0, 6))` → `((10, 14), (7, 9), (0, 6))`.
- **Expected Score Impact**: +2 animals × ~700 fertilizer value + milk/wool over 18 days ≈ +2,800 to +4,200.

---

### RULE-LIVESTOCK-001: Target 8–9 Cows

- **ID**: `RULE-LIVESTOCK-001`
- **Category**: Livestock / Husbandry
- **Condition**: `farm.cow_count < 9 AND empty_pastures > 0 AND money >= 400 + CASH_FLOOR AND day < 22`
- **Action**: `BUY_ANIMAL COW 1` (fill empty pastures)
- **Empirical Evidence**: All 4 players target 8+ cows. HealthStone/ThunderThunder average 8.98/8.68 (closer to 9). GiovanniCR exactly 8.00 with zero variance. n=205.
- **Confidence**: 95%
- **Implementation Complexity**: Low — change `TARGET_COW = 8` to `TARGET_COW = 9`.

---

### RULE-LIVESTOCK-002: Target 5–6 Sheep

- **ID**: `RULE-LIVESTOCK-002`
- **Category**: Livestock / Husbandry
- **Condition**: `farm.sheep_count < 5 AND cow_count >= 8 AND empty_pastures > 0 AND money >= 500 + CASH_FLOOR`
- **Action**: `BUY_ANIMAL SHEEP 1`
- **Empirical Evidence**: HealthStone 5.02 ± 1.33, ThunderThunder 5.25 ± 2.00 (both high-win-rate). Ezzzzzekki/GiovanniCR average 4.32/4.00. Higher sheep count → more wool revenue + more fertilizer. n=205.
- **Confidence**: 80%
- **Implementation Complexity**: Low — change `TARGET_SHEEP = 6` to `TARGET_SHEEP = 5` (more achievable given 14 pastures and 9 cows).

---

### RULE-LIVESTOCK-003: No Goose / No Coop

- **ID**: `RULE-LIVESTOCK-003`
- **Category**: Livestock / Blacklist
- **Condition**: Always
- **Action**: Never `BUILD_COOP`, never `BUY_ANIMAL GOOSE`
- **Empirical Evidence**: 0/205 episodes contain any coop or goose. Goose: cost 300 + coop space, produces EGG (base price 50), interval 1 day. Milk (base 160) and Wool (base 200) with 2–3 day intervals are vastly superior per tile. n=205.
- **Confidence**: 100%

---

### RULE-WHEAT-001: Maintain Wheat Buffer ≥ Animals × 1.5 Days

- **ID**: `RULE-WHEAT-001`
- **Category**: Feed / Supply Chain
- **Condition**: `shed.WHEAT < placed_animals * 2 AND day < 28`
- **Action**: `BUY_PRODUCT WHEAT N` where N = `placed_animals * 2 - shed.WHEAT`
- **Empirical Evidence**: HealthStone (highest win rate) maintains 22–24 wheat with ~14 animals = 1.7-day buffer. Others run 6–13 with ~12 animals = 0.5–1.1 day buffer. A missed feed kills an animal worth 400–500 + all future yield. n=205.
- **Confidence**: 90% (HealthStone's buffer is clearly larger and correlated with fewer escapes)
- **Implementation Complexity**: Low — current R5 uses `animals × 3` but the wheat buffer is under-maintained in practice. Calibrate to 2.0 days.

---

### RULE-CROP-001: Strawberry as Primary Crop (Target ~35 Tiles)

- **ID**: `RULE-CROP-001`
- **Category**: Crop Portfolio
- **Condition**: `crop_strawberry_tiles < 35 AND free_tiles > 0 AND days_left >= 13 AND seeds.STRAWBERRY > 0`
- **Action**: Plant STRAWBERRY
- **Empirical Evidence**: All 4 players maintain 33–36 strawberry tiles at day 15. n=205, >95% of games. Strawberry: ongoing, first yield day 10, every 2 days, base price 120.
- **Confidence**: 97%
- **Implementation Complexity**: Low — already in `policy.py`.

---

### RULE-CROP-002: Melon as Secondary Crop (~12 Tiles, Cutoff Day 17)

- **ID**: `RULE-CROP-002`
- **Category**: Crop Portfolio
- **Condition**: `crop_melon_tiles < 12 AND days_left >= 13 AND seeds.MELON > 0`
- **Action**: Plant MELON
- **Condition for cutoff**: `days_left < 13` → stop planting melon
- **Empirical Evidence**: All 4 players have 9–14 melon tiles at day 15. Last melon alive ~day 21 (planted by day ~8). n=205.
- **Confidence**: 95%

---

### RULE-CROP-003: Wheat as Filler and Feed Source

- **ID**: `RULE-CROP-003`
- **Category**: Crop Portfolio
- **Condition**: `free_tiles > 0 AND days_left >= 5`
- **Action**: Plant WHEAT (filler after melon/strawberry targets met)
- **Empirical Evidence**: All players maintain 13 wheat tiles at midgame. Wheat recycles melon tiles from day 20 onward (wheat count rises from 13 → 42 at day 25). n=205.
- **Confidence**: 97%

---

### RULE-CROP-004: No Carrot / No Tomato

- **ID**: `RULE-CROP-004`
- **Category**: Crop Blacklist
- **Condition**: Always
- **Action**: Never plant CARROT or TOMATO
- **Empirical Evidence**: <1% of episodes contain carrot (only HealthStone, occasionally). Zero tomato across all 205 episodes. n=205.
- **Confidence**: 99%

---

### RULE-ENDGAME-001: Endgame Wheat Blitz from Day 20

- **ID**: `RULE-ENDGAME-001`
- **Category**: Endgame / Crop Rotation
- **Condition**: `game.day >= 20`
- **Action**: Replace expired melon tiles with WHEAT (max yield in 4 days → harvest before season end)
- **Empirical Evidence**: Wheat tiles jump from ~5 at day 20 to ~42 at day 25 (from cross-player aggregate). n=205.
- **Confidence**: 97%

---

### RULE-ENDGAME-002: Stop Planting Melon After Day 17

- **ID**: `RULE-ENDGAME-002`
- **Category**: Endgame
- **Condition**: `game.day >= 17`
- **Action**: Do not plant new melon seeds
- **Empirical Evidence**: Last live melon tile mean = 21 days. Melon needs 13 days to reach max yield. Any melon planted after day 17 cannot reach full value (day 17 + 13 = day 30 = end of game). n=205.
- **Confidence**: 98%

---

### RULE-LABOUR-001: Crew Scaling Schedule

- **ID**: `RULE-LABOUR-001`
- **Category**: Labour
- **Condition**: Daily rehire at hour 0
- **Action**:
  | Day | Target Hands |
  |---|---|
  | 0 | 4 (or 3 per HealthStone) |
  | 1–4 | 1–3 (save cash for land/animals) |
  | 5–6 | 3–4 |
  | 7–10 | 7–9 |
  | 11–19 | 10 |
  | 20–29 | 12–14 |
- **Empirical Evidence**: Cross-player consensus on crew size at each phase. n=205. Day 1 = 0 (HealthStone only, highest win rate).
- **Confidence**: 90%
- **Implementation Complexity**: Medium — current `target_hands` function returns 5/3/8/13. Must recalibrate.
