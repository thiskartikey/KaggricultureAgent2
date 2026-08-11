import policy
obs = {
    "player": 0,
    "day": 0,
    "hour": 1,
    "step": 1,
    "farms": [{"money": 3000, "tiles": [[None]*10]*10, "farmer": [4,4]}],
    "private": {"shed": {}},
    "market": {"inventory": {}}
}
try:
    print(policy._agent(obs, 30))
except Exception as e:
    import traceback
    traceback.print_exc()
