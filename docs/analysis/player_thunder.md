# Player Deep Dive: ThunderThunder

> Phase 3 deliverable — n=53 episodes, 38,160 canonical turns (display name: "THUNDER THUNDER").
> Win rate: **96.2%**. Mean score: **91,290** (median: 90,680, max: 139,403).

---

## Opening Phase (Days 0–6)

### Day 0 Blueprint (100% consistency, n=53)
| Order | Action |
|---|---|
| ×4 | `HIRE` |
| ×1 | `BUY_ANIMAL COW 1` |
| ×1 | `BUY_ANIMAL SHEEP 4` |
| ×1 | `BUY_SEED WHEAT` |
| ×1 | `BUY_SEED MELON` |
| ×1 | `BUY_PRODUCT WHEAT` |

Identical opening to Ezzzzzekki and GiovanniCR. Day 0 spend ~2,991, leaves ~9 cash.

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
| 13 | 9 |
| 15 | 10.2 |
| 20 | 14 |
| 25 | 12.7 |
| 29 | 10 |

### Land Expansion
- **NE**: Day 6.0 ± 0 (100%)
- **SW**: Day 10.0 ± 0 (100%)
- **SE**: 0/53 games (0%)

---

## Midgame Engine (Days 7–20)

### Pasture Build-Up
| Day | Pastures |
|---|---|
| 5 | 6.0 |
| 7 | 8.9 (8–10) |
| 10 | 13.7 (12–17) |
| 11 | 13.9 (12–17) |
| 13 | 13.9 |
| 15 | 13.9 |
| 20 | 14.0 |
| 25 | 15.0 |

**Similar to HealthStone** — reaches ~14 pastures by day 10–11, more aggressive than Ezzzzzekki/GiovanniCR's 12.

### Livestock Composition at Day 15
- **Cows**: 8.68 ± 1.03 (typically 8–9)
- **Sheep**: 5.25 ± 2.00 (5–6, more variance)
- **Ratio**: 1.65:1 (most balanced ratio of the four)

### Crop Portfolio at Day 15
| Crop | Tiles |
|---|---|
| Strawberry | 34.9 |
| Melon | 13.2 |
| Wheat | 13.0 |

### Wheat Supply
| Day | Shed Wheat |
|---|---|
| 5 | 6.9 |
| 10 | 13.5 |
| 15 | 7.0 |
| 20 | 13.2 |

Similar oscillation to Ezzzzzekki — buys in batches, runs close to minimum.

### Sell Behaviour
| Product | Batches | Total | Mean Batch |
|---|---|---|---|
| WHEAT | 1,760 | 22,992 | 13.1 |
| STRAWBERRY | 973 | 14,378 | 14.8 |
| FERTILIZER | 2,816 | 14,027 | 5.0 |
| MILK | 1,730 | 11,988 | 6.9 |
| WOOL | 965 | 8,464 | 8.8 |
| MELON | 770 | 5,813 | 7.5 |

---

## Endgame Liquidation

- **Last melon tile day**: 21.6 (latest of all 4 players — holds melons slightly longer)
- **Last strawberry tile day**: 27.5 (ends strawberries earliest of the four)

---

## Distinguishing Characteristics

1. **Highest win rate** (96.2%) — the benchmark player in terms of competitive outcomes.
2. **Most balanced cow/sheep ratio** (1.65:1) — closer to parity than others, potentially exploiting both milk and wool pricing.
3. **14 pastures like HealthStone** — confirms the 14-pasture target is associated with higher win rates.
4. **More sheep variance** (std=2.0) — may be adapting sheep purchases to market wool price.
5. **Largest strawberry sell batches** (14.8 mean) — aggressive strawberry liquidation.
6. **Later melon cutoff** (21.6 vs 21.0) — holds melon tiles ~0.6 days longer, extracting maximum yield before recycling to wheat.
