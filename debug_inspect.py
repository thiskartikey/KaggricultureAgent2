from kaggle_environments import make
import importlib.util

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])

for i, step in enumerate(env.steps):
    action = step[0].action
    if action:
        print(f"Step {i}:")
        print("Market orders:", action.get('market'))
        print("Hands actions:", action.get('hands'))
        print("Farmer action:", action.get('farmer'))
        
    if i > 50:
        break
