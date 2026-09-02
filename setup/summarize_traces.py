#!/usr/bin/env python3
"""Quick summary of baseline trace CSVs."""
from pathlib import Path
import pandas as pd

trace_dir = Path.home() / "tcp-dqn-ns3" / "results" / "traces"
for csv in sorted(trace_dir.glob("*.csv")):
    df = pd.read_csv(csv)
    mean_tp = df["throughput_Bps_since_last_sample"].mean()
    mean_rtt = df["rtt_ms"].mean()
    loss = df["cumulative_lost_segments"].iloc[-1] if len(df) else 0
    print(f"{csv.stem:20s}  mean_tp={mean_tp:12.1f} B/s  mean_rtt={mean_rtt:6.2f} ms  lost={loss:.0f}")
