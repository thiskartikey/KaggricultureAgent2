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
    
    # Check if there are any harvest tasks for animals
    me = obs.get("farms", [{}])[obs.get("player", 0)]
    scan = main._scan(me, day)
    
    if len(scan.get("harvest_animal", [])) > 0:
        print(f"Day {day} hour {hour} scan harvest_animal: {scan['harvest_animal']}", file=sys.stderr)
        
    for op in [res.get("farmer")] + res.get("hands", []):
        if op and len(op) > 0 and op[0] == "HARVEST":
            print(f"Day {day} hour {hour} DOING HARVEST!", file=sys.stderr)
            
    if hour == 23:
        private = obs.get("private", {})
        print(f"Day {day} SHED: {private.get('shed', {})}", file=sys.stderr)
        
    return res
main.agent = wrapped_agent

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
print(f"Final Score: {env.steps[-1][0].reward}", file=sys.stderr)
