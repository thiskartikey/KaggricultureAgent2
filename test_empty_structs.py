from kaggle_environments import make
import importlib.util

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

old_agent = main._agent
def wrapped_agent(obs):
    res = old_agent(obs)
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    if hour == 23:
        me = obs.get("players")[obs.get("player")]
        farm = me.get("farm", {})
        empty = 0
        tiles = farm.get("tiles", [])
        for row in tiles:
            for t in row:
                if isinstance(t, dict) and t.get("kind") in ("COOP", "PASTURE") and not t.get("animal"):
                    empty += 1
        print(f"Day {day} end: {empty} empty structures, money: {farm.get('money')}")
    return res

main._agent = wrapped_agent

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
