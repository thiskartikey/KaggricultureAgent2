from kaggle_environments import make
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
print(f"Final Score: {env.steps[-1][0].reward}", file=sys.stderr)
