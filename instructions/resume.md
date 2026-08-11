# Resuming Development (Version A1, Restored 2026-08-12)

If you are a new AI agent or human resuming work, follow these steps to understand the current state and make changes safely.

## Status Summary

**Current agent:** Version A1 (pure heuristic, ~111k local mean). **Submission status:** Ready to upload to Kaggle (rebuilt `ml_submission.tar.gz` verified).

**Critical history:** A v6 "Decision Transformer rewrite" (commits ~52a2cb0 through 66ab183) was deployed and scored ~27k on Kaggle (113k regression). It gutted the working blueprint (pastures 6→6 max, CARE deleted, planting demoted to last priority). All analysis in `downloads/fails/` and `downloads/p2_v2_failure/` relates to that buggy v6. The agent has now been restored to A1 (byte-identical to `versions/Phase2_v1_policy.py`).

## Step 1: Verify Core Repository Files

Ensure that all necessary core files are present in the root directory:
- [ml_main.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/ml_main.py) (Main entrypoint, delegates to policy.agent())
- [policy.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/policy.py) (A1 heuristic strategy engine)
- [evaluate.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/evaluate.py) (Local A/B evaluation harness, 8+ seeds recommended for p<0.05)
- [build_submission.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/build_submission.py) (Packaging script, creates ml_submission.tar.gz)

**Validated baseline:** `versions/Phase2_v1_policy.py` (byte-identical to working policy.py as of 2026-08-12).

## Step 2: Run a Smoke Test Evaluation

Before modifying any code, run a quick validation to check that the current code runs without errors.

```bash
python evaluate.py policy.py versions/Phase2_v1_policy.py --games 2
```

This will run 2 seeds x 2 seats (4 games total). You should see scores near 111k vs 111k (noise only, p≈1.0). If they differ significantly, you have local changes.

## Step 3: Evaluation Protocol

When testing changes:
- **Always test against A1 baseline**: `python evaluate.py policy.py versions/Phase2_v1_policy.py --games 8` (16 games, paired t-test).
- **Significance bar:** p < 0.05 (≥10 seeds x 2 seats, i.e., 20 games total) is required to claim improvement.
- **Single-seed scoring:** Kaggle replays show ~2× variance per run (see `downloads/training/*.json` for reference 150k scores). Never A/B on one run.

## Step 4: Making Changes

- **To adjust heuristic rules:** Edit [policy.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/policy.py) directly.
- **To test:** Use `python evaluate.py policy.py versions/Phase2_v1_policy.py --games 8` (8+ seeds).
- **To submit:** `python build_submission.py && kaggle competitions submit -c kaggriculture -f ml_submission.tar.gz -m "description"`.

## Key Constraints (Learned the Hard Way)

1. **Hands are wiped nightly.** Re-hire every morning or workers will vanish.
2. **Feed routing is critical.** Only wheat-carrying workers can service hungry animals; ignoring this costs +21k (tested).
3. **Crew size: 13 is optimal.** Fib hire cost means hand 14+ cost 987/day marginal vs 609/day for the full crew. Testing 15-crew lost −22k (p=0.000).
4. **Sticky claims prevent oscillation.** Workers holding a task until it disappears saves ~54% of unit-turns vs. recomputing nearest-pair every turn.
5. **Planting is not the bottleneck.** Fallow land post-day-11 is caused by planting being low priority (tier 2) while daily watering treadmill (tier 0–1) starves it for labor; crew size doesn't fix this.
6. **Earlier land unlocks lose money.** Testing days (6,10) vs (7,11) lost −2,347 (p=0.004); day-7/11 are already tuned.

## Files You Can Safely Ignore

- `rl_weights.npz`: Dead-weight (DT disconnected, p=1.000 no impact).
- `train_dt.py`, `versions/rl_inference_v0.py`: Dead code (RL approach never shipped).
- `versions/`: Historical snapshots; reference only. The good archive is `Phase2_v1_policy.py`.
