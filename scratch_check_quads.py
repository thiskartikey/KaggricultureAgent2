import json
from kaggle_environments import make

env = make("kaggriculture", debug=True)
out = env.run(["policy.py", "policy.py"])

print("Quads at step 168 (before action):", out[168][0].observation.farms[0].get('unlocked_quadrants'))
print("Quads at step 169 (after action):", out[169][0].observation.farms[0].get('unlocked_quadrants'))
print("Quads at step 170 (after action):", out[170][0].observation.farms[0].get('unlocked_quadrants'))
