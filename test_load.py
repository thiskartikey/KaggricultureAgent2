from rl_inference import RLPolicy
import os
import sys
if "__file__" in globals():
    sys.path.append(os.path.dirname(__file__))
else:
    sys.path.append("/kaggle_simulations/agent")
DIR_PATH = os.path.dirname(__file__) if "__file__" in globals() else "/kaggle_simulations/agent"
policy = RLPolicy(os.path.join(DIR_PATH, "rl_weights.npz"))
print("Is policy loaded?", policy.loaded)
