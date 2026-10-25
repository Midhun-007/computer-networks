# Evaluation Summary

| Algorithm | Mean throughput (B/s) | Mean RTT (ms) | Loss rate |
|---|---:|---:|---:|
| TCP-DQN | 2217436.24 | 57.11 | 0.000005 |
| NewReno | 1149526.53 | 57.05 | 0.000002 |
| Cubic | 2034465.31 | 56.99 | 0.000002 |
| HighSpeed | 1860457.14 | 56.99 | 0.000001 |

## TCP-DQN speedup vs baselines

- vs NewReno: **1.93x**
- vs Cubic: **1.09x**
- vs HighSpeed: **1.19x**
