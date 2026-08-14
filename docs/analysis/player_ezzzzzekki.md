# Player Deep Dive: Ezzzzzekki

> Phase 3 deliverable — n=44 episodes, 31,680 canonical turns.
> Win rate: **86.4%**. Mean score: **89,666** (median: 85,340, max: 160,864).

---

## Opening Phase (Days 0–6)

### Day 0 Blueprint (100% consistency, n=44)
| Order | Action | Notes |
|---|---|---|
| ×4 | `HIRE` | 4 hands hired immediately |
| ×1 | `BUY_ANIMAL COW 1` | |
| ×1 | `BUY_ANIMAL SHEEP 4` | Wait — 1 cow + 4 sheep is the Ezzzzzekki/GiovanniCR/ThunderThunder opening |
| ×1 | `BUY_SEED WHEAT` | |
| ×1 | `BUY_SEED MELON` | |
| ×1 | `BUY_PRODUCT WHEAT` | Feed reserve purchased immediately |

**Day 0 spend**: ~2,993 of 3,000 (leaves ~7 cash). Full commitment.

**Day 0 farm state (hour=0)**:
- Money: 3,000 → ~7 by hour 6
- Pastures: 2.83 (6 built by end of day)
- Animals: 0.75 cow, 1.88 sheep (in shed at hour 0, placed during day)
- Wheat tiles: 2.54, Melon tiles: 1.75 (planted during day)

### Labor Ramp
| Day | Hands (end-of-day) |
|---|---|
| 0 | 4 |
| 1 | 1 |
| 2 | 2 |
| 3 | 3 |
| 5 | 3 |
| 7 | 7 |
| 9 | 7 |
| 11 | 10 |
| 13 | 8.1 |
| 15 | 9.1 |
| 20 | 14 |
| 25 | 12 |
| 29 | 10 |

### Land Expansion
- **NE unlock**: Day 6.0 ± 0 (100% of episodes, zero variance)
- **SW unlock**: Day 10.0 ± 0 (100% of episodes, zero variance)
- **SE unlock**: 0/44 games (0%) — never purchased

---

## Midgame Engine (Days 7–20)

### Pasture Build-Up
| Day | Mean Pastures |
|---|---|
| 5 | 6.0 (always exactly 6) |
| 7 | 9.0 (8–9) |
| 10 | 12.2 (12–17) |
| 11 | 12.2 |
| 15 | 12.2 |
| 20 | 12.2 |

**Key observation**: Ezzzzzekki locks at exactly 12 pastures for most games — less aggressive expansion than HealthStone/ThunderThunder (14+).

### Livestock Composition at Day 15
- **Cows**: 7.89 ± 0.54 (nearly always 8)
- **Sheep**: 4.32 ± 1.47 (more variance — sometimes stops at 4)
- **Ratio**: 1.83:1 (cow-heavy)
- **Goose**: 0 (never)

### Crop Portfolio at Day 15
| Crop | Tiles |
|---|---|
| Strawberry | 35.5 |
| Melon | 13.4 |
| Wheat | 13.0 |
| Carrot | 0 |
| Tomato | 0 |

### Wheat Supply Management
| Day | Shed Wheat (hour=23) |
|---|---|
| 5 | 7.0 ± 0.0 |
| 10 | 13.1 ± 0.6 |
| 15 | 6.0 ± 1.3 |
| 20 | 8.6 ± 6.3 |

**Pattern**: Tight wheat buffer — runs close to minimum (animals × 2–3 days).

### Sell Behaviour (lifetime totals per episode)
| Product | Batches | Total Units | Mean Batch |
|---|---|---|---|
| WHEAT | 1,621 | 19,847 | 12.2 |
| STRAWBERRY | 824 | 12,484 | 15.2 |
| MILK | 1,413 | 10,459 | 7.4 |
| FERTILIZER | 2,156 | 10,426 | 4.8 |
| WOOL | 580 | 6,068 | 10.5 |
| MELON | 702 | 5,052 | 7.2 |

---

## Endgame Liquidation (Days 21–29)

- **Last melon tile day**: mean 21.2 (melon planting stops ~day 17, last melon alive until ~day 21)
- **Last strawberry tile day**: mean 27.9 (planted right up to ~day 15–16, alive until late)
- **Endgame wheat blitz**: melon tiles recycled into wheat from ~day 20 (wheat tiles jump from 5.5 → 22.4 → 30.3 → 42.1 → 29.8 at days 20–28)

---

## Distinguishing Characteristics

1. **Identical to GiovanniCR and ThunderThunder** — same opening (4 HIRE, 1 COW, 4 SHEEP), same land schedule (NE d6, SW d10), same pasture curve. These three agents appear to run the same codebase or near-identical strategies.
2. **12 pastures max** — stops 2 fewer than HealthStone's 14 average.
3. **Tighter sheep count** — mean 4.3 sheep vs HealthStone's 5.0 — potentially leaving passive income on the table.
4. **High variance score** (std=30,175 vs GiovanniCR's 23,378) — more volatile outcomes.
