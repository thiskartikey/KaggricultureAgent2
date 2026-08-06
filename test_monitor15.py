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
    scan = main._scan(me, day)
    
    # Let's print the status of the first animal we find
    for row in me.get("tiles") or []:
        for t in row:
            if isinstance(t, dict) and t.get("kind") in ("COOP", "PASTURE") and t.get("animal"):
                print(f"Day {day} hour {hour} ANIMAL at {t.get('animal')} fed: {t.get('fed_today')} cared: {t.get('cared_today')} y: {t.get('yield_units', 0)} pd: {t.get('placed_day')}", file=sys.stderr)
                break
        else:
            continue
        break
        
    return res
main.agent = wrapped_agent

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
print(f"Final Score: {env.steps[-1][0].reward}", file=sys.stderr)
