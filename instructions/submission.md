# Submission Packaging Instructions

To submit the agent to the Kaggle competition, follow the packaging rules below.

## Packaging Script

```bash
python3 build_submission.py
```

This creates `ml_submission.tar.gz` in the root directory.

## File Mappings Inside the Archive

Kaggle requires the entrypoint script to be named `main.py`.

| Local Source File | Tar Destination | Purpose |
|---|---|---|
| `ml_main.py` | `main.py` | Main agent entrypoint |
| `policy.py` | `policy.py` | Strategy engine |

## Kaggle Environment Constraints

1. **Zero-Dependency**: No heavy ML dependencies (PyTorch, TensorFlow, Gym, scipy) — `policy.py` imports only `math`.
2. **Execution Limits**: Must return actions within 1 second. Heuristic executes in ~2–5 ms per step.
3. **No stdout pollution**: `policy.py` and `ml_main.py` must not print to stdout. Validated by `tests/test_policy_invariants.py`.

## Pre-Submission Checklist

```bash
# 1. Run all tests
python3 -m pytest tests/ -q

# 2. Build tarball
python3 build_submission.py

# 3. Verify tarball contents
tar -ztvf ml_submission.tar.gz

# 4. Submit
kaggle competitions submit kaggriculture -f ml_submission.tar.gz -m "EXP-YYYYMMDD-NN description"
```
