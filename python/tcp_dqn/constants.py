"""Shared TCP-DQN constants mirrored from C++ (tcp-dqn-constants.h)."""

OBS_DIM = 7
ACTION_DIM = 101
ACTION_CENTER = 50
OBS_LOW = 0.0
OBS_HIGH = 1e9
DEFAULT_ALPHA = 0.5
DEFAULT_TIME_STEP_S = 0.1

OBS_NAMES = [
    "relative_time_s",
    "cwnd_segments",
    "bytes_in_flight",
    "ack_count",
    "avg_rtt_ms",
    "throughput_bps",
    "lost_segments",
]
