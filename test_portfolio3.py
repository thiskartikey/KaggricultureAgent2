from kaggle_environments import make
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

old_plan = main.plan_portfolio
def wrapped_plan(*args, **kwargs):
    orders, seeds = old_plan(*args, **kwargs)
    day = args[0] # Actually `plan_portfolio` has `day` as first or maybe 3rd arg?
    # signature: plan_portfolio(day, total_days, money, free_cells, current_seeds)
    if isinstance(args[0], int):
        day = args[0]
    else:
        day = getattr(args[0], "day", "unknown")
    print(f"Day {day} plan_portfolio orders: {orders}", file=sys.stderr)
    return orders, seeds

main.plan_portfolio = wrapped_plan

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
