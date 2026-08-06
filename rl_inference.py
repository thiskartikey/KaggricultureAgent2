"""Zero-dependency numpy MLP inference — mirrors SB3 MlpPolicy architecture.

Load with:  net = RLPolicy("rl_weights.npz")
Predict:    action = net.predict(obs_vec)
"""
import numpy as np
import os

# Must match train_rl.py: net_arch=[256, 256, 128], N_ACTIONS=8
ARCH = [256, 256, 128]
N_ACTIONS = 8


def _relu(x):
    return np.maximum(0.0, x)


class RLPolicy:
    def __init__(self, weights_path):
        if not os.path.exists(weights_path):
            self._loaded = False
            return
        d = np.load(weights_path, allow_pickle=False)
        self._w = dict(d)
        self._loaded = True

    def predict(self, obs_vec):
        """Returns integer action (greedy argmax)."""
        if not self._loaded:
            return 7  # PASS fallback
        x = obs_vec.astype(np.float32).flatten()
        # shared MLP layers (mlp_extractor.policy_net)
        for i in range(len(ARCH)):
            W_key = f"mlp_extractor__policy_net__{i*2}__weight"
            b_key = f"mlp_extractor__policy_net__{i*2}__bias"
            if W_key not in self._w:
                return 7
            x = _relu(self._w[W_key] @ x + self._w[b_key])
        # action head (action_net)
        W = self._w.get("action_net__weight")
        b = self._w.get("action_net__bias")
        if W is None:
            return 7
        logits = W @ x + b
        return int(np.argmax(logits))

    @property
    def loaded(self):
        return self._loaded
