# Reinforcement Learning (Legacy / Archived)

> [!NOTE]
> The Reinforcement Learning (PPO) model and its supporting codebase are currently **archived/dead code**. The active agent uses a pure rule-based heuristic strategy which dramatically outperforms the old RL model (yielding 123k+ vs 1.9k).

## Archived Files in `versions/`

If you want to revive, retrain, or analyze the Reinforcement Learning approach, all files have been archived in the [versions/](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/versions) directory:

- **`train_rl_v0.py`**: The training configuration script using `stable-baselines3` and `PyTorch`.
- **`env_wrapper_v0.py`**: Handles numerical observation vectorization (`obs_to_vec`) and discrete action decoding.
- **`rl_inference_v0.py`**: Pure-NumPy neural network engine for zero-dependency policy forward passes.
- **`rl_weights_v0.npz`**: The serialized actor-critic weights.
- **`tune_v0.py`**: The hyperparameter optimization script.
- **`train_on_kaggle.ipynb`**: Prepared Jupyter notebook template to train models using Kaggle's free GPU resources.
