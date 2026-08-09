import os
import sys

DIR_PATH = os.path.dirname(__file__) if "__file__" in globals() else "/kaggle_simulations/agent"
if DIR_PATH not in sys.path:
    sys.path.append(DIR_PATH)

import policy


def agent(obs, config=None):
    return policy.agent(obs, config)
