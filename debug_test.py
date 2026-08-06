from kaggle_environments import make
import importlib.util

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
print("Final score:", env.steps[-1][0]["reward"])
