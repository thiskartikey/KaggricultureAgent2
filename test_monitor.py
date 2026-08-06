from kaggle_environments import make
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

old_assign_tasks = main.assign_tasks
def wrapped_assign_tasks(unit_positions, tasks, day, hour, invs, board_size):
    for _, ops, _ in tasks:
        if ops and ops[0] == "BUILD_PASTURE":
            print(f"Day {day} hour {hour} assign_tasks received BUILD_PASTURE!", file=sys.stderr)
    return old_assign_tasks(unit_positions, tasks, day, hour, invs, board_size)

main.assign_tasks = wrapped_assign_tasks
old_agent = main._agent
def wrapped_agent(obs):
    res = old_agent(obs)
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    for r in [res.get("farmer", [])] + res.get("hands", []):
        if len(r) > 0 and r[0] == "BUILD_PASTURE":
            print(f"Day {day} hour {hour} ACTUALLY EXECUTING BUILD_PASTURE!", file=sys.stderr)
    return res

main._agent = wrapped_agent
main.agent = lambda obs, conf: wrapped_agent(obs)

env = make("kaggriculture", debug=True)
env.run([main.agent, "starter"])
