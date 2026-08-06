from kaggle_environments import make
import importlib.util
import traceback

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

def crash_agent(obs):
    return main._agent(obs)

env = make("kaggriculture", debug=True)
env.run([crash_agent, "starter"])
