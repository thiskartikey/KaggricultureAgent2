from kaggle_environments import make
import policy

env = make("kaggriculture", debug=True)
env.run(["ml_main.py", "versions/heuristic_v7.py"])

last_step = env.steps[-1]
obs = last_step[0]["observation"]

for p in [0, 1]:
    farm = obs["farms"][p]
    print(f"\n--- Player {p} Final Stats ---")
    print("Money:", farm.get("money"))
    
    # Count animals
    animals = {"COW": 0, "SHEEP": 0, "GOOSE": 0}
    tiles = farm.get("tiles", [])
    for row in tiles:
        for t in row:
            if isinstance(t, dict) and t.get("animal"):
                animals[t["animal"]] += 1
    print("Placed Animals:", animals)
    
    # Unlocked quadrants
    print("Unlocked Quadrants:", farm.get("unlocked_quadrants"))
    
    # Total score
    print("Total Reward:", last_step[p].get("reward"))
