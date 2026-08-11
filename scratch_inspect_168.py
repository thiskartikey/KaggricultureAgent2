import json
from kaggle_environments import make

env = make("kaggriculture", debug=True)
out = env.run(["policy.py", "policy.py"])

print("Step 168:")
print("Player 0 Action:", out[168][0].action)
print("Player 1 Action:", out[168][1].action)

# check if any step has BUY_LAND
found = False
for step_idx, step in enumerate(out):
    for p, agent in enumerate(step):
        if agent.action and 'market' in agent.action:
            for m in agent.action['market']:
                if m and m[0] == 'BUY_LAND':
                    print(f"BUY_LAND found at step {step_idx} for player {p}")
                    found = True

if not found:
    print("No BUY_LAND found in any step!")
