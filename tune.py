"""Offline coordinate-descent tuner for the heuristic agent's knobs.

Learning happens here, not in the submitted agent: a Kaggle episode is a fresh
process with no persistent storage, so an agent cannot accumulate outcomes
across games. Instead we search main.py's `P` knobs against a fixed seed set
(deterministic, so candidates are comparable) and keep only changes that raise
the mean. The winning params get folded into P's defaults.

Candidates run as subprocesses because main.py reads KAGR_PARAMS at import.

Usage: .venv/bin/python tune.py [rounds]
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(HERE, ".venv", "bin", "python")
WORK = os.path.join(HERE, "tuning")
TRAIN_SEEDS = [7, 42, 101, 202, 303]
HOLDOUT_SEEDS = [404, 505, 606, 707]

BASE = dict(
    d0_melon=6, d0_wheat_seed=7, d0_cow=2, d0_sheep=1, d0_feed=20,
    target_pastures=14, hire_target=14, min_reserve=60, land_free=8,
    pr_plant=70, pr_collect=78, pr_care=72, pr_harvest_crop=80,
    pr_build_pasture=88, seed_restock=3, wheat_hold_days=3,
)

# Values to try per knob. Ordered widest-impact first so early rounds matter most.
GRID = {
    "d0_melon":       [4, 6, 9, 12],
    "d0_feed":        [10, 20, 30, 45],
    "d0_cow":         [1, 2, 3],
    "d0_sheep":       [0, 1, 2],
    "target_pastures":[8, 11, 14, 18],
    "hire_target":    [8, 11, 14, 18],
    "wheat_hold_days":[2, 3, 5, 8],
    "pr_plant":       [70, 82, 92, 100],
    "pr_collect":     [40, 60, 78],
    "pr_care":        [35, 55, 72],
    "pr_harvest_crop":[80, 90, 98],
    "pr_build_pasture":[74, 88, 96],
    "land_free":      [5, 8, 12],
    "min_reserve":    [0, 60, 200],
}

RUNNER = r'''
import json, os, statistics, sys
from kaggle_environments import make
seeds = json.loads(sys.argv[1])
out = []
for s in seeds:
    env = make("kaggriculture", configuration={"seed": s})
    env.run(["main.py", "starter"])
    r = env.steps[-1][0].reward
    out.append(-1 if r is None else r)
print("RESULT", statistics.mean(out))
'''


def evaluate(args):
    """Run one candidate in a fresh interpreter; return mean score."""
    params, seeds, tag = args
    os.makedirs(WORK, exist_ok=True)
    pf = os.path.join(WORK, f"p_{tag}.json")
    with open(pf, "w") as fh:
        json.dump(params, fh)
    env = dict(os.environ, KAGR_PARAMS=pf)
    try:
        r = subprocess.run([PY, "-c", RUNNER, json.dumps(seeds)], cwd=HERE, env=env,
                           capture_output=True, text=True, timeout=1800)
    except subprocess.TimeoutExpired:
        return tag, None
    for line in reversed(r.stdout.splitlines()):
        if line.startswith("RESULT"):
            return tag, float(line.split()[1])
    return tag, None


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    best = dict(BASE)
    _, base_score = evaluate((best, TRAIN_SEEDS, "base"))
    print(f"baseline train mean {base_score:,.0f}", flush=True)
    best_score = base_score

    for rnd in range(rounds):
        improved = False
        for knob, values in GRID.items():
            cands = [v for v in values if v != best[knob]]
            if not cands:
                continue
            jobs = []
            for i, v in enumerate(cands):
                p = dict(best); p[knob] = v
                jobs.append((p, TRAIN_SEEDS, f"{rnd}_{knob}_{i}"))
            with ProcessPoolExecutor(max_workers=3) as ex:
                results = list(ex.map(evaluate, jobs))
            for (tag, score), v in zip(results, cands):
                if score is None:
                    continue
                mark = ""
                if score > best_score + 1:
                    best_score, best[knob], improved = score, v, True
                    mark = "  <-- kept"
                print(f"  {knob}={v:<5} {score:>10,.0f}{mark}", flush=True)
            print(f"[{knob}] best so far {best_score:,.0f} {best[knob]}", flush=True)
        with open(os.path.join(WORK, "best.json"), "w") as fh:
            json.dump(best, fh, indent=2)
        print(f"\nround {rnd}: train mean {best_score:,.0f}\n{json.dumps(best)}", flush=True)
        if not improved:
            print("no improvement this round; stopping", flush=True)
            break

    # Holdout check: a gain that does not transfer is overfitting to 5 boards.
    _, hb = evaluate((BASE, HOLDOUT_SEEDS, "hold_base"))
    _, hn = evaluate((best, HOLDOUT_SEEDS, "hold_new"))
    print(f"\nHOLDOUT  baseline {hb:,.0f}  tuned {hn:,.0f}  delta {hn - hb:+,.0f}")
    print(f"train {base_score:,.0f} -> {best_score:,.0f}")


if __name__ == "__main__":
    main()
