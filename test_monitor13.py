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
    if day == 20 and hour == 0:
        me = obs.get("farms", [{}])[obs.get("player", 0)]
        print(f"Day 20 hour 0 market: {res.get('market')}", file=sys.stderr)
        # we can't easily intercept the internal variables, let's just observe if hands exist at hour 1
    if day == 20 and hour == 1:
        print(f"Day 20 hour 1 hands: {res.get('hands')}", file=sys.stderr)
    return res
main.agent = wrapped_agent

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
