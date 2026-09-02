"""Reward function mirror of C++ TcpDqnEnv::ComputeReward (Eq. 6)."""

from __future__ import annotations


def compute_reward(
    throughput: float,
    throughput_max: float,
    rtt_ms: float,
    rtt_min_ms: float,
    rtt_max_ms: float,
    alpha: float,
) -> float:
    """
    Paper Eq. (6). T_min is undefined in the paper; we assume T_min = 0.
    Returns 0 when denominator ranges are not yet established.
    """
    throughput_min = 0.0
    t_denom = throughput_max - throughput_min
    r_denom = rtt_max_ms - rtt_min_ms

    if t_denom <= 0.0 or r_denom <= 0.0:
        return 0.0

    throughput_term = alpha * (throughput - throughput_min) / t_denom
    rtt_term = (1.0 - alpha) * (rtt_ms - rtt_min_ms) / r_denom
    return float(throughput_term - rtt_term)
