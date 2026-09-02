#!/usr/bin/env python3
"""Train TCP-DQN agent against live ns-3 simulation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "python"))

from tcp_dqn.agent import train_agent
from tcp_dqn.config import DqnConfig, LinkConfig
from tcp_dqn.env import TcpDqnNs3Env


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train TCP-DQN with SB3")
    p.add_argument("--timesteps", type=int, default=None, help="Training timesteps")
    p.add_argument("--link-config", type=Path, default=None)
    p.add_argument("--dqn-config", type=Path, default=None)
    p.add_argument("--model-out", type=Path, default=REPO_ROOT / "results" / "models" / "tcp_dqn")
    p.add_argument("--plot-out", type=Path, default=REPO_ROOT / "results" / "plots" / "training_reward_curve.png")
    p.add_argument("--sim-time-s", type=float, default=None, help="Override per-episode simulation time")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    link_cfg = LinkConfig.from_yaml(args.link_config)
    dqn_cfg = DqnConfig.from_yaml(args.dqn_config)
    if args.sim_time_s is not None:
        link_cfg.sim_time_s = args.sim_time_s

    env = TcpDqnNs3Env(link_cfg=link_cfg, dqn_cfg=dqn_cfg)
    model = train_agent(
        env,
        total_timesteps=args.timesteps,
        model_path=args.model_out,
        cfg=dqn_cfg,
    )

    # SB3 stores episode rewards on the model's logger when available
    rewards = []
    if hasattr(model, "ep_info_buffer") and len(model.ep_info_buffer) > 0:
        rewards = [ep["r"] for ep in model.ep_info_buffer if "r" in ep]

    if rewards:
        plt.figure(figsize=(8, 4))
        plt.plot(rewards)
        plt.xlabel("Episode")
        plt.ylabel("Episode reward")
        plt.title("TCP-DQN training reward curve")
        args.plot_out.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(args.plot_out, dpi=150)
        plt.close()
        print(f"Saved training curve to {args.plot_out}")

    env.close()
    print(f"Saved model to {args.model_out}.zip")


if __name__ == "__main__":
    main()
