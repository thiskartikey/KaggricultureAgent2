from kaggle_environments import make
import sys
try:
    env = make("kaggriculture", debug=True)
    env.run(["revancedmain.py", "starter"])
    print("FINISHED SUCCESSFULLY")
except Exception as e:
    import traceback
    traceback.print_exc()
