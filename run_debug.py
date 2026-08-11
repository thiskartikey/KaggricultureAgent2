from kaggle_environments import make
import policy

env = make("kagriculture", debug=True)
env.run(["policy.py", "policy.py", "policy.py", "policy.py"])
