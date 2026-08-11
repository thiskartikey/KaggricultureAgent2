# Decision Transformer (DT) Strategy — DISCONNECTED (2026-08-12)

> [!WARNING]
> This document describes an experiment in offline learning methodology. **The DT is currently disconnected from gameplay** (see [[policy.md]]). The code, weights, and dataset remain archived for reference, but `dt_task` is computed and immediately discarded before task assignment runs. A/B testing (2026-08-12) confirmed zero impact: p=1.000, identical scores.
>
> If you want to wire the DT back in, see the "Next Steps" section below.

## Architecture Overview (Reference)

Traditional Reinforcement Learning (like PPO) models the policy as $P(a|s)$. The **Decision Transformer** models the policy as a sequence model conditioned on desired future returns (returns-to-go):

\[
P(a_t | s_1, a_1, R_1, \dots, s_t, a_t, R_t)
```
  Returns-to-go (R_t) ──┐
  Observations   (S_t) ──┼──> [ Linear Projection ] ──> [ GPT-style Causal Transformer ] ──> [ Action Predictor ] ──> Action (A_t)
  Actions        (A_t) ──┘
```
\]

By framing RL as sequence modeling, the model learns directly from expert play histories without needing complex value function estimation or exploration during training.

## Replay Dataset (`downloads/training/`)

We have **73 top-player replays** (2.2 GB of JSON logs) representing expert runs.
1. **Trajectories**: Extract episodes where the player scored $\ge 100k$.
2. **State representation**: Map observation dictionaries to a fixed-size state vector $s_t$ (cash, day, hour, farm structures, crops status).
3. **Action representation**: Map farmer commands and market transactions to discrete tokens $a_t$.
4. **Returns-to-go**: Initialize $R_1$ with the final episode cash reward ($100k - 150k$), and decrement it at each step by any cost incurred:
   \[
   R_t = \text{Final Cash} - \text{Cash accrued up to step } t
   \]

## Inference (NumPy implementation)

To maintain a zero-dependency, ultra-lightweight submission:
1. **Offline Training**: Train the PyTorch model offline (e.g. on Kaggle Notebook GPU).
2. **Weight Export**: Save weight matrices for projections, multi-head self-attention, layer normalization, and feed-forward MLPs into a `.npz` file.
3. **NumPy Implementation**: Implement the causal self-attention forward pass in pure NumPy. Since sequence lengths during active inference are short (sliding context window of size $K \approx 20$), inference time will be extremely fast ($< 10$ ms), well below the 1-second Kaggle act limit.

## Why It's Disconnected

During development, `dt_task` was computed at `policy.py` ~line 1036 but then immediately discarded via `dt_assigned_task = None` at line 1044, before the tier-based task assignment runs. The assumption was that the DT would generate high-level macro guidance (e.g., "prioritize harvest over water"), but:

1. **The task assignment engine already does this** via tier-based ordering (service tier 0, harvest tier 1, plant tier 2, etc.). The DT token was redundant.
2. **Testing showed no impact** (2026-08-12 A/B, 16 games, p=1.000): A1 with DT weights vs without were identical to the dollar. The DT was a no-op.
3. **The heuristic is already optimal** at ~111k mean. Incremental gains would require re-training on the current Kaggle meta, not offline expert data.

## If You Want to Wire It Back In

1. **Find the disconnection point** in `policy.py` near line 1044: uncomment or restore the lines that assign `dt_assigned_task = dt_task`.
2. **Test it A/B** against A1 baseline with ≥8 seeds x 2 seats (16 games, p<0.05 bar) before claiming improvement.
3. **Verify weights load** on Kaggle (the current cwd-relative path breaks on Kaggle; use `__file__`-relative pathing with fallback).
4. **Retrain if needed**: The 73 replays in `downloads/training/` are from top players ~2026-08-07. Current Kaggle meta may differ; if testing shows the DT hurts, retraining on newer replays would be needed.
