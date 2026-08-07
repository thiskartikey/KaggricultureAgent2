# Submission Packaging Instructions

To submit the agent to the Kaggle competition, you must follow the packaging rules specified below.

## Packaging Script

The repository includes a script [build_submission.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/build_submission.py) to package the agent.

Run the following command to build the submission archive:
```bash
python build_submission.py
```
This command creates `ml_submission.tar.gz` in the root directory.

## File Mappings Inside the Archive

Kaggle requires the entrypoint script to be named `main.py`. The build script maps files accordingly:

| Local Source File | Tar Destination Path | Purpose |
| :--- | :--- | :--- |
| `ml_main.py` | `main.py` | Main agent loop entrypoint |
| `env_wrapper.py` | `env_wrapper.py` | Vectorization & wrappers |
| `heuristic.py` | `heuristic.py` | Heuristics & market pricing fallback |
| `rl_inference.py` | `rl_inference.py` | Zero-dependency neural net loader |
| `rl_weights.npz` | `rl_weights.npz` | PPO model weights |

## Kaggle Environment Constraints

1. **Zero-Dependency Inference**: Submissions run on Kaggle sandboxes without internet access or GPU acceleration. You cannot import `stable-baselines3` or `torch` during evaluation. The policy uses pure numpy matrix multiplications via `rl_inference.py`.
2. **File References**: The Kaggle agent loader extracts and runs the tarball in a temporary directory. Dynamic path handling is implemented in `main.py` to load `rl_weights.npz` relative to `__file__`.
3. **Execution Limits**: The agent must return actions within the game's time limit per step (typically 1 second). Do not add slow calculations or search algorithms to the step loop.
