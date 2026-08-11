from kaggle_environments import make
import policy

env = make("kaggriculture", debug=True)
out = env.run(["policy.py", "policy.py"])

print("Final scores:", [agent.reward for agent in out[-1]])

import sys
sys.path.append(".")
import policy

print("Melon profit day 1:", policy.plant_expected_profit("MELON", 1, 30, {}))
print("Melon profit day 15:", policy.plant_expected_profit("MELON", 15, 30, {}))
print("Melon profit day 20:", policy.plant_expected_profit("MELON", 20, 30, {}))

print("Strawberry profit day 1:", policy.plant_expected_profit("STRAWBERRY", 1, 30, {}))

