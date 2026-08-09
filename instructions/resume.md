# Resuming Development

If you are a new AI agent resuming work on this repository, follow these steps to verify the environment and start making changes safely.

## Step 1: Verify Core Repository Files

Ensure that all necessary core files are present in the root directory:
- [ml_main.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/ml_main.py) (Main entrypoint)
- [policy.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/policy.py) (Strategy engine)
- [evaluate.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/evaluate.py) (Local A/B evaluation harness)
- [build_submission.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/build_submission.py) (Packaging script)

## Step 2: Run a Smoke Test Evaluation

Before modifying any code, run a quick local validation to check that the current code runs and outputs actions correctly without errors.

```bash
python evaluate.py ml_main.py versions/heuristic_v7.py --games 2
```

This will run 2 seeds x 2 seats (4 games in total) between the current policy and the baseline heuristic agent (v7) to check for run-time compatibility.

## Step 3: Making Changes

- **To adjust rules/heuristics**: Edit [policy.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/policy.py).
- **To test modifications**: Use the A/B evaluation tool: `python evaluate.py ml_main.py versions/heuristic_v7.py --games 10`

Always run `python evaluate.py` after editing code to ensure you did not introduce regression bugs.
