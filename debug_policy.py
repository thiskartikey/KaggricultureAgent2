import policy
obs = {
    "player": 0,
    "day": 0,
    "hour": 0,
    "step": 0,
    "farms": [{"money": 3000, "tiles": [], "farmer": [4,4]}],
    "private": {"shed": {}},
    "market": {"inventory": {}}
}
try:
    print(policy.agent(obs))
except Exception as e:
    import traceback
    traceback.print_exc()
