# Data Limitations & Observability Boundaries

> Phase 1 deliverable — what is and is not available from the replay corpus.

---

## 1. What Is Fully Observable in Replays

| Data | Source | Notes |
|---|---|---|
| Both players' board tiles at every step | `observation.farms[p].tiles` | Full 10×10 grid |
| Both players' money at every step | `observation.farms[p].money` | |
| Both players' unit positions | `observation.farms[p].farmer` + `hands` | |
| Both players' unlocked quadrants | `observation.farms[p].unlocked_quadrants` | |
| Both players' hired hands count | `observation.farms[p].hands` length | |
| Market prices and inventory | `observation.market` | Shared — same for both |
| Town shops | `observation.town.unlocked_shops` | Shared |
| All actions taken by both players | `steps[t][p].action` | Including market orders |
| Final scores | `rewards` | |
| Game seed | `info.seed` | |

---

## 2. What Is Hidden / Private

| Data | Visibility | Workaround |
|---|---|---|
| Shed contents | Private — only visible in observing player's obs | Reconstruct from BUY/SELL/HARVEST actions |
| Seeds held | Private | Reconstruct from BUY_SEED and PLANT actions |
| Per-unit inventory (what each hand carries) | Private | Infer from PICKUP/DROP/FEED/PLACE actions |
| Opponent's shed / seeds at any step | Fully hidden | Cannot reconstruct for opponent |

---

## 3. Action Interpretation Caveats

- **Actions are issued simultaneously** — player 0's action at step `t` does not have visibility into player 1's action at step `t`.
- **Invalid actions are silent no-ops** — a HIRE order when `money < fib(n)` is simply dropped; the action record still shows it.
- **Market order overflow** — only the first 10 orders are processed; the rest appear in the action record but have no effect.
- **Day 0 step 0** — the initial observation is the game's starting state; the actions at step 0 are always `{"farmer":["PASS"],"hands":[],"market":[]}` (setup turn). The real opening orders appear at step 1 (hour=1).

---

## 4. Self-Play Episodes

All 4 top players have self-play episodes (seed=0, same agent vs itself). These are included in the corpus with both players extracted, but they are lower quality data because:
- Both players follow identical decision trees → low variance in strategies observed.
- Self-play scores are systematically lower (mean ~60k vs ~90k vs real opponents) because neither agent adapts to the other.
- They are retained for temporal pattern analysis but flagged with `opponent_name == player_name`.

---

## 5. Corpus Coverage Gaps

| Potential Gap | Impact |
|---|---|
| Only 53–60 unique episodes per player | Some rare strategies may be under-sampled |
| No loss replays (by design — only top-4 players downloaded) | Cannot analyse failure modes or opponent-adaptive decisions |
| Display name aliasing (`THUNDER THUNDER` ↔ `ThunderThunder`) | Fixed in parser v1.1 |
| Missing `private` data for opponent | Opponent's shed/seed state must be inferred |

---

## 6. Temporal Resolution

The dataset captures every turn (720 per episode). For most analyses, sampling at:
- `hour == 0` — start-of-day state
- `hour == 12` — mid-day state (hands are active, orders processed)
- `hour == 23` — end-of-day state (pre-decay snapshot)

...is sufficient and avoids intra-day noise.
