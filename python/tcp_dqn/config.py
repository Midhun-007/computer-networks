"""YAML/dataclass configuration loaders."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LINK_CONFIG = REPO_ROOT / "configs" / "link_default.yaml"
DEFAULT_DQN_CONFIG = REPO_ROOT / "configs" / "dqn_default.yaml"


@dataclass
class LinkConfig:
    bandwidth_mbps: float = 67.8
    base_rtt_ms: float = 56.0
    loss_rate: float = 0.0001
    segment_size: int = 1460
    queue_packets: int = 325
    sim_time_s: float = 600.0
    seed: int = 42

    @classmethod
    def from_yaml(cls, path: Path | None = None) -> "LinkConfig":
        path = path or DEFAULT_LINK_CONFIG
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


@dataclass
class DqnConfig:
    gamma: float = 0.99
    learning_rate: float = 0.0005
    buffer_size: int = 50000
    exploration_fraction: float = 0.1
    exploration_initial_eps: float = 1.0
    exploration_final_eps: float = 0.02
    policy_net_arch: List[int] = field(default_factory=lambda: [64, 64])
    total_timesteps: int = 60000
    alpha: float = 0.5
    time_step_s: float = 0.1
    seed: int = 42
    tensorboard_log: str = "results/tensorboard/"

    @classmethod
    def from_yaml(cls, path: Path | None = None) -> "DqnConfig":
        path = path or DEFAULT_DQN_CONFIG
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


def ns3_dir() -> Path:
    return REPO_ROOT / "ns-3"
