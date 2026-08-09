# Resuming Development

If you are a new AI agent resuming work on this repository, follow these steps to verify the environment and start making changes safely.

## Step 1: Verify Core Repository Files

Ensure that all necessary core files are present in the root directory:
- [ml_main.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/ml_main.py) (Main entrypoint)
- [heuristic.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/heuristic.py) (Pure heuristic strategy engine)
- [evaluate.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/evaluate.py) (Local A/B evaluation harness)
- [build_submission.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/build_submission.py) (Packaging script)

## Step 2: Run a Smoke Test Evaluation

Before modifying any code, run a quick local validation to check that the current code runs and outputs actions correctly without errors.

```bash
python evaluate.py heuristic.py versions/heuristic_BASELINE_ab.py --games 2
```

This will run 2 seeds x 2 seats (4 games in total) between the current heuristic and the baseline historical agent to check for run-time compatibility.

## Step 3: Making Changes

- **To adjust rules/heuristics**: Edit [heuristic.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/heuristic.py).
- **To test modifications**: Use the A/B evaluation tool: `python evaluate.py <your_modified_script.py> heuristic.py --games 10`

Always run `python evaluate.py` after editing code to ensure you did not introduce regression bugs.

