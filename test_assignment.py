from kaggle_environments import make
import importlib.util
import sys
import json

spec = importlib.util.spec_from_file_location("main", "revancedmain.py")
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

def wrapped_assign_tasks(unit_positions, tasks, day, hour):
    # Just print if we have an animal in our inventory
    return main.old_assign_tasks(unit_positions, tasks, day, hour)

# wait, we can just modify assign_tasks to prefer workers who ALREADY have the animal!
