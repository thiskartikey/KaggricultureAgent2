from kaggle_environments import make
import importlib.util

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])

for step_idx, step in enumerate(env.steps):
    action = step[0].get("action", {})
    if isinstance(action, dict):
        market = action.get("market", [])
        for order in market:
            if order[0] in ("HIRE", "BUY_SEED", "BUY_ANIMAL", "SELL"):
                print(f"Day {step_idx//24} Hour {step_idx%24} MARKET: {order}")

score1 = env.steps[-1][0]["reward"]
print(f"My agent score: {score1}")
