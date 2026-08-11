import json

def check_hiring(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    steps = data.get("steps", [])
    if not steps: return
    
    for p_idx in [0]:
        print(f"--- Player {p_idx} in {file_path} ---")
        for step_idx, step in enumerate(steps):
            obs = step[p_idx].get("observation", {})
            farms = obs.get("farms", {})
            if len(farms) > p_idx:
                me = farms[p_idx]
                day = obs.get("day", 0)
                hour = obs.get("hour", 0)
                hires_today = me.get("hires_today", 0)
                hands = len(me.get("hands", []))
                money = me.get("money", 0)
                
                raw_action = step[p_idx].get("action", {})
                market_orders = raw_action.get("market", [])
                hires_in_action = sum(1 for m in market_orders if m[0] == "HIRE")
                
                if hires_in_action > 0 or hires_today > 15:
                    print(f"Day {day} Hour {hour}: hands={hands} hires_today={hires_today} money={money:.1f} action_hires={hires_in_action}")
        print()

if __name__ == "__main__":
    check_hiring("downloads/p2_v2_failure/f2/91735339.json")
