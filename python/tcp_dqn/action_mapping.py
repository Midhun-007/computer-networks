"""Action mapping mirror of C++ TcpDqnEnv helpers."""

from __future__ import annotations

from .constants import ACTION_CENTER, ACTION_DIM


def action_index_to_delta_segments(action_index: int) -> int:
    if action_index < 0 or action_index >= ACTION_DIM:
        action_index = ACTION_CENTER
    return action_index - ACTION_CENTER


def apply_cwnd_delta(cwnd_bytes: int, delta_segments: int, segment_size: int) -> int:
    new_cwnd = cwnd_bytes + delta_segments * segment_size
    return max(segment_size, new_cwnd)
