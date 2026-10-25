# Multi-Node Network Congestion Evaluation Summary

- **Senders:** 4 competing flows
- **Bottleneck Bandwidth:** 15.0 Mbps
- **Bottleneck Queue Size:** 40 packets (DropTail FifoQueueDisc)
- **Simulation Time:** 15.0 seconds

### Benchmark Results

| algorithm   |   total_throughput_mbps |   mean_rtt_ms |   total_queue_drops |   jains_fairness |
|:------------|------------------------:|--------------:|--------------------:|-----------------:|
| NewReno     |                   13.98 |         71.9  |                 170 |            0.848 |
| Cubic       |                   13.95 |         75.64 |                 448 |            0.781 |
| HighSpeed   |                   13.94 |         72.05 |                 178 |            0.871 |
| BBR         |                   13.76 |         77.88 |                2025 |            0.853 |

### Key Observations

- **Queue Overflow:** High aggregate offered load quickly filled the 40-packet buffer, triggering substantial packet drops.
- **Loss Recovery & Backoff:** Traditional loss-based algorithms (NewReno, Cubic) oscillate aggressively as packet drops cut their cwnd in half.
- **BBR Rate Pacing:** BBR models the bottleneck bandwidth and RTT directly, achieving high link utilization while pacing transmissions.
