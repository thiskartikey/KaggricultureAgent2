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
    
    # Check if ANY animal has yield > 0
    yield_count = 0
    fed_count = 0
    cared_count = 0
    total_animals = 0
    for row in me.get("tiles") or []:
        for t in row:
            if isinstance(t, dict) and t.get("kind") in ("COOP", "PASTURE") and t.get("animal"):
                total_animals += 1
                if t.get("yield_units", 0) > 0:
                    yield_count += 1
                if t.get("fed_today"):
                    fed_count += 1
                if t.get("cared_today"):
                    cared_count += 1
    
    if hour == 23 and total_animals > 0:
        print(f"Day {day} hour {hour} Animals: {total_animals} (Fed: {fed_count}, Cared: {cared_count}, Yielding: {yield_count})", file=sys.stderr)
        
    return res
main.agent = wrapped_agent

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
print(f"Final Score: {env.steps[-1][0].reward}", file=sys.stderr)
