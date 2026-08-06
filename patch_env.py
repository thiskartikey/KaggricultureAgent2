import re

with open("env_wrapper.py", "r") as f:
    content = f.read()

calc_nw_func = """
def calc_net_worth(obs, player):
    me = obs["farms"][player]
    priv = obs.get("private", {}) or {}
    money = float(me.get("money", 0.0))
    
    seeds = priv.get("seeds", {}) or {}
    money += seeds.get("MELON", 0) * 80
    money += seeds.get("CARROT", 0) * 20
    money += seeds.get("WHEAT", 0) * 10
    
    shed = priv.get("shed", {}) or {}
    vals = {"MELON": 250, "CARROT": 35, "WHEAT": 25, "TOMATO": 60, "STRAWBERRY": 120}
    for k, v in shed.items():
        money += v * vals.get(k, 50)
        
    tiles = me.get("tiles") or []
    for row in tiles:
        for t in row:
            if isinstance(t, dict) and t.get("kind") == "PLANT":
                money += vals.get(t.get("crop"), 50) * 0.5
    return money

class KagrEnv
"""
content = content.replace("class KagrEnv", calc_nw_func.strip())

content = content.replace("self._prev_money = self._obs[\"farms\"][0].get(\"money\", 3000.0)", "self._prev_money = calc_net_worth(self._obs, 0)")

step_logic = """
        new_money = calc_net_worth(new_obs, 0)
        opp_money = calc_net_worth(new_obs, 1)
        reward = float(new_money - self._prev_money)
        self._prev_money = new_money
        self._obs = new_obs

        if done:
            self._done = True
            reward += 5000.0 if new_obs["farms"][0].get("money", 0) > new_obs["farms"][1].get("money", 0) else -5000.0
"""
content = re.sub(r'        new_money = new_obs\["farms"\]\[0\].get\("money", self\._prev_money\)\n        opp_money = new_obs\["farms"\]\[1\].get\("money", 0\.0\)\n        reward = float\(new_money - self\._prev_money\)\n        self\._prev_money = new_money\n        self\._obs = new_obs\n\n        if done:\n            self\._done = True\n            reward \+= 5000\.0 if new_money > opp_money else -5000\.0', step_logic.strip(), content)

with open("env_wrapper.py", "w") as f:
    f.write(content)
print("Patched env_wrapper.py!")
