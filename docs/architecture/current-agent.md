# Current Agent Architecture

> Authoritative description of `policy.py` as it stands today (champion: `EXP-20260815-69`).

---

## 1. Entry Point

### `ml_main.py` (submission entry point)
```
ml_main.agent(obs, config) → policy.agent(obs, config)
```
- Thin shim that delegates to `policy.py`.
- This is the file executed inside the Kaggle sandbox.

---

## 2. `policy.py` — Strategy Engine (880 lines)

All DT/RL dead code was removed in the health-check cleanup session. The file is pure heuristic.

### 2.1 Call Graph
```
agent(obs, config)
  └── _agent(obs, total_days)
        ├── _scan(me, day, total_days)              → scan dict
        ├── _free_cells(me, board)                  → list[(x,y)], sorted by shed proximity
        ├── _make_market_orders(obs, …, scan)        → list[order]  (R1–R7)
        ├── _build_tasks(scan, me, private, …)       → list[task]
        ├── _assign_tasks(positions, tasks, …)       → dict[unit_idx → task]
        └── _unit_op(pos, task, …)                  → [op, …args]
```

### 2.2 `_scan` — Farm State Scanner

| Key | Contents | Tier |
|---|---|---|
| `service` | Occupied pastures with unfed animals | 0 |
| `water` | Plants that will die tonight if unwatered | 0 |
| `service_soon` | Occupied pastures, fed but needs harvest/care/fertilizer | 1 |
| `harvest_crop` | Ready-to-harvest plants | 1 |
| `fertilize` | Ongoing crops in yield window without active fertilizer | 1 |
| `water_soon` | Plants safe today but need water tomorrow | 3 |
| `weeds` | Weed tiles to clear | 4 |
| `structures_empty` | Unoccupied pastures/coops | — |
| `feed` | Unfed animals (subset of service) | wheat routing |

### 2.3 `_make_market_orders` — Market Order Builder (R1–R7)

| Rule | Description |
|---|---|
| **R1** | Day 0 hour 0: hard-coded opening blitz (5 HIRE, 2 COW, 2 SHEEP, 11 MELON seeds, 7 WHEAT seeds, 8 WHEAT feed) |
| **R2** | Sell all produce every turn; hold wheat = 2-day feed buffer (tapers to 0 at game end) |
| **R3** | Re-hire crew every morning (target: 5/3/8/13/10 by phase) |
| **R4** | Buy land: NE day 7 ($1k), SW day 9 ($2k); SE never |
| **R5** | Buy wheat when deficit ≥ `fed_animals` (≥1 full day short) |
| **R6** | Buy animals to fill empty pastures: 8 COW then 6 SHEEP then 0 GOOSE |
| **R7** | Buy seeds: MELON (≥13 days left), STRAWBERRY (≥13 days), WHEAT (≥3 days) |

### 2.4 `_build_tasks` — Task List Builder

1. `service` / `service_soon` tasks
2. `water` / `water_soon` tasks
3. `harvest_crop` tasks
4. `place_animal` — animals from shed onto empty pastures
5. `build_pasture` — up to `target_pastures(day)`: 6 → 12 → 14
6. `build_coop` — always 0 (no GOOSE in blueprint)
7. `plant` — sow free tiles in shed-proximity order
8. `fertilize` tasks
9. `weed` tasks

### 2.5 `_assign_tasks` — Sticky Greedy Dispatcher

- Score: `tier × 1000 + manhattan_distance`
- Workers at their tile (d=0) get a −1500 bonus to stay and finish.
- Sticky claims: previous-turn assignment honoured if task still exists.
- Feed-routing: only wheat-carrying units assigned to hungry animals.
- Endgame (day ≥ 20): `plant` promoted to tier 1.

### 2.6 `_unit_op` — Per-Unit Action Resolver

- `service/service_soon`: FEED → HARVEST → COLLECT_FERTILIZER → CARE in one visit.
- `place_animal`: fetch from shed, then PLACE.
- `fertilize`: fetch FERTILIZER from shed, then FERTILIZE.
- All others: step_toward(cell) until at tile, then terminal op.

### 2.7 Blueprint Constants (Champion Values)

| Constant | Value |
|---|---|
| `TARGET_COW` | 8 |
| `TARGET_SHEEP` | 6 |
| `TARGET_GOOSE` | 0 |
| `TARGET_STRAWBERRY` | 35 |
| `TARGET_MELON` | 9 |
| `TARGET_PASTURE_BY_DAY` | ((11,14),(7,12),(0,6)) |
| `LAND_UNLOCK_DAY` | (7, 9) |
| `CASH_FLOOR` | 200 |
| `SHED_CAP` | 100 |

### 2.8 TASK_TIER (Current)

```python
TASK_TIER = {
    "service":       0,
    "water":         0,
    "harvest_crop":  1,
    "place_animal":  1,
    "service_soon":  1,
    "fertilize":     1,   # was 2; raised in EXP-20260815-15
    "build_pasture": 2,
    "build_coop":    2,
    "plant":         2,   # dynamically raised to 1 when day >= 20
    "water_soon":    3,
    "weed":          4,
    "dropoff":       4,
}
```

---

## 3. Evaluation & Autoresearch

### `src/autoresearch/evaluator.py`
- **Stages**: 0 (AST/invariant gate) → 1 (4 games, Δ < −2000 → reject) → 2 (16 games, Δ ≤ 0 → reject) → 3 (32 games, champion gate: p < 0.05, d > 0.20, Δ > 0, worst-case drop ≤ 5%)
- **Usage**: `from src.autoresearch.evaluator import evaluate; evaluate("candidate.py", "baseline.py")`

### `src/autoresearch/controller.py` (KaggriRatchet)
```bash
python3 -m src.autoresearch.controller --step          # one iteration
python3 -m src.autoresearch.controller --loop --max-exp 10
python3 -m src.autoresearch.controller --test-ratchet  # git integrity check
```

### `versions/EXP-20260815-69_policy.py`
- **Current champion baseline** — use as `baseline` in any evaluation.
- `versions/Phase2_v1_policy.py` — original A1 baseline (historical reference only).

---

## 4. Key Invariants for Strategy Engineers

1. **Hands vanish nightly** — re-hire from scratch every day; crew cost is trivial.
2. **Planting day counts as unwatered** — a plant sown at hour > 20 will die overnight.
3. **Shed cap = 100** — overflow is silently discarded at end-of-day.
4. **10 market orders per turn** — excess orders are silently dropped.
5. **Only `WHEAT` and `FERTILIZER` can be purchased via `BUY_PRODUCT`**.
6. **`CARE` bonus only accrues when the animal is also fed that day**.
7. **Sell-all beats price reserves** — holding for a better price costs more than the price difference (shed overflow penalizes holding).
