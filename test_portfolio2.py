from kaggle_environments import make
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

old_plan = main.plan_portfolio
def wrapped_plan(*args, **kwargs):
    orders, seeds = old_plan(*args, **kwargs)
    day = args[1]
    if orders or seeds:
        print(f"Day {day} plan_portfolio -> orders: {orders}, seeds: {seeds}", file=sys.stderr)
    return orders, seeds

main.plan_portfolio = wrapped_plan

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
