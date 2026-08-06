"""Deterministic evaluation over a fixed seed set.

The env is non-deterministic by default: repeated runs of identical code span
~6k-17k, so single-run A/B comparisons are meaningless. Passing an explicit
seed makes a run reproducible, so the same seed set gives comparable means
across agent versions.

Usage: .venv/bin/python eval_seeds.py [agent.py] [n_seeds]
"""
import statistics
import sys

from kaggle_environments import make

SEEDS = [7, 42, 101, 202, 303, 404, 505, 606, 707, 808]

agent = sys.argv[1] if len(sys.argv) > 1 else "main.py"
n = int(sys.argv[2]) if len(sys.argv) > 2 else len(SEEDS)

scores, wins = [], 0
for s in SEEDS[:n]:
    env = make("kaggriculture", configuration={"seed": s})
    env.run([agent, "starter"])
    me, opp = env.steps[-1][0].reward, env.steps[-1][1].reward
    scores.append(me)
    wins += (me or -1) > (opp or -1)
    print(f"seed {s:4d}  me={me:>9,.0f}  opp={opp:>9,.0f}")

print(f"\n{agent}  n={len(scores)}  wins={wins}/{len(scores)}")
print(f"  mean   {statistics.mean(scores):>10,.0f}")
print(f"  median {statistics.median(scores):>10,.0f}")
print(f"  min    {min(scores):>10,.0f}   max {max(scores):>10,.0f}")
