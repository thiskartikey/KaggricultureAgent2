# Current Agent Architecture Audit

> Phase 0 deliverable — authoritative description of `KaggricultureAgent` as it stands today.

---

## 1. Entry Points

### `ml_main.py` (submission entry point)
```
ml_main.agent(obs, config) → policy.agent(obs, config)
```
- Thin shim that appends the agent directory to `sys.path` and delegates to `policy.py`.
- This is the file that is executed inside the Kaggle sandbox.

### `main.py` (legacy / development entry point)
- Contains a self-contained v2 heuristic **plus** an optional RL/DT path loaded from `rl_weights.npz`.
- The RL path (`_RL_POLICY`) always falls back silently to the heuristic when weights are absent.
- The `DecisionTransformer` class is present but effectively dead code in production — `rl_weights.npz` is not shipped in the submission tarball.
- **Not used in production submissions.** Only `policy.py` matters.

---

## 2. `policy.py` — Strategy Engine (1,406 lines)

### 2.1 Call Graph
```
agent(obs)
  └── _agent(obs, total_days=30)
        ├── _scan(me, day, total_days)          → scan dict
        ├── _free_cells(me, board)              → list[(x,y)]
        ├── _make_market_orders(obs, …, scan)   → list[order]
        ├── _build_tasks(scan, me, …)           → list[task]
        ├── _assign_tasks(positions, tasks, …)  → dict[unit_idx → task]
        └── _unit_op(pos, task, …)              → [op, …args]
```

### 2.2 `_scan(me, day, total_days)` — Farm State Scanner
Returns a dict with lists of tile coordinates grouped by urgency:

| Key | Contents | Notes |
|---|---|---|
| `service` | Occupied pastures with unfed animals | Tier-0 — starvation risk |
| `water` | Plants that will die tonight if unwatered | Tier-0 |
| `service_soon` | Occupied pastures, fed but needs harvest/care/fertilizer | Tier-1 |
| `water_soon` | Plants safe today but need water tomorrow | Tier-3 |
| `harvest_crop` | Ready-to-harvest plants | Tier-1 |
| `fertilize` | Ongoing crops in yield window without active fertilizer | Tier-2 |
| `weeds` | Weed tiles to clear | Tier-4 |
| `structures_empty` | Unoccupied pastures/coops | Used by build_tasks |
| `feed` | Unfed animals (subset of service) | Used for wheat routing |

### 2.3 `_make_market_orders(obs, …)` — Market Order Builder
Processes up to 10 market orders per turn. Rules in priority order:

| Rule | Description |
|---|---|
| **R1** | Day 0 hour 0: hard-coded opening blitz (5 HIRE, 2 COW, 2 SHEEP, 11 MELON, 7 WHEAT seeds, 8 WHEAT feed) |
| **R2** | Sell produce every turn; hold wheat for animal feed; price-floor gated |
| **R3** | Re-hire crew every morning (`target_hands(day)` → 5/3/8/13 by phase) |
| **R4** | Buy land on schedule: NE day 7 (1000), SW day 11 (2000); SE never |
| **R5** | Maintain wheat feed reserve: buy if `fed_animals × 3 > wheat_in_shed+inv` |
| **R6** | Buy animals to fill empty pastures: 8 COW then 6 SHEEP |
| **R7** | Buy seeds: fill free tiles with MELON (if ≥13 days left), STRAWBERRY, WHEAT |

### 2.4 `_build_tasks(scan, me, …)` — Task List Builder
Constructs a flat task list that the dispatcher consumes:

1. `service` / `service_soon` tasks from scan
2. `water` / `water_soon` tasks
3. `harvest_crop` tasks
4. `place_animal` — move animals from shed onto empty pastures
5. `build_pasture` — up to `target_pastures(day)` (6 → 12 → 14 by phase)
6. `build_coop` — always 0 (no coops in blueprint)
7. `plant` — sow free tiles in shed-proximity order
8. `fertilize` tasks
9. `weed` tasks

### 2.5 `_assign_tasks(positions, tasks, …)` — Sticky Greedy Dispatcher
- Tier-priority × distance scoring: `score = tier × 1000 + manhattan_distance`
- Workers at their tile (d=0) get a −1500 bonus to stay and finish vs. being redirected.
- Sticky claims: a unit's previous-turn assignment is honoured if the task still exists, preventing oscillation.
- Feed-routing override: units carrying wheat are preferentially assigned to unfed animals.

### 2.6 `_unit_op(pos, task, …)` — Per-Unit Action Resolver
Resolves a task into a single action op for one turn:
- `service/service_soon`: runs `FEED → HARVEST → COLLECT_FERTILIZER → CARE` sequentially in one visit.
- `place_animal`: fetches animal from shed, then `PLACE`.
- `fertilize`: fetches fertilizer from shed, then `FERTILIZE`.
- All others: `step_toward(cell)` until adjacent, then the terminal op.

### 2.7 Strategy Blueprint Constants (empirically mined)

| Constant | Value | Source |
|---|---|---|
| `TARGET_COW` | 8 | Replay mining |
| `TARGET_SHEEP` | 6 | Replay mining |
| `TARGET_STRAWBERRY` | 42 | Replay mining |
| `TARGET_MELON` | 12 | Replay mining |
| `LAND_UNLOCK_DAY` | (7, 11) | Replay mining |
| `target_hands` | 5/3/8/13 | Replay mining |
| `CASH_FLOOR` | 350 | Feed safety buffer |

### 2.8 Disconnected / Dead Code

| Symbol | Status | Notes |
|---|---|---|
| `DecisionTransformer` | Dead | `rl_weights.npz` not in submission tarball |
| `obs_to_vec` | Dead | Only used by DT path |
| `macro_to_farmer_op` / `resolve_farmer_op` | Dead | Only used by DT path |
| `get_dt_task` | Dead | DT always returns `None` |
| `STATE_HISTORY / ACTION_HISTORY / RETURN_HISTORY` | Dead | Appended every turn but never used |
| `DT_MODEL` | Always `None` in production | `rl_weights.npz` absent |

---

## 3. Simulation & Testing Harness

### `evaluate.py`
- **Purpose**: Multi-game A/B evaluation to remove seat bias and seed variance.
- **Protocol**: `N` seeds × 2 seats = `2N` games total.
- **Output**: Mean score, win rate, paired *t*-statistic and *p*-value.
- **Parallelism**: `ProcessPoolExecutor`, default workers = CPU count.
- **Usage**: `python evaluate.py policy.py versions/Phase2_v1_policy.py --games 8`

### `versions/Phase2_v1_policy.py`
- **Frozen control baseline** (identical line count to `policy.py` at the time of freeze).
- All strategy experiments must be measured against this file.
- Gate: any candidate must beat it with `p < 0.05` over ≥16 games.

---

## 4. Submission Build

### `build_submission.py`
- Bundles `main.py`, `ml_main.py`, `policy.py` into `ml_submission.tar.gz`.
- **No external ML dependencies** may be imported in submitted files (PyTorch, TensorFlow, Gym are all absent from `policy.py`).

---

## 5. Key Invariants for Strategy Engineers

1. **Hands vanish nightly** — re-hire from scratch every day; crew cost is trivial.
2. **Planting day counts as unwatered** — a plant sown at hour ≥ 21 will die overnight.
3. **Shed cap = 100** — overflow is silently discarded at end-of-day.
4. **10 market orders per turn** — excess orders are silently dropped.
5. **Only `WHEAT` and `FERTILIZER` can be purchased via `BUY_PRODUCT`** — all produce is sell-only.
6. **`CARE` bonus only accrues when the animal is also fed that day** — feed must precede care.
