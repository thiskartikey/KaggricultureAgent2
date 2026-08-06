from kaggle_environments import make
import importlib.util

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])

for day in range(2):
    for step in env.steps:
        if step[0].observation.day == day and step[0].observation.hour == 0:
            me = step[0].observation.farms[0]
            print(f"Day {day} start seeds: {me.get('shed', {})}")
            break
