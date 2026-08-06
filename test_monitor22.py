from kaggle_environments import make
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

old_agent = main.agent
def wrapped_agent(obs, conf=None):
    res = old_agent(obs)
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    if day == 29 and hour == 23:
        p_idx = obs["player"]
        me = obs["farms"][p_idx]
        priv = obs.get("private", {})
        print(f"FINAL STATS: Money: {me.get('money')}", file=sys.stderr)
        animals_yield = 0
        for row in me.get("tiles", []):
            for t in row:
                if isinstance(t, dict) and "animal" in t:
                    animals_yield += t.get("yield_units", 0)
        print(f"Animals yield units waiting to be collected: {animals_yield}", file=sys.stderr)
    return res
main.agent = wrapped_agent

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
