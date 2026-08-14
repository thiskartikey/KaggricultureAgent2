# Replay System Technical Design

> Phase 0 deliverable — technical design of the parser pipeline and data model.

---

## 1. Raw Replay Format

Each replay is a JSON file at `replays/<PlayerFolder>/episode-<ID>-replay.json`.

### Top-Level Structure
| Field | Type | Description |
|---|---|---|
| `id` | string | UUID of the episode |
| `info.EpisodeId` | int | Numeric episode ID |
| `info.TeamNames` | list[str] | Display names of the two agents |
| `info.seed` | int or null | RNG seed used |
| `rewards` | list[float] | Final scores for player 0 and 1 |
| `statuses` | list[str] | `"DONE"` for both when game completes |
| `steps` | list[list[dict]] | 720 entries (one per turn); each inner list has 2 player dicts |

### Per-Step Player Dict
```json
{
  "action":      { "farmer": [...], "hands": [[...]], "market": [[...]] },
  "observation": { "day": 6, "hour": 0, "step": 144, "player": 0,
                   "farms": [...], "market": {...}, "town": {...},
                   "private": { "shed": {...}, "seeds": {...}, "inventories": [...] } },
  "reward":      57576.0,
  "status":      "ACTIVE",
  "info":        {}
}
```

### Key Observability Notes
| Field | Visibility | Notes |
|---|---|---|
| `farms[p].tiles` | **Public** | Full board for both players |
| `farms[p].money` | **Public** | Both players' cash visible |
| `farms[p].unlocked_quadrants` | **Public** | Both players |
| `private.shed` | **Private** | Only own player |
| `private.seeds` | **Private** | Only own player |
| `private.inventories` | **Private** | Only own player |
| `market` | **Shared** | Same object for both players |
| `town.unlocked_shops` | **Shared** | Same for both players |

---

## 2. Canonical Data Pipeline

```
replays/<Player>/*.json
       │
       ▼
src/replay_analysis/parser.py
  parse_replay(path, corpus_player)
  ├── Alias resolution (THUNDER THUNDER → ThunderThunder)
  ├── Self-play detection (both players same resolved name)
  ├── Per-step extraction:
  │     _count_tile_crops(tiles)      → crop_counts dict
  │     _count_tile_animals(tiles)    → animal_counts + structures dicts
  │     _summarise_action(action)     → ActionsSummary
  └── Yields CanonicalTurn objects
       │
       ▼
data/processed/canonical_turns.csv
  147,600 rows × 24 columns
```

### Name Alias Map
| Display Name | Folder / Corpus Key |
|---|---|
| `THUNDER THUNDER` | `ThunderThunder` |

---

## 3. Corpus Statistics (post-fix)

| Player | Replays | Episodes | Rows | Win Rate | Mean Score |
|---|---|---|---|---|---|
| Ezzzzzekki | 91 | 44 unique | 31,680 | 86.4% | 89,666 |
| GiovanniCR | 89 | 48 unique | 34,560 | 87.5% | 90,336 |
| HealthStone | 120 | 60 unique | 43,200 | 91.7% | 90,802 |
| ThunderThunder | 113 | 53 unique | 38,160 | 96.2% | 91,290 |
| **Total** | **413** | **205** | **147,600** | — | — |

> Note: Multiple replays per episode exist because the same game may appear in multiple player folders when both were top-4.

---

## 4. Schema — `CanonicalTurn`

Defined in `src/replay_analysis/schema.py`.

| Column | Type | Description |
|---|---|---|
| `episode_id` | int | Numeric episode ID |
| `step` | int | Turn index 0–719 |
| `day` | int | Day 0–29 |
| `hour` | int | Hour within day 0–23 |
| `player_name` | str | Kaggle display name |
| `player_index` | int | 0 or 1 |
| `opponent_name` | str | Opponent display name |
| `money` | float | Player's bank balance |
| `unlocked_quadrants` | JSON str | List of unlocked quad names |
| `num_hands` | int | Hired hands present this step |
| `crop_counts` | JSON str | Dict of crop → tile count |
| `animal_counts` | JSON str | Dict of animal → count |
| `structures` | JSON str | Dict of PASTURE/COOP → count |
| `actions_summary` | JSON str | ActionsSummary counts |
| `market_orders` | JSON str | List of market orders issued |
| `market_prices` | JSON str | Market prices this turn |
| `market_inventory` | JSON str | Market inventory this turn |
| `town_shops` | JSON str | Unlocked shops |
| `shed` | JSON str | Private shed contents |
| `seeds` | JSON str | Private seed counts |
| `final_score` | float | End-of-game reward |
| `final_reward` | float | Normalised reward |
| `corpus_player` | str | Folder the replay came from |
| `won` | bool | Whether this player won |

---

## 5. Running the Pipeline

```bash
# Regenerate the canonical dataset
python -m src.replay_analysis.parser --input replays/ --output data/processed/

# Run parser tests
python -m pytest tests/test_replay_parser.py -v
```
