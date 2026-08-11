import json

def check_unlocks(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    steps = data.get("steps", [])
    if not steps: return
    
    for p_idx in [0, 1]:
        unlocks = set()
        for step in steps:
            obs = step[p_idx].get("observation", {})
            farms = obs.get("farms", {})
            if len(farms) > p_idx:
                me = farms[p_idx]
                u = tuple(me.get("unlocked_quadrants", []))
                unlocks.add(u)
        print(f"Player {p_idx} unlocks over game: {unlocks}")

if __name__ == "__main__":
    check_unlocks("downloads/p2_v2_failure/f2/91735093.json")
    check_unlocks("downloads/p2_v2_failure/f2/91735339.json")
