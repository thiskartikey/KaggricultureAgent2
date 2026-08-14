# Strategy Changelog

> Phase 12 deliverable — versioned log of all accepted strategy changes.

---

## Version History

| Version | Date | Description | Δ Mean Score | p-value |
|---|---|---|---|---|
| Phase2_v1 | 2026-08-07 | Baseline freeze — top-player blueprint from 72 replays | — | — |
| Phase2_v2 | TBD | Land unlock day correction (NE d6, SW d10) | TBD | TBD |
| Phase2_v3 | TBD | Pasture target 14 + earlier ramp | TBD | TBD |
| Phase2_v4 | TBD | Labour schedule recalibration | TBD | TBD |

---

## Detailed Entries

### Phase2_v1 — Baseline (2026-08-07)
- **Description**: Heuristic agent derived from mining of 72 leaderboard replays.
- **Key parameters**: `LAND_UNLOCK_DAY=(7,11)`, `TARGET_COW=8`, `TARGET_SHEEP=6`, `target_hands` returns 5/3/8/13.
- **Status**: Frozen control. Never modify. Referenced as `versions/Phase2_v1_policy.py`.

---

> **Template for future entries:**
>
> ### Phase2_vN — Description (YYYY-MM-DD)
> - **Hypothesis**: ...
> - **Mutation**: `policy.py` lines X–Y changed.
> - **Test**: `python evaluate.py policy.py versions/Phase2_v1_policy.py --games 8`
> - **Results**: Policy mean=X, Baseline mean=Y, Δ=+Z, t=T, p=P, win rate=W/16
> - **Verdict**: ACCEPT / REJECT
> - **Promoted to**: `versions/Phase2_vN_policy.py` (if accepted)
