# Decision Transformer (DT) Strategy

This document details the offline learning methodology to replace traditional RL with a sequence-modeling Decision Transformer.

## Architecture Overview

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
