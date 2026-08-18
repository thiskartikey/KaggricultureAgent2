# Cross-Player Comparative Analysis Matrix

> Phases 4 & 5 deliverable — statistical comparison of all 4 top players across 205 episodes.
> Sample sizes: Ezzzzzekki n=44, GiovanniCR n=48, HealthStone n=60, ThunderThunder n=53.

---

## 1. Final Score Distributions

| Player | Mean | Median | StdDev | Q25 | Q75 | Max | Win Rate |
|---|---|---|---|---|---|---|---|
| Ezzzzzekki | 89,666 | 85,340 | 30,175 | 67,240 | 111,315 | 160,864 | 86.4% |
| GiovanniCR | 90,336 | 91,590 | 23,378 | 75,904 | 98,086 | 149,642 | 87.5% |
| HealthStone | 90,802 | 89,772 | 26,253 | 68,380 | 104,666 | 151,412 | 91.7% |
| ThunderThunder | 91,290 | 90,680 | 23,750 | 75,970 | 102,671 | 139,403 | **96.2%** |

**Cross-player ranking** (by win rate): ThunderThunder > HealthStone > GiovanniCR > Ezzzzzekki

---

## 2. Land Acquisition (100% agreement across all 4 players)

| Metric | Ezzzzzekki | GiovanniCR | HealthStone | ThunderThunder | Consensus |
|---|---|---|---|---|---|
| NE unlock day | 6.0 ± 0 | 6.0 ± 0 | 6.0 ± 0 | 6.0 ± 0 | **Day 6, zero variance** |
| SW unlock day | 10.0 ± 0 | 10.0 ± 0 | 10.0 ± 0 | 10.0 ± 0 | **Day 10, zero variance** |
| SE purchased | 0% | 0% | 0% | 0% | **Never** |

> **SHARED INVARIANT**: All 4 players unlock NE on day 6 and SW on day 10, in 100% of games. SE (4,000) is never bought.

---

## 3. Opening Blueprint (Day 0)

| Action | Ezzzzzekki | GiovanniCR | HealthStone | ThunderThunder |
|---|---|---|---|---|
| HIRE (day 0) | 4 | 4 | **3** | 4 |
| BUY_ANIMAL COW | 1 | 1 | 1 | 1 |
| BUY_ANIMAL SHEEP | 4 | 4 | 4 | 4 |
| BUY_SEED MELON | ✓ | ✓ | ✓ | ✓ |
| BUY_SEED WHEAT | ✓ | ✓ | ✓ | ✓ |
| BUY_PRODUCT WHEAT | ✓ | ✓ | **✗** | ✓ |
| Cash remaining | ~7 | ~8 | **~71** | ~9 |

> **INNOVATION (HealthStone)**: 3 hires instead of 4, no day-0 wheat purchase, keeps 71 in reserve. Tradeoff: 1 fewer hand on day 0, but 71 more cash for early pasture builds.

---

## 4. Labour Trajectory

| Day | Ezzzzzekki | GiovanniCR | HealthStone | ThunderThunder |
|---|---|---|---|---|
| 0 | 4 | 4 | 3 | 4 |
| 1 | 1 | 1 | **0** | 1 |
| 2 | 2 | 2 | 3 | 2 |
| 3 | 3 | 3 | 3 | 3 |
| 5 | 3 | 3 | 3.9 | 3 |
| 7 | 7 | 7 | 6.8 | 7 |
| 9 | 7 | 7 | **9** | 7 |
| 11 | 10 | 10 | 10 | 10 |
| 20 | **14** | **14** | 12.8 | **14** |
| 25 | 12 | 12 | 12.1 | 12.7 |

> **SHARED INVARIANT**: All players reach 10 hands by day 11. Maximum of 14 from day 20.
> **INNOVATION (HealthStone)**: Day 1 zero hands (saves cost), reaches 9 hands by day 9 (earlier ramp).

---

## 5. Pasture Build-Up

| Day | Ezzzzzekki | GiovanniCR | HealthStone | ThunderThunder |
|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 |
| 5 | 6 | 6 | 5.5 | 6 |
| 7 | 9.0 | 9.0 | **9.3** | **8.9** |
| 10 | 12.2 | 12.0 | **13.2** | **13.7** |
| 11 | 12.2 | 12.0 | **13.6** | **13.9** |
| 15 | 12.2 | 12.0 | **14.2** | **13.9** |
| 25 | 13.2 | **15.0** | 14.4 | **15.0** |

> **KEY DIVERGENCE**: HealthStone and ThunderThunder target **~14 pastures** from day 10–11 onward. Ezzzzzekki and GiovanniCR cap at **12** until day 25. The +2 pastures = +2 animals = +2 fertilizer/day = ~+2,400 additional fertilizer revenue over 12 remaining days.

---

## 6. Livestock Composition at Day 15

| Player | Cows | Sheep | Ratio | Total Animals |
|---|---|---|---|---|
| Ezzzzzekki | 7.89 ± 0.54 | 4.32 ± 1.47 | 1.83:1 | 12.2 |
| GiovanniCR | **8.00 ± 0.00** | **4.00 ± 0.00** | 2.00:1 | 12.0 |
| HealthStone | 8.98 ± 0.81 | 5.02 ± 1.33 | 1.79:1 | **14.0** |
| ThunderThunder | 8.68 ± 1.03 | 5.25 ± 2.00 | **1.65:1** | 13.9 |

> **SHARED INVARIANT** (3/4 players): Target 8 cows. Seen in 94%+ of episodes.
> **INNOVATION (HealthStone/Thunder)**: ~9 cows + ~5 sheep = 14 total (vs 12). Extra revenue from milk and fertilizer.

---

## 7. Crop Portfolio at Day 15

| Crop | Ezzzzzekki | GiovanniCR | HealthStone | ThunderThunder |
|---|---|---|---|---|
| Strawberry | 35.5 | **35.9** | 33.1 | 34.9 |
| Melon | 13.4 | **13.7** | 9.8 | 13.2 |
| Wheat | 13.0 | 13.0 | 13.6 | 13.0 |
| Carrot | 0 | 0 | **0.1** | 0 |
| Tomato | 0 | 0 | 0 | 0 |

> **SHARED INVARIANT**: ~35 strawberry tiles, ~12 melon tiles, ~13 wheat tiles at midgame peak.
> HealthStone has slightly fewer strawberry/melon tiles — those tiles are taken by the 2 extra pastures.

---

## 8. Wheat Supply Management

| Day | Ezzzzzekki | GiovanniCR | HealthStone | ThunderThunder |
|---|---|---|---|---|
| 5 | 7.0 | 7.0 | 6.2 | 6.9 |
| 10 | 13.1 | 12.7 | **22.1** | 13.5 |
| 15 | 6.0 | 5.9 | **23.8** | 7.0 |
| 20 | 8.6 | 12.9 | **23.7** | 13.2 |

> **KEY DIVERGENCE (HealthStone)**: Maintains 22–24 wheat throughout midgame — 3–4× more than others. With 14 animals, this is a ~1.7-day buffer (24/14). Others run a tighter ~0.5-day buffer with 12 animals.

---

## 9. Market Behaviour

### Sell Batch Sizes (mean per order)
| Product | Ezzzzzekki | GiovanniCR | HealthStone | ThunderThunder |
|---|---|---|---|---|
| STRAWBERRY | **15.2** | 13.8 | 7.4 | 14.8 |
| MILK | 7.4 | 7.3 | 4.8 | 6.9 |
| WOOL | 10.5 | 8.6 | 4.7 | 8.8 |
| MELON | 7.2 | 7.1 | 8.1 | 7.5 |
| FERTILIZER | 4.8 | 5.0 | 4.8 | 5.0 |
| WHEAT | 12.2 | 12.9 | 12.5 | 13.1 |

> HealthStone sells in smaller batches (more conservative, less market impact). The three identical-strategy agents sell strawberries in larger batches (~15 units).

---

## 10. Endgame Timings

| Metric | Ezzzzzekki | GiovanniCR | HealthStone | ThunderThunder |
|---|---|---|---|---|
| Last melon tile day | 21.2 | **21.0** | 21.4 | **21.6** |
| Last strawberry tile day | 27.9 | **28.0** | **28.9** | 27.5 |

---

## 11. Strategy Taxonomy

### Shared Invariants (≥3 players, ≥80% frequency) → MANDATORY

| ID | Pattern | Players | Frequency |
|---|---|---|---|
| INV-001 | NE land unlock day 6 | 4/4 | 100% |
| INV-002 | SW land unlock day 10 | 4/4 | 100% |
| INV-003 | SE land never purchased | 4/4 | 100% |
| INV-004 | Day 0: 1 COW + 4 SHEEP | 4/4 | 100% |
| INV-005 | Target ~8 cows | 4/4 | 94%+ |
| INV-006 | ~35 strawberry tiles at midgame | 4/4 | 95%+ |
| INV-007 | ~12–14 melon tiles at midgame | 4/4 | 95%+ |
| INV-008 | 10+ hands by day 11 | 4/4 | 100% |
| INV-009 | No GOOSE/COOP/EGG | 4/4 | 100% |
| INV-010 | No CARROT/TOMATO planted | 4/4 | 99%+ |
| INV-011 | 6 pastures built by day 5 | 4/4 | 100% |

### Player Innovations → HIGH-PRIORITY EXPERIMENTS

| ID | Player | Innovation | Win Rate Impact |
|---|---|---|---|
| INN-001 | HealthStone / ThunderThunder | 14 pastures vs 12 | +91.7/96.2% vs 86.4/87.5% |
| INN-002 | HealthStone | 3 hires day 0 (saves 1 fib unit) | Part of higher win rate |
| INN-003 | HealthStone | Larger wheat buffer (22–24 vs 6–13) | Fewer animal escapes |
| INN-004 | GiovanniCR / ThunderThunder | Late pasture expansion day 25 (+3) | Associated with final score bump |

### Suboptimal Artifacts → EXPLICIT BLACKLIST

| ID | Pattern | Evidence |
|---|---|---|
| BL-001 | SE quadrant purchase | 0/205 games — negative ROI confirmed |
| BL-002 | GOOSE/COOP/EGG | 0/205 games — never seen in any win |
| BL-003 | CARROT cultivation | <1% of episodes — near-zero contribution |
| BL-004 | TOMATO cultivation | 0/205 games — never seen |
