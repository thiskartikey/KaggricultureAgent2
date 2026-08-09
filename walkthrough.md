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

### 5. NumPy Decision Transformer
- Implemented a complete, zero-dependency `DecisionTransformer` inference class using causal self-attention directly inside `policy.py`. It is ready to consume offline-trained PyTorch weights once exported to `.npz`.

## Local A/B Test Results

We evaluated the final clean policy (Routing + Replanting + Melon Reserve) against the baseline `v7` heuristic:
```
=== ml_main.py  vs  heuristic_v7.py ===
  ml_main.py           mean   111,923   median   115,744
  heuristic_v7.py      mean   100,856   median   102,162
  diff +11,067   ml_main.py wins 20/20
  paired t=+9.87  p=0.000  ->  SIGNIFICANT
```
The optimized logic beats the v7 baseline by **+11,067 points** on average with a 100% win rate (20/20 wins).
