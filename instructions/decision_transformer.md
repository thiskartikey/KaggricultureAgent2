# Decision Transformer — REMOVED

> **Status**: All DT/RL code was **removed** from `policy.py` during the health-check cleanup session.
> `policy.py` is now 880 lines with zero dead code (confirmed Δmean = 0, p = 1.000 vs the previous version).

## What Was Removed

The following symbols were present in `policy.py` as dead code and have been deleted:
- `DecisionTransformer` class (NumPy causal transformer implementation)
- `obs_to_vec` — state vectorizer
- `_farm_summary`, `_norm_shop` — DT helper functions
- `macro_to_farmer_op`, `resolve_farmer_op` — DT action helpers
- `get_dt_task` — DT task selector
- `DT_MODEL`, `STATE_HISTORY`, `ACTION_HISTORY`, `RETURN_HISTORY` — module-level globals
- Duplicate `CROPS`, `PRODUCTS`, `ANIMALS` definitions
- Duplicate `_nearest`, `_step_toward` definitions
- All 7 inline `import numpy as np` calls

## Why It Was Removed

1. None of these functions were reachable from `agent()` or `_agent()` (confirmed by AST analysis).
2. The dead block contained 7 inline `import numpy` calls that could trip submission linters.
3. The duplicate `CROPS` and `PRODUCTS` name bindings shadowed the live ones.
4. Removing 471 lines shrank the file by 35% and makes the mutator's Tier 2 function-replacement more reliable.

## If You Want to Revisit a DT Approach

Start from scratch. The old DT code was a skeleton that never influenced gameplay.
The weights file (`rl_weights.npz`) is also no longer needed.

The correct approach would be:
1. Design a state representation for the current 880-line heuristic's decision points.
2. Train offline using the `replays/` corpus via `src/replay_analysis/`.
3. Wire it in as a **replacement** for a specific decision (e.g., task assignment), A/B test it
   via `src/autoresearch/evaluator.py` against the champion.
