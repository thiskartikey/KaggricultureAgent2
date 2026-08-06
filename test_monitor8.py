from kaggle_environments import make
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

old_agent = main.agent
def wrapped_agent(obs, *args):
    res = old_agent(obs, *args)
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    if day in (15, 16):
        print(f"Day {day} hour {hour} ACTUALLY EXECUTING {res}", file=sys.stderr)
    return res
main.agent = wrapped_agent

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
