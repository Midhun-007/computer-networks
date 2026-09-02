"""Unit tests for action mapping."""

from tcp_dqn.action_mapping import action_index_to_delta_segments, apply_cwnd_delta


def test_delta_mapping_corners():
    assert action_index_to_delta_segments(0) == -50
    assert action_index_to_delta_segments(50) == 0
    assert action_index_to_delta_segments(100) == 50


def test_cwnd_floor_one_segment():
    seg = 1460
    assert apply_cwnd_delta(seg, -50, seg) == seg
    assert apply_cwnd_delta(10 * seg, 50, seg) == 60 * seg
