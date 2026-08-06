from kaggle_environments import make
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

old_agent = main.agent
def wrapped_agent(obs, conf=None):
    if obs.get("day", 0) == 0 and obs.get("hour", 0) == 0:
        with open("revancedmain.py", "r") as f:
            code = f.read()
            if 'print("MONEY LEFT BEFORE SEED:", money_left)' not in code:
                # Let's just modify the code manually using sed instead of this hack
                pass
    return old_agent(obs)
main.agent = wrapped_agent
