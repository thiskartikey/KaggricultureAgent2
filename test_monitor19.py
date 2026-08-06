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
    if 17 <= day <= 17 and 13 <= hour <= 15:
        p_idx = obs["player"]
        priv = obs["players"][p_idx]
        farmer = obs["farmer"]
        print(f"Day {day} hour {hour} HAND INVS: {priv.get('inventories', [])}", file=sys.stderr)
        print(f"Day {day} hour {hour} SHED: {priv.get('shed', {})}", file=sys.stderr)
        print(f"Day {day} hour {hour} HAND POSITIONS: {obs.get('hands', [])}", file=sys.stderr)
        print(f"Day {day} hour {hour} HANDS OPS: {res.get('hands')}", file=sys.stderr)
    return res
main.agent = wrapped_agent

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
