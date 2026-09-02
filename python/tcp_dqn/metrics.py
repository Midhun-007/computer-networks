"""Load CSV traces and build comparison metrics/plots."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import pandas as pd

TRACE_COLUMNS = [
    "time_s",
    "cwnd_segments",
    "rtt_ms",
    "throughput_Bps_since_last_sample",
    "cumulative_lost_segments",
]


def load_trace(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in TRACE_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"Trace {path} missing column {col}")
    return df


def summarize_trace(df: pd.DataFrame, sim_time_s: float) -> Dict[str, float]:
    mean_tp = float(df["throughput_Bps_since_last_sample"].mean())
    mean_rtt = float(df["rtt_ms"].mean())
    final_loss = float(df["cumulative_lost_segments"].iloc[-1]) if len(df) else 0.0
    total_pkts_est = max(1.0, mean_tp * sim_time_s / 1460.0)
    loss_rate = final_loss / total_pkts_est
    return {
        "mean_throughput_Bps": mean_tp,
        "mean_rtt_ms": mean_rtt,
        "packet_loss_count": final_loss,
        "packet_loss_rate": loss_rate,
    }


def plot_time_series(
    traces: Dict[str, pd.DataFrame],
    column: str,
    ylabel: str,
    out_path: Path,
    title: str,
) -> None:
    plt.figure(figsize=(10, 5))
    for name, df in traces.items():
        plt.plot(df["time_s"], df[column], label=name, linewidth=1.2)
    plt.xlabel("Time (s)")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150)
    plt.close()


def plot_cdf(traces: Dict[str, pd.DataFrame], column: str, out_path: Path, title: str) -> None:
    plt.figure(figsize=(8, 5))
    for name, df in traces.items():
        values = df[column].sort_values().to_numpy()
        if len(values) == 0:
            continue
        y = (pd.Series(range(1, len(values) + 1)) / len(values)).to_numpy()
        plt.plot(values, y, label=name, linewidth=1.2)
    plt.xlabel(column)
    plt.ylabel("CDF")
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150)
    plt.close()


def plot_loss_bars(summaries: Dict[str, Dict[str, float]], out_path: Path) -> None:
    names = list(summaries.keys())
    losses = [summaries[n]["packet_loss_rate"] for n in names]
    plt.figure(figsize=(8, 5))
    plt.bar(names, losses)
    plt.ylabel("Packet loss rate (approx.)")
    plt.title("Packet loss comparison")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150)
    plt.close()


def write_summary_md(
    summaries: Dict[str, Dict[str, float]],
    out_path: Path,
    baseline_names: List[str],
) -> None:
    lines = ["# Evaluation Summary\n"]
    dqn = summaries.get("TCP-DQN", summaries.get("tcp_dqn", {}))
    dqn_tp = dqn.get("mean_throughput_Bps", 0.0)

    lines.append("| Algorithm | Mean throughput (B/s) | Mean RTT (ms) | Loss rate |")
    lines.append("|---|---:|---:|---:|")
    for name, stats in summaries.items():
        lines.append(
            f"| {name} | {stats['mean_throughput_Bps']:.2f} | "
            f"{stats['mean_rtt_ms']:.2f} | {stats['packet_loss_rate']:.6f} |"
        )

    lines.append("\n## TCP-DQN speedup vs baselines\n")
    for base in baseline_names:
        base_tp = summaries.get(base, {}).get("mean_throughput_Bps", 0.0)
        if base_tp > 0:
            speedup = dqn_tp / base_tp
            lines.append(f"- vs {base}: **{speedup:.2f}x**")
        else:
            lines.append(f"- vs {base}: N/A")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
