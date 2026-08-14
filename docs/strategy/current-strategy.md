# Current Strategy Documentation

> Baseline A1 heuristic as of Phase2_v1 freeze.

The current production strategy is fully documented in [`docs/architecture/current-agent.md`](../architecture/current-agent.md).

Key parameters that differ from the empirically-derived optimal:

| Parameter | Current (Phase2_v1) | Optimal (empirical) | Gap ID |
|---|---|---|---|
| NE unlock day | 7 | 6 | GAP-001 |
| SW unlock day | 11 | 10 | GAP-001 |
| Target pastures (mid) | 12 | 14 | GAP-002 |
| Day 0 hires | 5 | 4 | GAP-006 |
| Target cows | 8 | 9 | GAP-005 |
| Target sheep | 6 | 5 | GAP-002 |

See [`docs/strategy/strategy-gaps.md`](strategy-gaps.md) for full priority-scored analysis.
