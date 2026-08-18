# Agent Restrictions and Repository Rules

To ensure consistency and prevent corruption of files in this repository, all AI agents must strictly adhere to the following restrictions and rules.

## Critical Protections

> [!CAUTION]
> **DO NOT modify or delete anything inside `downloads/protected/`**
> This directory contains critical historical models, weights, or submission replays that cannot be recovered if deleted.

## Development & Code Guidelines

1. **Stdout Cleanliness**: Never add arbitrary print statements to `ml_main.py` or `policy.py`. Validated by `tests/test_policy_invariants.py`.
2. **Legacy RL/DT Code**: All RL and DT code has been removed from `policy.py`. Do not restore unless explicitly testing a new ML approach.

## File Cleanup Restrictions

- Do not leave screen recordings (`.webm`), logs (`.log`, `.txt`), or debugging scripts (`debug_*.py`, `fix*.py`) inside the root directory after a task is finished.
- Refer to `instructions/cleanup.md` for specific cleanup procedures.

## Verification Checklist

> [!IMPORTANT]
> Any code change must be validated locally using `python evaluate.py` to ensure no syntax errors or logic bugs are introduced before making a submission.
