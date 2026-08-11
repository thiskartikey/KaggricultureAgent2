import json

def print_tiles(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    steps = data.get("steps", [])
    if not steps: return
    
    # Just grab step 100
    step = steps[100]
    for p_idx in [0, 1]:
        obs = step[p_idx].get("observation", {})
        farms = obs.get("farms", {})
        if len(farms) > p_idx:
            me = farms[p_idx]
            tiles = me.get("tiles", [])
            print(f"Player {p_idx} unlocked_quadrants: {me.get('unlocked_quadrants')}")
            print(f"Tiles dimensions: {len(tiles)}x{len(tiles[0]) if tiles else 0}")
            # Print a quick map
            for y, row in enumerate(tiles):
                row_str = ""
                for x, t in enumerate(row):
                    if t is None:
                        row_str += "."
                    elif isinstance(t, str):
                        row_str += "X" if t == "LOCKED" else t[0]
                    elif isinstance(t, dict):
                        kind = t.get("kind", "?")
                        row_str += kind[0]
                print(row_str)
            print("-" * 20)

if __name__ == "__main__":
    print_tiles("downloads/p2_v2_failure/f2/91734538.json")
