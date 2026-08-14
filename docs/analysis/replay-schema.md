# Replay JSON Schema — Exact Structure Documentation

> Phase 1 deliverable — ground-truth mapping of every field in raw replay JSONs.

---

## 1. File Naming Convention
```
replays/<CorpusPlayer>/episode-<EpisodeId>-replay.json
```

---

## 2. Top-Level Fields

```json
{
  "id":             "f3bc671e-943d-11f1-86ac-0242ac130204",  // UUID
  "name":           "kaggriculture",
  "title":          "Kaggriculture",
  "version":        "0.1.0",
  "module_version": "1.32.6",
  "schema_version": 1,
  "description":    "Advanced farming simulation...",
  "rewards":        [57576.0, 57695.0],          // final scores [p0, p1]
  "statuses":       ["DONE", "DONE"],
  "info": {
    "EpisodeId":    91449177,
    "TeamNames":    ["Ezzzzzekki", "Ezzzzzekki"], // display names
    "seed":         0,                            // RNG seed (null = random)
    "Agents":       [{"Name": ..., "ThumbnailUrl": null}, {...}],
    "LiveVideoPath": null
  },
  "configuration": {
    "actTimeout": 1, "boardSize": 10, "episodeSteps": 720,
    "farmHandCostMult": 1, "maxMarketOrdersPerTurn": 10,
    "runTimeout": 1200, "seed": null, "shedCapacity": 100,
    "startingMoney": 3000, "townCenterSellInterval": 24,
    "townShopSellInterval": 4, "townShopUnlockInterval": 3,
    "turnsPerDay": 24, "weedSpawnChance": 0.005
  },
  "steps": [...]   // list of 720 step records
}
```

---

## 3. Step Record Structure

`steps[t]` is a **list of 2 player dicts**, one per player:

```json
[
  { /* player 0 at step t */
    "action": { "farmer": ["PASS"], "hands": [], "market": [["HIRE"], ...] },
    "observation": { /* see §4 */ },
    "reward":  57576.0,   // cumulative score (final value set only at last step)
    "status":  "ACTIVE",  // or "DONE"
    "info":    {}
  },
  { /* player 1 at step t */ }
]
```

> **Action timing**: `steps[t][p]['action']` is the action player `p` took **at** step `t`.
> The observation in `steps[0][p]` represents the initial state; the first non-trivial
> market orders appear at `steps[1]` (hour=1).

---

## 4. Observation Fields

```json
{
  "player": 0,
  "step":   1,
  "day":    0,
  "hour":   1,
  "remainingOverageTime": 1.0,

  "farms": [
    {
      "money":               2008.0,
      "hires_today":         4,
      "farmer":              [4, 4],     // [x, y]
      "hands":               [[4,4],[4,4],[4,4],[4,4]],
      "unlocked_quadrants":  ["NW"],
      "tiles": [ /* 10×10 array — see §5 */ ]
    },
    { /* player 1 farm — same structure, fully public */ }
  ],

  "private": {             // only non-empty for the observing player
    "shed":        {"WHEAT": 5, "COW": 1, "SHEEP": 4, ...},
    "seeds":       {"WHEAT": 5, "MELON": 5, ...},
    "inventories": [{}, {}, {}, {}, {}]   // one dict per unit (farmer + hands)
  },

  "market": {
    "prices":    {"WHEAT": 32, "MELON": 256, "MILK": 169, ...},
    "inventory": {"WHEAT": 9950, "MELON": 10000, ...}
  },

  "town": {
    "unlocked_shops": ["PET_CAFE"]   // may be empty or contain duplicates
  }
}
```

---

## 5. Tile Types

| Value | Kind | Fields Present |
|---|---|---|
| `null` | Empty unlocked tile | — |
| `"LOCKED"` | Locked quadrant tile | — |
| `{"kind":"PLANT",...}` | Growing crop | `crop`, `planted_day`, `watered_today`, `consecutive_unwatered`, `yield_units`, `max_lifespan_step`, `fertilized_until_day` |
| `{"kind":"WEED"}` | Weed | — |
| `{"kind":"PASTURE",...}` | Pasture (empty or occupied) | `animal` (str or null), `placed_day`, `yield_units`, `fed_today`, `consecutive_unfed`, `cared_today`, `fertilizer_available`, `pending_care_bonus` |
| `{"kind":"COOP",...}` | Coop | Same as PASTURE |

---

## 6. Quadrant Layout

```
(0,0)──────(4,0)│(5,0)──────(9,0)
  NW  (5×5)     │     NE (5×5)
(0,4)──────(4,4)│(5,4)──────(9,4)
──────────────────────────────────
(0,5)──────(4,5)│(5,5)──────(9,5)
  SW  (5×5)     │     SE (5×5)
(0,9)──────(4,9)│(5,9)──────(9,9)
```

Shed-adjacent tiles (where DROP/PICKUP work): `(4,4)`, `(5,4)`, `(4,5)`, `(5,5)`.

---

## 7. Land Costs

| Quadrant | BUY_LAND cost |
|---|---|
| NE (2nd) | 1,000 |
| SW (3rd) | 2,000 |
| SE (4th) | 4,000 |
