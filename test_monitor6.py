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
    if hour == 1:
        farm = obs.get("private", {}).get("farm", {})
        tiles = farm.get("tiles", [])
        animals = 0
        for row in tiles:
            for t in row:
                if isinstance(t, dict) and "animal" in t:
                    animals += 1
        print(f"Day {day} Animals: {animals}", file=sys.stderr)
    return res

main._agent = wrapped_agent
main.agent = lambda obs, conf: wrapped_agent(obs)

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
