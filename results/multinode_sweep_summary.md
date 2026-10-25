# Multi-Node Network Congestion Sweep Summary

- **Evaluated Algorithms:** NewReno, Cubic, HighSpeed, BBR, TCP-DQN
- **Node Counts:** [np.int64(2), np.int64(4), np.int64(6), np.int64(8), np.int64(10)]
- **Bottleneck Bandwidth:** 15.0 Mbps
- **Bottleneck Queue Capacity:** 40 packets (DropTail FIFO)
- **Simulation Time:** 15.0 seconds

### Benchmark Data Table

| algorithm   |   nodes |   total_throughput_mbps |   mean_rtt_ms |   total_queue_drops |   jains_fairness |
|:------------|--------:|------------------------:|--------------:|--------------------:|-----------------:|
| NewReno     |       2 |                   14.27 |         88.48 |                  74 |            0.994 |
| Cubic       |       2 |                   14.24 |         98.72 |                 114 |            0.984 |
| HighSpeed   |       2 |                   13.93 |         90.08 |                 125 |            0.999 |
| BBR         |       2 |                   13.66 |         92.22 |                 789 |            0.966 |
| TcpDqn      |       2 |                    8.69 |         83.83 |                 960 |            0.95  |
| NewReno     |       4 |                   14.27 |         96.21 |                 180 |            0.998 |
| Cubic       |       4 |                   13.37 |         97.82 |                 594 |            0.99  |
| HighSpeed   |       4 |                   14.18 |         94.69 |                 267 |            0.987 |
| BBR         |       4 |                   13.12 |         99.35 |                1552 |            0.961 |
| TcpDqn      |       4 |                    9.51 |         81.67 |                3064 |            0.778 |
| NewReno     |       6 |                   14.32 |        103.84 |                 222 |            0.942 |
| Cubic       |       6 |                   13.53 |        102.09 |                 711 |            0.96  |
| HighSpeed   |       6 |                   14.35 |        102.69 |                 329 |            0.992 |
| BBR         |       6 |                   12.13 |        102.87 |                2413 |            0.986 |
| TcpDqn      |       6 |                    9.84 |         80.4  |                5044 |            0.986 |
| NewReno     |       8 |                   14.27 |        105.2  |                 112 |            0.963 |
| Cubic       |       8 |                   14.4  |        106.96 |                 436 |            0.988 |
| HighSpeed   |       8 |                   14.4  |        104.45 |                 382 |            0.974 |
| BBR         |       8 |                   13.51 |        101.37 |                2609 |            0.975 |
| TcpDqn      |       8 |                   12.06 |         87.17 |                6322 |            0.976 |
| NewReno     |      10 |                   14.33 |        105.05 |                 200 |            0.94  |
| Cubic       |      10 |                   14.44 |        111.1  |                 547 |            0.953 |
| HighSpeed   |      10 |                   14.45 |        106.94 |                 521 |            0.985 |
| BBR         |      10 |                   13.89 |        103.03 |                3153 |            0.976 |
| TcpDqn      |      10 |                   12.57 |         81.11 |                7805 |            0.955 |

