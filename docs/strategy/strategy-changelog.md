# Strategy Changelog

> Versioned log of all accepted strategy changes from Phase2_v1 baseline.

---

## Version History

| Version | Date | Key Change | Δ Mean vs v1 | p-value |
|---|---|---|---|---|
| Phase2_v1 | 2026-08-07 | Baseline freeze | — | — |
| Phase2_v2 | 2026-08-13 | R5 wheat buy threshold `need > 0` → `need >= fed_animals` | +439 | 0.638 (noise in self-play; structural fix) |
| Phase2_v4 | 2026-08-15 | R5 + dropoff 3/5 + STRAW=44 + MELON reserve 0.80→0.50 | +5,404 | 0.000 |
| Phase2_v5 | 2026-08-15 | Clean re-baseline of v4 changes | +5,306 | 0.000 |
| Phase2_v6 | 2026-08-15 | Endgame wheat logic (plant cutoff, seed buffer, plant tier 1 from day 20) | +6,277 | 0.000 |
| Phase2_v7 | 2026-08-15 | Wheat buffer taper (release held wheat in final days) | +8,919 | 0.000 |
| Phase2_v8 | 2026-08-15 | Wheat buffer 3→2 days | +10,310 | 0.000 |
| Phase2_v9 | 2026-08-15 | Shed squeeze thresholds 85/65→75/50 | +13,124 | 0.000 |
| Phase2_v10 | 2026-08-15 | Remove price reserve entirely (sell-all) | +15,823 | 0.000 |
| Phase2_v11 | 2026-08-15 | Fertilize tier 2→1 | ~+17,859 | 0.000 |
| Phase2_v12 | 2026-08-15 | Rolled-back clean baseline (highest Kaggle score) | — | — |
| EXP-20260815-32 | 2026-08-15 | KaggriRatchet campaign (see experiments.jsonl) | — | — |
| EXP-20260815-51 | 2026-08-15 | KaggriRatchet campaign | — | — |
| EXP-20260815-55 | 2026-08-15 | KaggriRatchet campaign | — | — |
| EXP-20260815-59 | 2026-08-15 | KaggriRatchet campaign | — | — |
| **EXP-20260815-69** | **2026-08-15** | **KaggriRatchet campaign 4 composite mutations (+6,797 vs v11)** | **~+17,859** | **0.000** |

---

## Current Champion: EXP-20260815-69

Cumulative accepted changes from Phase2_v1:

1. **R5 wheat threshold** — `need > 0` → `need >= fed_animals`
2. **Dropoff thresholds** — carry≥10/6 → carry≥5/3 (intra-day wool/milk selling)
3. **`TARGET_STRAWBERRY`** — 42 → 35 (space savings, better per-tile revenue)
4. **MELON sell reserve** — 0.80 → removed (sell-all)
5. **Endgame wheat logic** — plant cutoff hour 22, min buffer 20, plant tier 1 from day 20
6. **Wheat buffer taper** — 3 days → 2 days → tapers to 0 at end
7. **Price reserve removed** — sell-all every turn
8. **Fertilize tier** — 2 → 1
9. **`TARGET_MELON`** — 12 → 9
10. **`LAND_UNLOCK_DAY`** — (7, 11) → (7, 9) (SW day 9)
11. **`CASH_FLOOR`** — 350 → 200

---

## Detailed Entries

### Phase2_v1 — Baseline (2026-08-07)
- Heuristic agent derived from mining of 72 leaderboard replays.
- Key parameters: `LAND_UNLOCK_DAY=(7,11)`, `TARGET_COW=8`, `TARGET_SHEEP=6`, `TARGET_STRAWBERRY=42`, `TARGET_MELON=12`, `CASH_FLOOR=350`.
- **Status**: Frozen historical control. `versions/Phase2_v1_policy.py`.

### EXP-20260815-69 — Current Champion (2026-08-15)
- **KaggriRatchet campaign**: 4 composite mutations accepted over 8 campaigns (51 experiments total, 4 KEEP / 47 REJECT in this run).
- **vs Phase2_v11**: Δmean +6,797 (p=0.000, d=0.78, n=32)
- **vs Phase2_v1**: Δmean ~+17,859 (p=0.000)
- **Archived at**: `versions/EXP-20260815-69_policy.py`

---

## Rejected Changes (Do Not Re-Test)

See [`docs/strategy/current-strategy.md`](current-strategy.md) for the confirmed no-op / regression table.
