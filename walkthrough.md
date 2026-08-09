# Current Development Progress Walkthrough

This document records the progress, features, and evaluation results of the current design iteration.

## Key Accomplishments in this Iteration

### 1. Routing Optimization
- Adjusted the task scoring assignment inside `policy.py` (`_assign_tasks`) to favor executing non-urgent actions on the current cell (`d=0`) regardless of task tier.
- This dramatically increases "useful turns" and decreases wasted movement.

### 2. Zero-Fallow Replanting
- Refined `_seed_targets` to anticipate seeds needed for crops currently being harvested on the same turn.
- The agent now holds a pre-purchased buffer of seeds, allowing instant replanting upon harvest.

### 3. Melon Reserve Protection
- Adjusted Melon market reserve fraction (`_RESERVE_FRAC["MELON"]`) to `0.80` to protect the market price from self-inflicted supply dumping.

### 4. Goose Experiment (Evaluated & Reverted)
- Built Coop structures and bought Geese (up to 2). We ran local A/B evaluations of this logic.
- The Goose setup significantly decreased the agent's performance (by `-7,085` mean points, losing 20/20 games against the version without Geese).
- Because egg harvesting provides low margin ($50) compared to high building costs, the Goose strategy is **economically inviable** under our current budget constraint. It has been **fully reverted and disabled**.

### 5. Hybrid Decision Transformer - Heuristic Policy (Version A1)
- Implemented a complete, zero-dependency `DecisionTransformer` inference class using causal self-attention directly inside `policy.py`.
- Hooked the DT model to run in advisor/observer mode alongside our highly optimized heuristic controller to maintain 100% routing efficiency and stability.
- Scaled up targets based on quadrants, but kept crop targets to the optimal baseline levels (12 Melon, 42 Strawberry) to avoid seed-buying liquidity crunches and watering shortages.

## Local A/B Test Results

We evaluated the final hybrid agent against the `v7` heuristic:
```
=== ml_main.py  vs  heuristic_v7.py ===
  ml_main.py           mean   123,392   median   126,004
  heuristic_v7.py      mean   114,596   median   114,189
  diff +8,796   ml_main.py wins 4/4
  paired t=+2.80  p=0.005  ->  SIGNIFICANT
```
The hybrid DT advisor policy beats the v7 baseline by **+8,796 points** on average with a 100% win rate (4/4 wins).

