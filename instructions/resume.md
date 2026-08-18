# Resuming Development

If you are a new AI agent or human resuming work, read this first.

## Current State

- **Champion policy**: `policy.py` = `versions/EXP-20260815-69_policy.py` (functionally identical, dead code removed).
- **Autoresearch system**: Fully built in `src/autoresearch/` — controller, evaluator, mutator, hypothesis generator, memory, stats.
- **Test suite**: 83/83 tests pass in `tests/`.
- **Evaluation**: Use `src/autoresearch/evaluator.py` or the legacy `evaluate.py` CLI.

## Step 1: Smoke Test

```bash
python3 -m pytest tests/ -q
# Should show: 83 passed

python3 -c "
from src.autoresearch.evaluator import _run_games
from src.autoresearch.stats import full_stats
cand, base, _ = _run_games('policy.py', 'versions/EXP-20260815-69_policy.py', [9000], 2)
print(full_stats(cand, base))
# Δmean should be 0 — they are functionally identical
"
```

## Step 2: Understanding the Champion

See [`instructions/policy.md`](policy.md) for full strategy details and the complete list of rejected experiments.

Key constants to never blindly change (all have been tested and rejected):
- `LAND_UNLOCK_DAY = (6, 10)` → **−5,542** (agent can't afford unlock day 6)
- `target_hands` day 1 = 1 → **−11,509** (labour starvation)
- price reserve on sells → **−3,457** (sell-all beats holding)
- `TARGET_PASTURE_BY_DAY = ((10,14),(7,9),(0,6))` → **−6,389** (drops mid-game to 9)

## Step 3: Running an Experiment

### Via KaggriRatchet (automated)
```bash
python3 -m src.autoresearch.controller --step        # one experiment
python3 -m src.autoresearch.controller --loop --max-exp 5
```

### Manually
```bash
# Edit policy.py, then test vs champion:
python3 - << 'EOF'
from src.autoresearch.evaluator import _run_games
from src.autoresearch.stats import full_stats
import time
seeds = list(range(3000, 3016))
t0 = time.perf_counter()
c, b, failed = _run_games('policy.py', 'versions/EXP-20260815-69_policy.py', seeds, 6)
print(f"{time.perf_counter()-t0:.1f}s  failed={failed}")
s = full_stats(c, b)
print(f"Δmean={s['delta_mean']:+,.0f}  p_t={s['p_ttest']:.4f}  d={s['cohens_d']:.3f}")
EOF
```

**Promotion bar**: `p_ttest < 0.05`, `p_wilcoxon < 0.05`, `cohens_d > 0.20`, `delta_mean > 0` over 32 games.

## Step 4: Submitting

```bash
python3 build_submission.py
kaggle competitions submit kaggriculture -f ml_submission.tar.gz -m "EXP-YYYYMMDD-NN description"
```

## Key Invariants (Never Break)

1. **Hands wiped nightly** — always re-hire every morning.
2. **Feed routing** — only wheat-carrying workers → hungry animals.
3. **Sticky claims** — workers hold a task until it disappears; prevents oscillation.
4. **Planting day = unwatered day 1** — sow at hour ≤ 20 or the plant dies tonight.
5. **Shed cap = 100** — overflow discarded silently at end-of-day.
6. **10 market orders/turn** — extras silently dropped.
7. **No ML imports** — policy.py must pass the invariant gate (test_policy_invariants.py).
