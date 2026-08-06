from kaggle_environments import make
import sys
env = make("kaggriculture", debug=True)
env.run(["ml_main.py", "starter"])
# Get all actions of player 0
steps = env.steps
for i, step in enumerate(steps[1:10]):
    print(f"Step {i}: Action =", step[0]['action'])
