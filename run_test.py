"""Self-play test harness: main.py vs built-in baselines. Usage: .venv/bin/python run_test.py [n_games]"""
import sys
import importlib.util

from kaggle_environments import make

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
for opp in ["starter", "random"]:
    wins = losses = ties = 0
    for g in range(n):
        env = make("kaggriculture", debug=(g == 0))
        # alternate seats
        if g % 2 == 0:
            env.run([main.agent, opp])
            mine, theirs = env.steps[-1][0], env.steps[-1][1]
        else:
            env.run([opp, main.agent])
            mine, theirs = env.steps[-1][1], env.steps[-1][0]
        r0, r1 = mine.reward, theirs.reward
        if r0 is None:
            r0 = -1
        if r1 is None:
            r1 = -1
        wins += r0 > r1
        losses += r0 < r1
        ties += r0 == r1
        print(f"  vs {opp} g{g}: me={r0} opp={r1} status=({mine.status},{theirs.status})")
    print(f"vs {opp}: {wins}W {losses}L {ties}T")
