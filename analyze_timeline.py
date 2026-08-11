import json
import numpy as np

def analyze_timeline(file_path):
    print(f"\n{'='*40}")
    print(f"Deep Analysis: {file_path}")
    print(f"{'='*40}")
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    steps = data.get("steps", [])
    if not steps:
        return
        
    for p_idx in [0, 1]:
        print(f"\n--- Player {p_idx} ---")
        
        hands_passed = 0
        hands_total_actions = 0
        invalid_moves = 0
        
        wheat_starvations = 0
        
        for t, step in enumerate(steps):
            action = step[p_idx].get("action")
            if not action:
                continue
                
            obs = step[p_idx].get("observation", {})
            priv = obs.get("private", {})
            shed = priv.get("shed", {})
            
            # Check Hands
            for h_act in action.get("hands", []):
                if not h_act: continue
                hands_total_actions += 1
                if h_act[0] == "PASS":
                    hands_passed += 1
                elif h_act[0] == "FEED" and shed.get("WHEAT", 0) == 0:
                    wheat_starvations += 1
                    
            f_act = action.get("farmer", [])
            if f_act:
                if f_act[0] == "FEED" and shed.get("WHEAT", 0) == 0:
                    wheat_starvations += 1
                    
        final_obs = steps[-1][p_idx].get("observation", {})
        final_priv = final_obs.get("private", {})
        final_shed = final_priv.get("shed", {})
        
        print(f"Total Hand Actions: {hands_total_actions}")
        print(f"Total Hand PASSes: {hands_passed} ({hands_passed/max(1, hands_total_actions)*100:.1f}%)")
        print(f"Attempted FEED with 0 WHEAT in shed: {wheat_starvations}")
        
        # Look at unplaced items at the end of the game
        print("End of game shed inventory:")
        print({k: v for k, v in final_shed.items() if v > 0})

if __name__ == "__main__":
    analyze_timeline("downloads/p2_v2_failure/f2/91735093.json")
    analyze_timeline("downloads/p2_v2_failure/f2/91735339.json")
    analyze_timeline("downloads/p2_v2_failure/f2/91734538.json")
