"""Unit tests for TCP-DQN reward function."""

import pytest

from tcp_dqn.reward import compute_reward


def test_reward_zero_range_guard():
    assert compute_reward(100.0, 0.0, 50.0, 40.0, 60.0, 0.5) == 0.0


def test_reward_monotonic_throughput():
    r_low = compute_reward(500.0, 1000.0, 55.0, 50.0, 60.0, 0.5)
    r_high = compute_reward(900.0, 1000.0, 55.0, 50.0, 60.0, 0.5)
    assert r_high > r_low


def test_reward_monotonic_rtt():
    r_low_rtt = compute_reward(800.0, 1000.0, 52.0, 50.0, 60.0, 0.5)
    r_high_rtt = compute_reward(800.0, 1000.0, 58.0, 50.0, 60.0, 0.5)
    assert r_low_rtt > r_high_rtt


def test_reward_alpha_one_throughput_only():
    r = compute_reward(1000.0, 1000.0, 60.0, 50.0, 60.0, 1.0)
    assert r == pytest.approx(1.0)


def test_reward_alpha_zero_rtt_only():
    r = compute_reward(0.0, 1000.0, 60.0, 50.0, 60.0, 0.0)
    assert r == pytest.approx(-1.0)
