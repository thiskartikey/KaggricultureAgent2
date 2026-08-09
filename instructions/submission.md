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
| `ml_main.py` | `main.py` | Main agent entrypoint |
| `heuristic.py` | `heuristic.py` | Pure heuristic strategy engine |

## Kaggle Environment Constraints

1. **Zero-Dependency Heuristics**: The submission package is purely rule-based and requires no heavy machine learning dependencies (e.g. PyTorch, stable-baselines3), allowing it to fit into an ultra-lightweight ~11 KB archive.
2. **Execution Limits**: The agent must return actions within the game's time limit per step (typically 1 second). The heuristic executes in ~2.4 ms per call, well within limits.
3. **No stdout pollution**: Do not add print statements to `heuristic.py` or `ml_main.py` since stdout is reserved for sandbox execution communications.

