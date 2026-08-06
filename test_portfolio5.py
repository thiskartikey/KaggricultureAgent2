from kaggle_environments import make
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

old_plan_sells = main.plan_sells
def wrapped_plan_sells(*args, **kwargs):
    orders = old_plan_sells(*args, **kwargs)
    day = args[2]
    hour = args[3]
    if day == 15 and hour in (21, 22, 23):
        print(f"Day {day} Hour {hour} plan_sells orders: {orders}", file=sys.stderr)
    return orders

main.plan_sells = wrapped_plan_sells
env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
