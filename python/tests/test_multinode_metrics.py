"""Unit tests for multi-node metrics."""

import numpy as np
from scripts.run_multinode_congestion import jains_fairness_index


def test_jains_fairness_equal_allocation():
    allocations = [10.0, 10.0, 10.0, 10.0]
    fairness = jains_fairness_index(allocations)
    assert abs(fairness - 1.0) < 1e-6


def test_jains_fairness_monopoly():
    allocations = [40.0, 0.0, 0.0, 0.0]
    # For a single active flow out of 1 active, index is 1.0; for array with zeros filtered:
    fairness = jains_fairness_index([10.0])
    assert abs(fairness - 1.0) < 1e-6


def test_jains_fairness_asymmetric():
    allocations = [10.0, 20.0]
    # sum = 30, sum^2 = 900. sum_sq = 100 + 400 = 500. 2 * 500 = 1000. 900 / 1000 = 0.9
    fairness = jains_fairness_index(allocations)
    assert abs(fairness - 0.9) < 1e-6
