from kaggle_environments import make
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

old_agent = main._agent
def wrapped_agent(obs):
    res = old_agent(obs)
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    actions = [res.get("farmer")] + (res.get("hands") or [])
    for a in actions:
        if a and a[0].startswith("BUILD"):
            print(f"Day {day} hour {hour} ACTUALLY EXECUTING {a[0]}!", file=sys.stderr)
        if a and a[0].startswith("PLACE"):
            print(f"Day {day} hour {hour} ACTUALLY EXECUTING {a[0]}!", file=sys.stderr)
    return res

main._agent = wrapped_agent
main.agent = lambda obs, conf: wrapped_agent(obs)

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
