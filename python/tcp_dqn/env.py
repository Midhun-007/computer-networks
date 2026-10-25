"""Gymnasium wrapper around the ns3-ai bridge for TCP-DQN."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .config import DqnConfig, LinkConfig, ns3_dir
from .constants import ACTION_DIM, OBS_DIM, OBS_HIGH, OBS_LOW


class TcpDqnNs3Env(gym.Env):
    """Thin Gymnasium env over ns3ai_gym_env for tcp-dqn-topology."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        link_cfg: LinkConfig | None = None,
        dqn_cfg: DqnConfig | None = None,
        ns3_path: Path | None = None,
        sim_seed: int = 0,
    ):
        super().__init__()
        self.link_cfg = link_cfg or LinkConfig.from_yaml()
        self.dqn_cfg = dqn_cfg or DqnConfig.from_yaml()
        self.ns3_path = Path(ns3_path) if ns3_path else ns3_dir()
        self.sim_seed = sim_seed

        self.observation_space = spaces.Box(
            low=OBS_LOW, high=OBS_HIGH, shape=(OBS_DIM,), dtype=np.float64
        )
        self.action_space = spaces.Discrete(ACTION_DIM)

        self._env = None
        self._create_bridge()

    def _ns3_settings(self) -> Dict[str, Any]:
        return {
            "bandwidthMbps": self.link_cfg.bandwidth_mbps,
            "baseRttMs": self.link_cfg.base_rtt_ms,
            "lossRate": self.link_cfg.loss_rate,
            "queuePackets": self.link_cfg.queue_packets,
            "segmentSize": self.link_cfg.segment_size,
            "simTimeS": self.link_cfg.sim_time_s,
            "seed": self.link_cfg.seed,
            "alpha": self.dqn_cfg.alpha,
            "simSeed": self.sim_seed,
            "traceDir": str((self.ns3_path.parent / "results" / "traces").resolve()),
        }

    def _create_bridge(self) -> None:
        import ctypes
        core_lib = self.ns3_path / "build" / "lib" / "libns3.48-core-default.so"
        if core_lib.exists():
            ctypes.CDLL(str(core_lib), mode=ctypes.RTLD_GLOBAL)
        import ns3ai_gym_env  # noqa: F401

        self._env = gym.make(
            "ns3ai_gym_env/Ns3-v0",
            targetName="tcp-dqn-topology",
            ns3Path=str(self.ns3_path.resolve()),
            ns3Settings=self._ns3_settings(),
        )

    def reset(self, *, seed: Optional[int] = None, options: Optional[dict] = None):
        if seed is not None:
            np.random.seed(seed)
        obs, info = self._env.reset()
        return np.asarray(obs, dtype=np.float64), info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, dict]:
        obs, reward, terminated, truncated, info = self._env.step(int(action))
        done = bool(terminated or truncated)
        return np.asarray(obs, dtype=np.float64), float(reward), done, False, info

    def close(self) -> None:
        if self._env is not None:
            self._env.close()
            self._env = None
