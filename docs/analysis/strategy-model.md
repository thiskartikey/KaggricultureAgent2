# Unified 10-Pillar Strategy Model

> Phase 7 deliverable — coherent, non-contradictory master strategy blueprint assembled from all empirical rules.

---

## Overview

This blueprint is derived from 205 episodes of the 4 top-ranked Kaggriculture players. It represents the consensus optimal strategy with player-innovation extensions. Confidence is grounded in the empirical decision rule catalog (`decision-rules.md`).

---

## Pillar 1: Opening Acceleration (Days 0–1)

**Goal**: Deploy maximum capital on Day 0 to start the animal and crop engines simultaneously.

**Blueprint** (preferred — 4-hire variant, 75% of corpus):
```
Hour 0, Day 0:
  HIRE × 4
  BUY_ANIMAL COW 1
  BUY_ANIMAL SHEEP 4
  BUY_SEED MELON (enough for 5+ tiles)
  BUY_SEED WHEAT (7+)
  BUY_PRODUCT WHEAT 8 (feed reserve)
```

**Alternative** (HealthStone — highest win rate, 91.7%/96.2% with TT):
```
  HIRE × 3 (saves 1 unit cost)
  BUY_ANIMAL COW 1
  BUY_ANIMAL SHEEP 4
  BUY_SEED MELON (more seeds)
  BUY_SEED WHEAT
  (defer wheat purchase to day 1–2)
```

**Day 1**: Zero hands if cash is tight (HealthStone pattern) — the farm only has 1 NW quadrant and 3 hands worth of work. Save the hire cost.

**Constraints**: Spend all but ~7–71 cash on Day 0. The day-0 compounding effect of 5 planted tiles and 5 animals vastly outweighs any cash reserve.

---

## Pillar 2: Land Acquisition Blueprint

**Schedule** (all 4 players, 100% consistency):
| Action | Trigger |
|---|---|
| Buy NE (1,000) | Day 6, money ≥ 1,350 |
| Buy SW (2,000) | Day 10, money ≥ 2,350 |
| Never buy SE (4,000) | — |

**Rationale**: NE on day 6 opens 25 tiles for 19 remaining days = 475 tile-days at ~100–200 revenue/tile-day. SW on day 10 opens another 25 tiles for 15 days. SE would open 25 tiles for only 11 days — the 4,000 cost cannot be recouped.

> Current `policy.py` unlocks NE on day 7 and SW on day 11 — **both 1 day late**. Correcting this is the highest-confidence change available.

---

## Pillar 3: Labour Scaling & Daily Budgeting

**Target crew size by phase**:
| Days | Target Hands | Notes |
|---|---|---|
| 0 | 4 | Full opening crew |
| 1 | 0–1 | Save cost; farm barely needs labour |
| 2–4 | 2–3 | Light maintenance |
| 5–6 | 3–4 | Pre-expansion |
| 7–10 | 7–9 | After NE unlock; more tiles to work |
| 11–19 | 10 | After SW unlock; full animal+crop load |
| 20–29 | 12–14 | Harvest sprint; every unit pays back |

**Rule**: Hands are FREE every morning — rehire from scratch daily. The fib(n) cost is trivial compared to the value of worked tiles. A 14-hand crew from day 20 costs ~986/day vs the ~2,000+ in produce they process.

---

## Pillar 4: Dual-Livestock Husbandry Engine

**Targets** (from HealthStone/ThunderThunder, highest win-rate players):
- **14 pastures** total (reached by day 10–11)
- **9 cows** (produces MILK every 2 days + 1 FERTILIZER/day)
- **5 sheep** (produces WOOL every 3 days + 1 FERTILIZER/day)
- **0 goose/coop** — EGG at base 50 is dominated by MILK (160) and WOOL (200)

**Layout**: Place pastures in shed-adjacent tiles first (minimize walk distance for FEED/CARE/HARVEST).

**Daily protocol** (in order):
1. **FEED** first — missed feed is catastrophic (animal escapes if unfed 2 days)
2. **HARVEST** yield if `yield_units > 0`
3. **COLLECT_FERTILIZER** if available
4. **CARE** if fed today (banks +1 bonus on next production day)

**Wheat buffer**: Maintain `shed.WHEAT ≥ placed_animals × 2` at all times. HealthStone keeps 22–24 wheat with 14 animals.

---

## Pillar 5: Crop Rotation & Life-Cycle Management

**Steady-state portfolio** (from day 11 onward, 75 unlocked tiles):
| Crop | Tiles | Notes |
|---|---|---|
| Strawberry | ~35 | Ongoing, every 2 days, base 120. Keep planting through day 15 |
| Melon | ~12 | One-time, max day 12, base 250. Plant through day 17; recycle after |
| Wheat | ~13 | Fill remaining tiles + endgame blitz |
| Pasture | ~14 | Animal housing (see Pillar 4) |

**Lifecycle rules**:
- MELON: plant day 0–17, harvest at max_yield_day, recycle tile to WHEAT
- STRAWBERRY: plant continuously through day 15, harvest as yield appears
- WHEAT: filler + feed + endgame wheat blitz from day 20

**Fertilize**: Apply FERTILIZER to strawberry tiles (doubles next yield: 120 → 240). Prioritise tiles near next production day.

---

## Pillar 6: Worker Routing & Sticky Task Allocation

**Tier priority** (never defer a higher tier for a lower one):
| Tier | Task | Rationale |
|---|---|---|
| 0 | FEED unfed animals | Escape = total loss of 400–500 + future yield |
| 0 | WATER dying plants | Two dry days = weed (total loss) |
| 1 | HARVEST ready crops | Ongoing crops accumulate beyond shed cap |
| 1 | PLACE animals | Animal in shed earns nothing |
| 2 | BUILD pastures | Must precede animal placement |
| 2 | PLANT free tiles | Every day planted = +1 day of revenue |
| 2 | FERTILIZE strawberry | Doubles yield for nearly free |
| 3 | WATER-soon | Safe today; do it tomorrow if needed |
| 4 | DIG weeds | Low urgency |

**Sticky claims**: A worker committed to a task holds it until complete. Prevents oscillation (walking to a tile, getting reassigned, walking back).

**Shed-proximity ordering**: Fill tiles nearest the shed first (coordinates (4,4), (5,4), (4,5), (5,5) = shed adjacent). This minimises FEED/CARE walk cost — the most frequent operation per day.

---

## Pillar 7: Market Order Optimisation

**Per-turn order priority** (up to 10 orders):
1. SELL produce (price-floor gated; endgame = sell everything)
2. HIRE crew (hours 0–1 only)
3. BUY_LAND (on schedule)
4. BUY_PRODUCT WHEAT (maintain animal buffer)
5. BUY_ANIMAL (fill empty pastures: cows first to target, then sheep)
6. BUY_SEED (fill free tiles)

**Sell timing**:
- Sell every turn when shed is full (>85% capacity → ignore price floor)
- Hold `animals × 2` wheat as feed reserve
- Endgame (day ≥ 27): sell everything regardless of price

**Price floor** (avoid dumping when market is glutted):
- STRAWBERRY: never sell below 60 (50% of 120) unless endgame
- MELON: never sell below 200 (80% of 250) unless endgame
- MILK/WOOL: never sell below 80/100 unless endgame
- FERTILIZER: always sell (fungible, base 100)

---

## Pillar 8: Town Demand & Shop Exploitation

**Town centre** drains 1 unit of each non-fertilizer product every 24 turns. Scaling: ×1 before day 10, ×2 days 10–19, ×4 day 20+.

**Shop demand** reduces market inventory (and thus supports higher prices). Priority products:
- BAKERY (EGG + WHEAT) — never relevant (no eggs)
- YARN_STORE (WOOL × 2) — prioritise WOOL production if wool price high
- ICE_CREAM_SHOP (STRAWBERRY + MILK + WHEAT) — supports all primary products
- SMOOTHIE_SHOP (STRAWBERRY + MILK) — same

**Rule**: No specific action needed. Town demand passively supports prices on our primary products (STRAWBERRY, MILK, WOOL, MELON, FERTILIZER). Avoid early-dumping to exploit high prices sustained by town drain.

---

## Pillar 9: Endgame Depletion & Liquidation (Days 20–29)

**Day-by-day depletion schedule**:
| Day | Action |
|---|---|
| 17 | Stop planting MELON (can't reach full yield) |
| 20 | Begin endgame wheat blitz — recycle melon tiles to wheat |
| 22 | Stop planting STRAWBERRY (won't complete 2 production cycles) |
| 25 | Shed capacity management — sell in smaller batches to avoid glut |
| 27 | Drop price floors — sell everything regardless of price |
| 28 | Harvest all remaining yield; no new planting |
| 29 | Final market dump — everything in shed to market |

**Animal sunset**: Keep feeding and harvesting animals through day 27 (milk/wool at days 26–27 still valuable). Stop feed after day 27.

---

## Pillar 10: Fault Tolerance & Recovery

**Anti-starvation**: Never let `shed.WHEAT < placed_animals` with money > wheat_cost × 2.

**Weed clearing**: Clear weeds only when no tier-0, 1, or 2 tasks remain. A weed on a future pasture site should be cleared early; a weed in a corner can wait.

**Lost animals**: If an animal escapes (structure empty, no animal), rebuild by buying a replacement animal. Do not rebuild the structure (it survives escape).

**Cash floor**: Never drop below 350 on a non-land-purchase turn. Required for next-hour fib(0)=1 hire and emergency feed.
