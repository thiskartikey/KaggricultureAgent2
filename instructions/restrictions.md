# Agent Restrictions and Repository Rules

To ensure consistency and prevent corruption of files in this repository, all AI agents must strictly adhere to the following restrictions and rules.

## Critical Protections

> [!CAUTION]
> **DO NOT modify or delete anything inside `downloads/protected/`**
> This directory contains critical historical models, weights, or submission replays that cannot be recovered if deleted.

## Development & Code Guidelines

1. **Stdout Cleanliness**: The Kaggle environment communicates with the agent using standard input/output. Never add arbitrary print statements (`print()`) to files intended for submission (`ml_main.py` and `heuristic.py`). Only structured/expected stdout is allowed.
2. **Legacy RL Code**: The RL path (`env_wrapper.py`, `rl_inference.py`, `rl_weights.npz`) has been archived in `versions/`. Do not restore or use these unless explicitly reviving the RL model.

## File Cleanup Restrictions

- Do not leave screen recordings (`.webm`), logs (`.log`, `.txt`), or debugging scripts (`debug_*.py`, `fix*.py`) inside the root directory after a task is finished.
- Refer to `instructions/cleanup.md` for specific cleanup procedures.

## Verification Checklist

> [!IMPORTANT]
> Any code change must be validated locally using `python evaluate.py` to ensure no syntax errors or logic bugs are introduced before making a submission.
