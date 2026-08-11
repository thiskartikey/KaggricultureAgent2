from kaggle_environments import make
import policy

env = make("kaggriculture", debug=True)
out = env.run(["policy.py", "policy.py"])

print("Final scores:", [agent.reward for agent in out[-1]])

planted = [0, 0]
watered = [0, 0]
harvested = [0, 0]

for step_idx, step in enumerate(out):
    for p, agent in enumerate(step):
        if agent.action:
            if step_idx < 10 or (step_idx > 10 and len(agent.action.get('market', [])) > 0):
                d = step[0].observation.get('day', 0)
                h = step[0].observation.get('hour', 0)
                print(f"Step {step_idx} Day {d} Hour {h} Player {p} Action: {agent.action}")
            # Action is a dict: {'farmer': [...], 'hands': [[...], ...], 'market': [...]}
            all_acts = []
            if "farmer" in agent.action:
                all_acts.append(agent.action["farmer"])
            if "hands" in agent.action:
                all_acts.extend(agent.action["hands"])
            
            for act in all_acts:
                if act and len(act) > 0:
                    if act[0] == "PLANT":
                        planted[p] += 1
                    if act[0] == "WATER":
                        watered[p] += 1
                    if act[0] == "HARVEST":
                        harvested[p] += 1
                    if act[0] == "BUY_LAND":
                        print(f"Step {step_idx} Player {p} UNLOCKED QUADRANT!")

print(f"Player 0: Planted {planted[0]}, Watered {watered[0]}, Harvested {harvested[0]}")
print(f"Player 1: Planted {planted[1]}, Watered {watered[1]}, Harvested {harvested[1]}")
