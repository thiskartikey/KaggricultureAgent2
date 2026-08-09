# Kagriculture Agent — Resume Checkpoint

> **Updated**: 2026-08-09
> **Status**: Shifted architecture to **Decision Transformer** (DT) model policy. Renamed strategy core to `policy.py` (with the optimized v7 heuristic as our solid baseline/fallback layer).

---

## 0. Repository

- **GitHub**: **https://github.com/gytdrop/KaggricultureAgent** (branch `main`).
- Tracked files include `ml_main.py`, `policy.py`, `test_policy.py`, `CHECKPOINT_RESUME.md`, and the `instructions/` folder.
- Large replays in `downloads/` and caches are `.gitignore`d. See `instructions/git.md` for proper staging.

---

## 1. Where things stand

The baseline agent is a **pure heuristic** now located in [policy.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/policy.py) (scoring **~123k+** on evaluations, v7 baseline). 

The PPO Reinforcement Learning model files have been archived to `versions/` as legacy code. We are transitioning to a **Decision Transformer** offline learning strategy that will train on the 73 top-player replays under `downloads/training/`.

### Reproduce the Baseline Numbers

```bash
python evaluate.py policy.py versions/heuristic_BASELINE_ab.py --games 10
```

---

## 2. Ground truth — read the env source, do not guess

The real rules ship with the package:
`~/.local/lib/python3.14/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py`

Key parameters:
- **30 days** of 24 turns (720 steps). Reward is **final cash only**.
- **Farm hands cost progression**: $n$-th hire costs `fib(n)`. Dismissed every night; re-hired every morning.
- **Watering rules**: Crops must be watered the day they are sown to prevent weed conversion. Ongoing crops (strawberries) can skip watering days to save labor.
- **Shed limit**: 100 items; overflow is discarded at end of day.
- **Market transactions**: Max 10 orders per turn.

---

## 3. Decision Transformer Blueprint

We will train a sequence model on player-episodes scoring $\ge 100k$ from our replay corpus:
- **Input sequence**: $[R_1, S_1, A_1, R_2, S_2, A_2, \dots, R_t, S_t, A_t]$
- **States ($S$)**: Vector representation of local and global farm states.
- **Actions ($A$)**: Discrete action tokens for planting, watering, animal buying, and market trades.
- **Returns-to-go ($R$)**: Target final cash remaining to achieve.
- **Inference**: The causal self-attention network will be implemented in NumPy inside `policy.py` for lightning-fast execution.

---

## 4. File map

| File | Role |
|---|---|
| `policy.py` | **The strategy core.** Contains the v7 heuristic baseline and will house the NumPy Decision Transformer engine. |
| `ml_main.py` | Entrypoint packaged as `main.py` for Kaggle; delegates to `policy.agent`. |
| `evaluate.py` | A/B evaluation harness with paired t-test. |
| `build_submission.py` | Builds `ml_submission.tar.gz` (packages only `ml_main.py` and `policy.py`). |
| `instructions/` | Documentation for environment, restrictions, and strategy. |
| `versions/` | Historic snapshots of heuristic versions and archived legacy PPO model code. |

---

## 5. Next Steps

1. **Replay Parser**: Write a script to load JSON logs from `downloads/training/` and format them into sequence sequences of `(R, S, A)`.
2. **Train Script**: Implement a Decision Transformer model in PyTorch using causal self-attention, trained via supervised learning to predict the next expert action.
3. **NumPy Port**: Export trained weights and write a pure-NumPy self-attention inference pipeline in `policy.py`.
4. **Evaluate**: Run `python evaluate.py` to compare the Decision Transformer agent against the v7 heuristic baseline.
