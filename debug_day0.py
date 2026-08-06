from kaggle_environments import make
import importlib.util

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

old_agent = main._agent

def wrapped_agent(obs):
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    if day == 0 and hour == 0:
        print("====== DAY 0 HOUR 0 START ======")
    res = old_agent(obs)
    if day == 0 and hour == 0:
        print("====== DAY 0 HOUR 0 ORDERS ======")
        print(res.get("market", []))
    return res

main._agent = wrapped_agent

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
