# Player Deep Dive: GiovanniCR

> Phase 3 deliverable — n=48 episodes, 34,560 canonical turns.
> Win rate: **87.5%**. Mean score: **90,336** (median: 91,590, max: 149,642).

---

## Opening Phase (Days 0–6)

### Day 0 Blueprint (100% consistency, n=48)
| Order | Action |
|---|---|
| ×4 | `HIRE` |
| ×1 | `BUY_ANIMAL COW 1` |
| ×1 | `BUY_ANIMAL SHEEP 4` |
| ×1 | `BUY_SEED WHEAT` |
| ×1 | `BUY_SEED MELON` |
| ×1 | `BUY_PRODUCT WHEAT` |

**Day 0 spend**: ~2,992 of 3,000. Full commitment identical to Ezzzzzekki / ThunderThunder.

**Day 0 farm state**: Pastures 2.83, cows 0.75, sheep 1.88, wheat 2.54, melon 1.75.

### Labor Ramp
| Day | Hands |
|---|---|
| 0 | 4 |
| 1 | 1 |
| 2 | 2 |
| 3 | 3 |
| 5 | 3 |
| 7 | 7 |
| 9 | 7 |
| 11 | 10 |
| 13 | 8 |
| 15 | 9 |
| 20 | 14 |
| 25 | 12 |
| 29 | 9 |

### Land Expansion
- **NE**: Day 6.0 ± 0 (100%)
- **SW**: Day 10.0 ± 0 (100%)
- **SE**: 0/48 games (0%)

---

## Midgame Engine (Days 7–20)

### Pasture Build-Up
| Day | Pastures |
|---|---|
| 5 | 6.0 |
| 7 | 9.0 (zero variance) |
| 10 | 12.0 (zero variance) |
| 15 | 12.0 |
| 20 | 12.0 |
| 25 | 15.0 |

**Key observation**: GiovanniCR holds exactly 12 pastures through day 20, then adds 3 more at day 25. This is a late pasture expansion pattern not seen in Ezzzzzekki.

### Livestock Composition at Day 15
- **Cows**: 8.00 ± 0.00 — **perfect consistency, always exactly 8**
- **Sheep**: 4.00 ± 0.00 — **perfect consistency, always exactly 4**
- **Ratio**: 2.00:1

### Crop Portfolio at Day 15
| Crop | Tiles |
|---|---|
| Strawberry | 35.9 |
| Melon | 13.7 |
| Wheat | 13.0 |

### Wheat Supply
| Day | Shed Wheat |
|---|---|
| 5 | 7.0 |
| 10 | 12.7 |
| 15 | 5.9 |
| 20 | 12.9 |

**Pattern**: GiovanniCR oscillates wheat — buys in bulk around day 10 and day 20, lets it run low mid-cycle.

### Sell Behaviour
| Product | Batches | Total | Mean Batch |
|---|---|---|---|
| WHEAT | 1,632 | 21,120 | 12.9 |
| STRAWBERRY | 960 | 13,248 | 13.8 |
| FERTILIZER | 2,304 | 11,472 | 5.0 |
| MILK | 1,488 | 10,800 | 7.3 |
| WOOL | 768 | 6,624 | 8.6 |
| MELON | 768 | 5,472 | 7.1 |

---

## Endgame Liquidation

- **Last melon tile day**: 21.0 (sharpest cutoff)
- **Last strawberry tile day**: 28.0
- Endgame wheat blitz profile identical to Ezzzzzekki/ThunderThunder.

---

## Distinguishing Characteristics

1. **Perfectly deterministic animal purchasing** — always exactly 8 cows and 4 sheep by day 15, zero variance. Clearest signal of a rule-based agent with hard-coded targets.
2. **Tightest score distribution** — std=23,378, the lowest of all 4 players. Highly consistent strategy.
3. **Late pasture expansion** — adds 3 pastures between day 20–25 (from 12 to 15). This may represent a mid-game sheep conversion or opportunistic build once melons expire.
4. **Best median score** (91,590) though GiovanniCR has fewer episodes than HealthStone.
