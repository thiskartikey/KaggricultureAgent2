from kaggle_environments import make
import importlib.util

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])

for i, step in enumerate(env.steps):
    me = step[0].observation.farms[0]
    market = step[0].observation.market
    day = step[0].observation.day
    if day == 11 and step[0].observation.hour == 0:
        print("Day 11 farm keys:", dir(me))
        print("dict version:", dict(me))
        print("Day 11 market MELON base_price:", market["MELON"]["base_price"], "inv:", market["MELON"]["inventory"])
        break
