import json
import glob

def analyze_replay(file_path):
    print(f"\n{'='*40}")
    print(f"Analyzing Replay: {file_path}")
    print(f"{'='*40}")
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    steps = data.get("steps", [])
    if not steps:
        print("No steps found.")
        return

    final_step = steps[-1]
    
    for p_idx in [0, 1]:
        print(f"\n--- Player {p_idx} ---")
        print(f"Final Score: {final_step[p_idx].get('reward', 0)}")
        
        animals_bought = 0
        seeds_bought = 0
        products_sold = 0
        animals_sold = 0
        workers_hired = 0
        
        plants = 0
        harvests = 0
        cares = 0
        feeds = 0
        
        money_history = []
        wheat_history = []
        
        # Track items
        for t, step in enumerate(steps):
            obs = step[p_idx].get("observation", {})
            farms = obs.get("farms", {})
            if len(farms) > p_idx:
                me = farms[p_idx]
                money_history.append(me.get("money", 0))
                
                priv = obs.get("private", {})
                shed = priv.get("shed", {})
                wheat_history.append(shed.get("WHEAT", 0))
                
            action = step[p_idx].get("action")
            if not action:
                continue
                
            # Market
            for order in action.get("market", []):
                if not order: continue
                if order[0] == "HIRE":
                    workers_hired += 1
                elif order[0] == "BUY_ANIMAL":
                    animals_bought += order[2]
                elif order[0] == "BUY_SEED":
                    seeds_bought += order[2]
                elif order[0] == "SELL":
                    if order[1] in ["GOOSE", "COW", "SHEEP"]:
                        animals_sold += order[2]
                    else:
                        products_sold += order[2]
                    
            # Farmer
            f_act = action.get("farmer", [])
            if f_act:
                if f_act[0] == "PLANT": plants += 1
                elif f_act[0] == "HARVEST": harvests += 1
                elif f_act[0] == "CARE": cares += 1
                elif f_act[0] == "FEED": feeds += 1
                
            # Hands
            for h_act in action.get("hands", []):
                if not h_act: continue
                if h_act[0] == "PLANT": plants += 1
                elif h_act[0] == "HARVEST": harvests += 1
                elif h_act[0] == "CARE": cares += 1
                elif h_act[0] == "FEED": feeds += 1
                
        # Calculate escapes (bought vs alive at end + sold)
        final_obs = final_step[p_idx].get("observation", {})
        priv = final_obs.get("private", {})
        shed = priv.get("shed", {})
        final_farm = final_obs.get("farms", {})[p_idx]
        
        # Count animals on tiles
        animals_on_tiles = 0
        for row in final_farm.get("tiles", []):
            for tile in row:
                if isinstance(tile, dict):
                    if tile.get("kind") in ["COOP", "PASTURE"] and tile.get("animal"):
                        animals_on_tiles += 1
                        
        alive = shed.get('COW',0)+shed.get('SHEEP',0)+shed.get('GOOSE',0) + animals_on_tiles
        escaped = animals_bought - animals_sold - alive
        
        print(f"Workers Hired: {workers_hired}")
        print(f"Seeds Bought: {seeds_bought}")
        print(f"Products Sold: {products_sold}")
        print(f"Plants: {plants} | Harvests: {harvests}")
        print(f"Animals Bought: {animals_bought} | Sold: {animals_sold} | Alive: {alive} | Escaped: {escaped}")
        print(f"Feeds: {feeds} | Cares: {cares}")
        
        if money_history:
            print(f"Min Money: {min(money_history)} | Max Money: {max(money_history)}")
        if wheat_history:
            print(f"Min Wheat: {min(wheat_history)} | Max Wheat: {max(wheat_history)}")

if __name__ == "__main__":
    files = glob.glob("downloads/p2_v2_failure/f2/*.json")
    for f in files:
        analyze_replay(f)
