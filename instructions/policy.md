# Model Policy & Fallback System

This document outlines the strategy for the agent's core decision policy located in [policy.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/policy.py).

## Current State: Optimized Heuristic Baseline

Currently, `policy.py` implements a highly optimized, rule-based heuristic strategy that achieves a baseline score of **~111k+ / 115k+** median.

### Heuristic Features Implemented:
- **Routing Efficiency:** Global priority scoring favoring local (`d=0`) tasks over walking across tiles.
- **Replanting Buffer:** Pre-allocating and reserving seeds for crops harvesting in the same turn to achieve zero fallow time.
- **Melon Reserve:** Restricting Melon sales to protect against self-inflicted price dumping.

### Experimented and Discarded:
- **Goose Setup:** Tested building 2 Coops and buying 2 Geese. Evaluation showed this significantly reduced performance by `-7,085` points due to high building costs and low margins, so it has been reverted.

As we transition to the **Decision Transformer** (DT) model:
1. The heuristic rules inside `policy.py` will serve as the safe **fallback layer** (handles low-level action validation and emergency cash/wage management).
2. The DT model will serve as the **macro planner**, predicting high-level sequences of actions (worker allocation, quadrant purchases, crop rotations).

## Moving to Decision Transformer

The new learning policy will model decision-making as sequence modeling over state-action history:

```
Sequence Input: [R_0, S_0, A_0, R_1, S_1, A_1, ... R_t, S_t, A_t] -> Predict -> A_{t+1}
```

- **R (Return-to-go)**: Target reward (cash at day 30) remaining to achieve.
- **S (State)**: Observation vector extracted via our wrapper.
- **A (Action)**: Macro action commands executed by farmers and market transactions.

## Development Checklist

- [x] Implement NumPy-based self-attention forward pass in `policy.py` for zero-dependency inference (`DecisionTransformer` class).
- [ ] Refine sequence-data parsing pipeline to convert raw replay JSONs into DT training tuples.
- [ ] Implement and train the Decision Transformer network offline.
- [ ] Export transformer weights to `.npz` format matching expectations of the `DecisionTransformer` class.
