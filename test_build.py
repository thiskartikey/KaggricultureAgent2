from kaggle_environments import make
import importlib.util

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

def debug_agent(obs):
    day = obs.get("day", 0)
    res = main._agent(obs)
    if day == 10:
        tasks = []
        for v in res.get("farmer", []):
            tasks.append(v)
        for h in res.get("hands", []):
            tasks.append(h)
        # print("Day 10 actions:", tasks)
    return res
main._agent = debug_agent

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
for i, step in enumerate(env.steps):
    if i == 0: continue
    obs = step[0].observation
    day = obs.get("day", 0)
    me = obs["farms"][obs["player"]]
    empty = 0
    pasture = 0
    coop = 0
    for r in me["tiles"]:
        for t in r:
            if isinstance(t, dict):
                k = t.get("kind")
                if k == "PASTURE": pasture += 1
                if k == "COOP": coop += 1
                if k in ("COOP", "PASTURE") and not t.get("animal"):
                    empty += 1
    if day > 8 and day < 15:
        print(f"Day {day} hour {obs['hour']}: empty={empty} pasture={pasture} coop={coop}")
