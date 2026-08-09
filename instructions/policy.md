# Model Policy & Fallback System

This document outlines the strategy for the agent's core decision policy located in [policy.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/policy.py).

## Current State: Heuristic Policy Baseline
Currently, `policy.py` implements a highly optimized, rule-based heuristic strategy that achieves a baseline score of **~123k+**. 

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

- [ ] Write sequence-data parsing pipeline to convert raw replay JSONs into DT training tuples.
- [ ] Implement and train the Decision Transformer network offline.
- [ ] Export transformer weights to NumPy arrays.
- [ ] Implement NumPy-based self-attention forward pass in `policy.py` for zero-dependency inference.
