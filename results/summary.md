# Evaluation Summary

| Algorithm | Mean throughput (B/s) | Mean RTT (ms) | Loss rate |
|---|---:|---:|---:|
| TCP-DQN | 2240714.25 | 56.99 | 0.000161 |
| NewReno | 1493697.55 | 56.93 | 0.000199 |
| Cubic | 1978982.66 | 56.87 | 0.000196 |
| HighSpeed | 2096466.54 | 56.92 | 0.000196 |

## TCP-DQN speedup vs baselines

- vs NewReno: **1.50x**
- vs Cubic: **1.13x**
- vs HighSpeed: **1.07x**
