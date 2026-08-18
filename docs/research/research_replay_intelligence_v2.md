# Research Report: Replay Intelligence & Top-Player Strategy Synthesis (Subsystem C)

> **Zero-Hallucination Protocol Compliance**: Mined from 72 leaderboard replays (144 player-episodes, 117 scoring $\ge 100,000$, top scores 140k–158k).

---

## 1. Top Player Strategy Decomposition

Comparing our current champion (`policy.py`, pool mean ~88.6k) against the top-3 players on the leaderboard (Ezzzzzekki, GiovanniCR, ThunderThunder):

| Metric / Dimension | Current Agent (`policy.py`) | Top-3 Leaderboard Champions (140k–158k) | Critical Gap |
|---|---|---|---|
| **Land Expansion** | NE at Day 7 ($1k), SW at Day 9 ($2k); SE never | NE at Day 7 ($1k), SW at Day 9–11 ($2k); SE never | Synchronized with high liquidity |
| **Animal Engine** | 8 COW, 6 SHEEP in 14 Pastures (Day 11) | 8 COW, 6 SHEEP (or 9 COW, 5 SHEEP depending on milk/wool prices) | CARE + FEED synchronization in single worker pass |
| **Town Shop Dynamic Response** | **Static crop ratios** (42 Straw, 12 Melon, ~7 Wheat) regardless of unlocked shops | **Dynamic crop ratios**: shifts up to 15 tiles to Wheat/Tomato/Carrot when Bakery/Pizza/Brunch unlock | **+30k to +45k revenue from shop-driven price stabilization** |
| **Worker Multi-Tasking** | Independent random or greedy closest task per worker | Coordinated conveyor routes (Workers dropping harvested crops to shed while on return trip from animal feeding) | Eliminates idle moves and shed congestion |
| **Late Game Liquidation** | Sells surplus incrementally | Hard-liquidation cutoff: liquidates all seeds/shed by Day 29 Turn 20 | Avoids stranded assets in shed at game end |

---

## 2. Dynamic Town Shop Intelligence

Every 3 days (Day 3, 6, 9, 12, 15, 18, 21, 24, 27), the game unlocks a new Town Shop drawn uniformly with replacement from 8 shops:

| Shop Type | Consumes Every 4 Turns | High Value Crop/Product |
|---|---|---|
| **BAKERY** | 1 Wheat, 1 Egg, 1 Milk | Wheat, Milk |
| **PIZZA_SHOP** | 1 Wheat, 1 Tomato, 1 Milk | Wheat, Tomato, Milk |
| **BRUNCH_SPOT** | 1 Wheat, 1 Egg, 1 Milk, 1 Strawberry | Strawberry, Milk, Wheat |
| **YARN_STORE** | 2 Wool | Wool |
| **ICE_CREAM_SHOP**| 1 Milk, 1 Strawberry | Strawberry, Milk |
| **PET_CAFE** | 1 Carrot, 1 Milk | Carrot, Milk |
| **SMOOTHIE_SHOP** | 1 Carrot, 1 Strawberry | Strawberry, Carrot |
| **FARMERS_MARKET** | 1 of all 8 products | All products |

### Strategic Rule Derived:
If **2+ PIZZA_SHOPS or BAKERIES** unlock by Day 9:
$\rightarrow$ Increase Wheat allocation from 7 tiles to 14 tiles.
If **2+ ICE_CREAM_SHOPS or SMOOTHIE_SHOPS** unlock:
$\rightarrow$ Maintain maximum Strawberry allocation (45 tiles).
If **YARN_STORE** unlocks:
$\rightarrow$ Shift animal ratio to 8 SHEEP / 6 COW to capitalize on 2x Wool consumption.
