"""Stable-Baselines3 DQN agent wrapper."""

from __future__ import annotations

from pathlib import Path

from stable_baselines3 import DQN

from .config import DqnConfig
from .env import TcpDqnNs3Env


def build_dqn_agent(env: TcpDqnNs3Env, cfg: DqnConfig | None = None) -> DQN:
    cfg = cfg or DqnConfig.from_yaml()
    policy_kwargs = dict(net_arch=cfg.policy_net_arch)
    return DQN(
        "MlpPolicy",
        env,
        gamma=cfg.gamma,
        learning_rate=cfg.learning_rate,
        buffer_size=cfg.buffer_size,
        exploration_fraction=cfg.exploration_fraction,
        exploration_initial_eps=cfg.exploration_initial_eps,
        exploration_final_eps=cfg.exploration_final_eps,
        policy_kwargs=policy_kwargs,
        verbose=1,
        tensorboard_log=cfg.tensorboard_log,
        seed=cfg.seed,
    )


def train_agent(
    env: TcpDqnNs3Env,
    total_timesteps: int | None = None,
    model_path: Path | None = None,
    cfg: DqnConfig | None = None,
) -> DQN:
    cfg = cfg or DqnConfig.from_yaml()
    model = build_dqn_agent(env, cfg)
    steps = total_timesteps or cfg.total_timesteps
    model.learn(total_timesteps=steps)
    if model_path:
        model_path.parent.mkdir(parents=True, exist_ok=True)
        model.save(str(model_path))
    return model
