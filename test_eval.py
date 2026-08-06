from kaggle_environments import make
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

old_agent = main.agent
def wrapped_agent(obs, conf=None):
    return old_agent(obs)
main.agent = wrapped_agent

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
p0 = env.state[0].observation.farms[0]
p1 = env.state[0].observation.farms[1]
print(f"P0 Score: {p0.get('money')} P1 Score: {p1.get('money')}")
