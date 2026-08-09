# Kagriculture Agent — Resume Checkpoint

> **Updated**: 2026-08-09
> **Status**: Completed advanced strategy improvements (routing, replanting buffer, melon price protection) and implemented the pure NumPy **Decision Transformer** (DT) model inference class within `policy.py`. Note: Goose management was experimented with but discarded due to negative impact on profit.

---

## 0. Repository

- **GitHub**: **https://github.com/gytdrop/KaggricultureAgent** (branch `main`).
- Tracked files include `ml_main.py`, `policy.py`, `test_policy.py`, `CHECKPOINT_RESUME.md`, and the `instructions/` folder.
- Large replays in `downloads/` and caches are `.gitignore`d. See `instructions/git.md` for proper staging.

---

## 1. Where things stand

The baseline agent is a **highly optimized heuristic** now located in [policy.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/policy.py) (scoring **~111k+ / 115k+** median on evaluations, v7 baseline + optimizations). 

In this checkpoint run, we implemented:
- **Routing Efficiency:** Rewrote task assignment to favor local (`d=0`) actions regardless of tier, saving worker steps and boosting useful turns.
- **Replanting Buffer:** Sows are planned instantly by keeping a seed buffer for crops currently harvesting in the same turn.
- **Melon Price Protection:** Increased Melon market reserve fraction to `0.80` to prevent self-price dumping.
- **Goose Management (Discarded):** We implemented and evaluated Coop + Goose management. It significantly decreased scores (-7k points; 0/20 wins) compared to routing+replanting optimizations, likely due to low egg value ($50) and building overhead. We have disabled/reverted it.
- **Decision Transformer Inference:** Implemented a full pure-NumPy self-attention DT inference engine class (`DecisionTransformer`) inside `policy.py` so it can immediately run offline-trained PyTorch weights once exported to `.npz`.

### Evaluate the Current Policy Against the Baseline v7

```bash
python evaluate.py ml_main.py versions/heuristic_v7.py --games 10
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

## 3. Decision Transformer Integration

We will train a sequence model on player-episodes scoring $\ge 100k$ from our replay corpus:
- **Input sequence**: $[R_1, S_1, A_1, R_2, S_2, A_2, \dots, R_t, S_t, A_t]$
- **States ($S$)**: Vector representation of local and global farm states.
- **Actions ($A$)**: Discrete action tokens for planting, watering, animal buying, and market trades.
- **Returns-to-go ($R$)**: Target final cash remaining to achieve.
- **Inference**: The causal self-attention network has been implemented in NumPy inside `policy.py` for lightning-fast execution.

---

## 4. File map

| File | Role |
|---|---|
| `policy.py` | **The strategy core.** Contains the optimized heuristic and the NumPy Decision Transformer engine. |
| `ml_main.py` | Entrypoint packaged as `main.py` for Kaggle; delegates to `policy.agent`. |
| `evaluate.py` | A/B evaluation harness with paired t-test. |
| `build_submission.py` | Builds `ml_submission.tar.gz` (packages only `ml_main.py` and `policy.py`). |
| `instructions/` | Documentation for environment, restrictions, and strategy. |
| `versions/` | Historic snapshots of heuristic versions and archived legacy PPO model code. |

---

## 5. Next Steps

1. **Replay Parser**: Refine `parse_replays.py` to format JSON logs from `downloads/training/` into sequence sequences of `(R, S, A)` matching the model's dimensions.
2. **Train Script**: Implement the Decision Transformer training loop in PyTorch using causal self-attention, trained via supervised learning to predict the next expert action.
3. **Weights Export**: Export PyTorch model weights to `.npz` format matching the weight names expected by the NumPy implementation in `policy.py`.
4. **Evaluate**: Run evaluations comparing the active Decision Transformer agent against the active heuristic baseline.
