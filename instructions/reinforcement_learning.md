# Reinforcement Learning Details

The agent utilizes a Proximal Policy Optimization (PPO) model trained offline (e.g., via Kaggle notebooks or local GPUs) for global farmer scheduling.

## Model Training & Structure

- **Training Script**: [train_rl.py](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/train_rl.py) is used to configure and trigger PPO training.
- **Framework**: Offline training relies on `stable-baselines3` and `PyTorch`.
- **Model Output**: The final trained actor-critic weights are saved as [rl_weights.npz](file:///home/gytdrop/Documents/HACKATHONS/2026/kaggle/kagriculture/rl_weights.npz) to keep the submission bundle lightweight and dependency-free.

## Vectorization (`env_wrapper.py`)

The RL network accepts a flat floating-point feature vector. The conversion is handled by `obs_to_vec`:
- **State Features**: Normalizes numerical inputs such as current day/365, log cash scale, seed counts, farmer availability, land status, crop ages, pasture capacities, and animal health metrics.
- **Action Decoder**: Translates the discrete action output of the network back into structured game actions (`macro_to_farmer_op`).

## Inference (`rl_inference.py`)

- **Implementation**: Implements a simple feedforward neural network in pure NumPy to run the actor network forward pass.
- **Weight Loading**: Dynamically reconstructs weights from the `.npz` file mapping.
