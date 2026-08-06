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
    if day == 10 and hour > 10:
        print(f"Day {day} hour {hour} farmer: {res.get('farmer')} hands: {res.get('hands')}", file=sys.stderr)
    return res

main._agent = wrapped_agent
env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
