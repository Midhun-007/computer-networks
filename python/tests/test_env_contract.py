"""Assert Python env contract matches C++ constants."""

import numpy as np

from tcp_dqn.constants import ACTION_DIM, OBS_DIM, OBS_HIGH, OBS_LOW
from tcp_dqn.env import TcpDqnNs3Env


def test_env_contract_without_ns3():
    """Validate spaces without launching ns-3 (no bridge)."""
    class _StubEnv(TcpDqnNs3Env):
        def _create_bridge(self):
            pass

    env = _StubEnv()
    assert env.observation_space.shape == (OBS_DIM,)
    assert env.observation_space.low.dtype == np.float64
    assert float(env.observation_space.low[0]) == OBS_LOW
    assert float(env.observation_space.high[0]) == OBS_HIGH
    assert env.action_space.n == ACTION_DIM
