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
    me = obs.get("farms", [{}])[obs.get("player", 0)]
    private = obs.get("private", {})
    animals = main._count_animals(me, private)
    if hour == 23:
        print(f"Day {day} animals={animals} SHED_EGG={private.get('shed', {}).get('EGG', 0)} SHED_MILK={private.get('shed', {}).get('MILK', 0)} WHEAT={private.get('shed', {}).get('WHEAT', 0)}", file=sys.stderr)
    return res
main.agent = wrapped_agent

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
print(f"Final Score: {env.steps[-1][0].reward}", file=sys.stderr)
