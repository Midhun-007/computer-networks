# TCP-DQN Alpha Sensitivity Sweep Summary

- **Evaluated Alpha Values:** [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
- **Senders:** 4 competing TCP DQN flows
- **Bottleneck Bandwidth:** 15.0 Mbps
- **Bottleneck Queue Capacity:** 40 packets (DropTail FIFO)
- **Simulation Time:** 15.0 seconds

### Benchmark Data Table

|   alpha |   total_throughput_mbps |   mean_rtt_ms |   total_queue_drops |   jains_fairness |
|--------:|------------------------:|--------------:|--------------------:|-----------------:|
|     0   |                    9.93 |         76.61 |                1455 |            0.649 |
|     0.1 |                    9.91 |         76.53 |                1444 |            0.65  |
|     0.2 |                    7.65 |         79.1  |                1613 |            0.975 |
|     0.3 |                    6.85 |         78.47 |                1775 |            0.967 |
|     0.4 |                    6.85 |         78.47 |                1775 |            0.967 |
|     0.5 |                    9.51 |         81.67 |                3064 |            0.778 |
|     0.6 |                    6.66 |         73.4  |                3789 |            0.848 |
|     0.7 |                    6.66 |         73.4  |                3789 |            0.848 |
|     0.8 |                    6.66 |         73.4  |                3789 |            0.848 |
|     0.9 |                    6.66 |         73.4  |                3789 |            0.848 |
|     1   |                    6.66 |         73.4  |                3789 |            0.848 |

