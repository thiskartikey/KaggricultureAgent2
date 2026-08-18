# Evaluation Guidelines

We run an A/B evaluation harness locally using [evaluate.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/evaluate.py) to assess agent improvements. This eliminates noise from seed variance and seat bias.

## Running Evaluations

To run a head-to-head match between two agents:
```bash
python3 evaluate.py policy.py versions/EXP-20260815-69_policy.py --games 8
```

- Each seed is played **twice** (once with Agent A in seat 0, once with Agent B in seat 0) to prevent seat advantage bias.
- The command above will execute 16 games in total.

## Key Metrics Explained

1. **Mean Score**: The average reward achieved by the agent over all games.
2. **Win Rate**: The count of games where Agent A scored higher than Agent B.
3. **Paired t-statistic and P-value**:
   - The paired t-test calculates if the mean difference in score is significantly different from 0.
   - **p < 0.05**: The change is **SIGNIFICANT**. The agent is statistically superior/inferior.
   - **p >= 0.20**: The difference is **NOISE**. Do not rely on these results to make design choices.

## Performance Optimization

The evaluation harness parallelizes game runs across CPU cores. Use the `--workers` flag to specify parallel threads (defaults to CPU count - 2).
