# Resuming Development

If you are a new AI agent resuming work on this repository, follow these steps to verify the environment and start making changes safely.

## Step 1: Verify Core Repository Files

Ensure that all necessary core files are present in the root directory:
- [ml_main.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/ml_main.py) (Main RL wrapper)
- [heuristic.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/heuristic.py) (Fallback heuristic)
- [env_wrapper.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/env_wrapper.py) (State vectorizers)
- [rl_inference.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/rl_inference.py) (Model loader)
- [rl_weights.npz](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/rl_weights.npz) (Model weights)

## Step 2: Run a Smoke Test Evaluation

Before modifying any code, run a quick local validation to check that the current code runs and outputs actions correctly without errors.

```bash
python evaluate.py ml_main.py heuristic.py --games 2
```

This will run 2 seeds x 2 seats (4 games in total) between the RL-based agent and the heuristic agent to check for run-time compatibility issues.

## Step 3: Making Changes

- **To adjust rules/heuristics**: Edit [heuristic.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/heuristic.py).
- **To adjust observation space or features**: Edit [env_wrapper.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/env_wrapper.py).
- **To run hyperparameter tuning**: Refer to [tune.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/tune.py).

Always run `python evaluate.py` after editing code to ensure you did not introduce regression bugs.
