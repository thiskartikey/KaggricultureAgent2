"""Train PPO agent on Kaggriculture, save weights as numpy for zero-dep inference.

Usage:
    python train_rl.py              # trains for 500k steps (~20 min)
    python train_rl.py --steps 1000000
"""
import argparse, os, sys, numpy as np

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=500_000)
    ap.add_argument("--out",   default="rl_weights.npz")
    ap.add_argument("--n_envs", type=int, default=4)
    args = ap.parse_args()

    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor
    from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
    from env_wrapper import KagrEnv

    def make_env(rank):
        def _init():
            env = KagrEnv(opponent="starter")
            return env
        return _init

    print(f"Creating {args.n_envs} envs...")
    vec_env = SubprocVecEnv([make_env(i) for i in range(args.n_envs)])
    vec_env = VecMonitor(vec_env)

    eval_env = KagrEnv(opponent="starter")

    model = PPO(
        "MlpPolicy",
        vec_env,
        n_steps=1024,
        batch_size=256,
        n_epochs=10,
        gamma=0.995,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        learning_rate=3e-4,
        policy_kwargs=dict(net_arch=[256, 256, 128]),
        verbose=1,
        tensorboard_log="./rl_logs/",
    )

    checkpoint_cb = CheckpointCallback(
        save_freq=max(50_000 // args.n_envs, 1),
        save_path="./rl_checkpoints/",
        name_prefix="kagr_ppo",
    )
    eval_cb = EvalCallback(
        eval_env,
        n_eval_episodes=3,
        eval_freq=max(50_000 // args.n_envs, 1),
        best_model_save_path="./rl_best/",
        verbose=1,
    )

    print(f"Training for {args.steps} steps...")
    model.learn(args.steps, callback=[checkpoint_cb, eval_cb], progress_bar=False)

    # Save best model as SB3 format
    model.save("rl_final_model")
    print("Saved rl_final_model.zip")

    # Also export weights as numpy for zero-dependency inference
    export_weights(model, args.out)
    print(f"Exported numpy weights → {args.out}")

    vec_env.close()


def export_weights(model, out_path):
    """Extract MLP policy weights into a .npz file for numpy-only inference."""
    policy = model.policy
    params = {}

    # SB3 MlpPolicy stores layers in policy.mlp_extractor and policy.action_net
    state = policy.state_dict()
    for k, v in state.items():
        params[k.replace(".","__")] = v.cpu().numpy()

    np.savez_compressed(out_path, **params)
    print(f"Keys saved: {list(params.keys())[:8]} ...")


if __name__ == "__main__":
    main()
