# Player Deep Dive: HealthStone

> Phase 3 deliverable — n=60 episodes, 43,200 canonical turns.
> Win rate: **91.7%**. Mean score: **90,802** (median: 89,772, max: 151,412).

---

## Opening Phase (Days 0–6)

### Day 0 Blueprint (100% consistency, n=60)
| Order | Action |
|---|---|
| ×3 | `HIRE` (one fewer than others) |
| ×1 | `BUY_ANIMAL COW 1` |
| ×1 | `BUY_ANIMAL SHEEP 4` (or different split — see below) |
| ×1 | `BUY_SEED MELON` (more melons than others) |
| ×1 | `BUY_SEED WHEAT` |
| — | NO `BUY_PRODUCT WHEAT` on day 0 |

**Day 0 spend**: ~2,929 of 3,000. Leaves 71 in reserve (vs ~7 for others).

**Day 0 farm state**:
- Money: 71 remaining (vs ~7 for others — HealthStone keeps a cash buffer)
- Pastures: 3.25 (slightly more than the 2.83 of others)
- Melon: 2.96 tiles (vs 1.75 for others — more melon focus)
- Wheat: 1.16 tiles (vs 2.54 — less wheat, more melon)
- Hands: 3.0 (vs 4.0 for others — one fewer hire)

### Labor Ramp
| Day | Hands |
|---|---|
| 0 | 3 |
| 1 | 0 |
| 2 | 3 |
| 3 | 3 |
| 5 | 3.9 |
| 7 | 6.8 |
| 9 | 9 |
| 11 | 10 |
| 13 | 10 |
| 15 | 10 |
| 20 | 12.8 |
| 25 | 12.1 |
| 29 | 10 |

**Notable**: Day 1 = 0 hands (no rehire on day 1 — saves ~2 cost). Scales more smoothly and reaches 10 hands by day 9, one day earlier than others (who hit 10 only at day 11).

### Land Expansion
- **NE**: Day 6.0 ± 0 (100%)
- **SW**: Day 10.0 ± 0 (100%)
- **SE**: 0/60 games (0%)

---

## Midgame Engine (Days 7–20)

### Pasture Build-Up — **HealthStone's Key Differentiation**
| Day | Pastures |
|---|---|
| 5 | 5.5 (min 5, max 6) |
| 7 | 9.3 (8–11) |
| 10 | 13.2 (12–15) |
| 11 | 13.6 (12–17) |
| 13 | 14.1 (12–18) |
| 15 | 14.2 (12–18) |
| 20 | 14.3 |
| 25 | 14.4 |

**+2 pastures vs Ezzzzzekki/GiovanniCR** — 14 vs 12 at steady state. This directly enables more animals and more daily fertilizer income.

### Livestock Composition at Day 15
- **Cows**: 8.98 ± 0.81 (~9 cows, sometimes 10)
- **Sheep**: 5.02 ± 1.33 (~5 sheep)
- **Ratio**: 1.79:1 (more balanced than GiovanniCR's 2:1)

### Crop Portfolio at Day 15
| Crop | Tiles |
|---|---|
| Strawberry | 33.1 (fewer than others — tiles used for more pastures) |
| Melon | 9.8 (fewer melon — faster to shift pasture) |
| Wheat | 13.6 |

### Wheat Supply — **HealthStone's Key Differentiation**
| Day | Shed Wheat |
|---|---|
| 5 | 6.2 |
| 10 | 22.1 ± 2.5 |
| 15 | 23.8 ± 4.7 |
| 20 | 23.7 ± 4.4 |

**Massive wheat buffer vs others** — maintains 22–24 units in shed throughout the season (others run 6–13). This ensures animals are never at starvation risk and supports a larger herd.

### Sell Behaviour
| Product | Batches | Total | Mean Batch |
|---|---|---|---|
| WHEAT | 2,044 | 25,504 | 12.5 |
| FERTILIZER | 3,226 | 15,501 | 4.8 |
| STRAWBERRY | 1,903 | 14,063 | 7.4 |
| MILK | 2,297 | 11,067 | 4.8 |
| WOOL | 1,694 | 8,043 | 4.7 |
| MELON | 642 | 5,186 | 8.1 |
| CARROT | 47 | 246 | 5.2 |

**Notable**: HealthStone is the only player that sells occasional CARROT. Sell batches are smaller (7.4 strawberry vs 15.2 for Ezzzzzekki) — more frequent smaller sells that reduce market glut risk.

---

## Endgame Liquidation

- **Last melon tile day**: 21.4
- **Last strawberry tile day**: 28.9 (holds strawberries longest — nearly to end of season)

---

## Distinguishing Characteristics

1. **Higher pasture target** (~14 vs ~12) — the single biggest structural difference from others.
2. **Larger wheat buffer** (22–24 vs 6–13) — livestock safety net, never at starvation risk.
3. **More cows** (~9 vs ~8) — higher milk production, more fertilizer.
4. **Day 1 zero hands** — deliberate cost savings on the cheapest day.
5. **Highest win rate** (91.7%) — most consistent performer.
6. **Smaller sell batches** — more conservative market management.
