from kaggle_environments import make
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

old_plan_sells = main.plan_sells
def wrapped_plan_sells(*args, **kwargs):
    orders = old_plan_sells(*args, **kwargs)
    day = args[2]
    print(f"Day {day} plan_sells orders: {orders}", file=sys.stderr)
    return orders

main.plan_sells = wrapped_plan_sells

old_agent = main._agent
def wrapped_agent(obs):
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    if hour == 0:
        me = obs.get("farms", [{}])[obs.get("player", 0)]
        tiles = me.get("tiles", [])
        animals = 0
        for row in tiles:
            for t in row:
                if isinstance(t, dict) and t.get("kind") in ("COOP", "PASTURE") and t.get("animal"):
                    animals += 1
        shed = obs.get("private", {}).get("shed", {})
        print(f"Day {day} Hour {hour} BEFORE agent. Animals: {animals}, Shed WHEAT: {shed.get('WHEAT', 0)}", file=sys.stderr)
    res = old_agent(obs)
    return res
main._agent = wrapped_agent
main.agent = lambda obs, conf: wrapped_agent(obs)

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
