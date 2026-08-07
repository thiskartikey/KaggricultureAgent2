import os
import sys
import numpy as np

if "__file__" in globals():
    sys.path.append(os.path.dirname(__file__))
else:
    sys.path.append("/kaggle_simulations/agent")

from rl_inference import RLPolicy
from env_wrapper import obs_to_vec, macro_to_farmer_op, resolve_farmer_op

# Initialize policy lazily to avoid issues during Kaggle's agent
DIR_PATH = os.path.dirname(__file__) if "__file__" in globals() else "/kaggle_simulations/agent"

# Global policy instance (lazy load)
policy = None

def agent(obs, conf=None):
    global policy
    if policy is None:
        policy = RLPolicy(os.path.join(DIR_PATH, "rl_weights.npz"))
    
    player = obs.get("player", 0)
    
    # 1. Convert obs to vector
    obs_vec = obs_to_vec(obs, player)
    
    # 2. Get action from policy
    action_id = policy.predict(obs_vec)
    
    # 3. Convert macro action back to farmer op
    # We also need market orders. We can instantiate a dummy KagrEnv to use its helpers,
    # or we can extract the helper logic.
    from env_wrapper import KagrEnv
    # Instead of full KagrEnv, we can just use the methods we need.
    dummy_env = KagrEnv()
    dummy_env.player = player
    
    priv = obs.get("private", {}) or {}
    raw_op = macro_to_farmer_op(action_id, obs, player)
    farmer_op = resolve_farmer_op(raw_op, obs, player, priv)
    
    # Check if we need to buy seeds for a PLANT operation
    if str(raw_op[0]).startswith("__PLANT__"):
        crop = str(raw_op[0])[9:]
        seed_order = dummy_env._buy_seed_if_needed(obs, crop, player)
        if seed_order:
            market_orders = [seed_order]
        else:
            market_orders = []
    else:
        market_orders = dummy_env._make_market_orders(obs, player)
        
    n_hands = len(obs["farms"][player].get("hands") or [])
    hands = []
    for _ in range(n_hands):
        hands.append(resolve_farmer_op(raw_op, obs, player, priv))

    return {
        "farmer": farmer_op,
        "hands": hands,
        "market": market_orders
    }
