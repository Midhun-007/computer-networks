#!/usr/bin/env python3
"""Run multi-node congestion simulation across varying number of nodes for 5 TCP variants:
NewReno, Cubic, HighSpeed, BBR, and TCP DQN.
Generates plots for:
1. Throughput vs number of nodes
2. Mean RTT vs number of nodes
3. Packet drops vs number of nodes
4. Fairness index vs number of nodes
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "python"))

from tcp_dqn.config import ns3_dir


def parse_args():
    p = argparse.ArgumentParser(description="Multi-node sweep for TCP algorithms")
    p.add_argument("--algorithms", nargs="+", default=["NewReno", "Cubic", "HighSpeed", "BBR", "TcpDqn"])
    p.add_argument("--node-counts", type=int, nargs="+", default=[2, 4, 6, 8, 10])
    p.add_argument("--bottleneck-mbps", type=float, default=15.0)
    p.add_argument("--bottleneck-delay-ms", type=float, default=25.0)
    p.add_argument("--queue-packets", type=int, default=40)
    p.add_argument("--sim-time-s", type=float, default=15.0)
    p.add_argument("--plots-dir", type=Path, default=REPO_ROOT / "results" / "plots")
    p.add_argument("--traces-dir", type=Path, default=REPO_ROOT / "results" / "traces")
    p.add_argument("--skip-sim", action="store_true", help="Skip ns-3 runs and plot existing results CSV")
    return p.parse_args()


def jains_fairness_index(values: list[float] | np.ndarray) -> float:
    """Compute Jain's Fairness Index: (sum(x)^2) / (n * sum(x^2))."""
    arr = np.array(values, dtype=np.float64)
    arr = arr[arr > 0]
    if len(arr) == 0:
        return 0.0
    sum_x = np.sum(arr)
    sum_sq = np.sum(arr ** 2)
    return float((sum_x ** 2) / (len(arr) * sum_sq)) if sum_sq > 0 else 0.0


def run_simulation(algo: str, n_senders: int, args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    ns3 = ns3_dir()
    cmd = [
        str(ns3 / "ns3"),
        "run",
        (
            f"tcp-dqn-multinode-topology "
            f"--nSenders={n_senders} "
            f"--bottleneckMbps={args.bottleneck_mbps} "
            f"--bottleneckDelayMs={args.bottleneck_delay_ms} "
            f"--queuePackets={args.queue_packets} "
            f"--simTimeS={args.sim_time_s} "
            f"--transport_prot={algo} "
            f"--staggeredStarts=false "
            f"--traceDir={args.traces_dir.resolve()}"
        ),
    ]
    print(f"\n---> Running simulation: Algo={algo}, Nodes={n_senders}...")
    subprocess.run(cmd, cwd=ns3, check=True)

    flows_csv = args.traces_dir / f"multinode_flows_{algo}_n{n_senders}.csv"
    queue_csv = args.traces_dir / f"multinode_queue_{algo}_n{n_senders}.csv"

    flows_df = pd.read_csv(flows_csv)
    queue_df = pd.read_csv(queue_csv)
    return flows_df, queue_df


ALGO_DISPLAY_NAMES = {
    "NewReno": "NewReno",
    "Cubic": "Cubic",
    "HighSpeed": "HighSpeed",
    "BBR": "BBR",
    "TcpDqn": "TCP DQN",
}

ALGO_COLORS = {
    "NewReno": "#1f77b4",     # Blue
    "Cubic": "#ff7f0e",       # Orange
    "HighSpeed": "#2ca02c",   # Green
    "BBR": "#d62728",         # Red
    "TcpDqn": "#9467bd",      # Purple
}

ALGO_MARKERS = {
    "NewReno": "o",
    "Cubic": "s",
    "HighSpeed": "^",
    "BBR": "D",
    "TcpDqn": "P",
}


def plot_metrics(summary_df: pd.DataFrame, plots_dir: Path, bottleneck_mbps: float):
    plots_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    algos = summary_df["algorithm"].unique()
    node_counts = sorted(summary_df["nodes"].unique())

    # 1. Individual Plot: Throughput vs Number of Nodes
    fig1, ax1 = plt.subplots(figsize=(9, 6))
    for algo in algos:
        sub = summary_df[summary_df["algorithm"] == algo].sort_values("nodes")
        disp = ALGO_DISPLAY_NAMES.get(algo, algo)
        color = ALGO_COLORS.get(algo, None)
        marker = ALGO_MARKERS.get(algo, "o")
        ax1.plot(sub["nodes"], sub["total_throughput_mbps"], marker=marker, linewidth=2.4, markersize=8,
                 label=disp, color=color)

    ax1.axhline(bottleneck_mbps, color="black", linestyle="--", linewidth=1.5,
                label=f"Bottleneck Capacity ({bottleneck_mbps} Mbps)")
    ax1.set_xlabel("Number of Nodes (Competing Flows)", fontweight="bold", fontsize=12)
    ax1.set_ylabel("Total Bottleneck Throughput (Mbps)", fontweight="bold", fontsize=12)
    ax1.set_title("Throughput vs. Number of Nodes", fontweight="bold", fontsize=14, pad=12)
    ax1.set_xticks(node_counts)
    ax1.legend(loc="lower right", framealpha=0.9, fontsize=10)
    ax1.grid(True, linestyle="--", alpha=0.6)
    fig1.tight_layout()
    p1 = plots_dir / "throughput_vs_nodes.png"
    fig1.savefig(p1, dpi=300)
    plt.close(fig1)

    # 2. Individual Plot: Mean RTT vs Number of Nodes
    fig2, ax2 = plt.subplots(figsize=(9, 6))
    for algo in algos:
        sub = summary_df[summary_df["algorithm"] == algo].sort_values("nodes")
        disp = ALGO_DISPLAY_NAMES.get(algo, algo)
        color = ALGO_COLORS.get(algo, None)
        marker = ALGO_MARKERS.get(algo, "o")
        ax2.plot(sub["nodes"], sub["mean_rtt_ms"], marker=marker, linewidth=2.4, markersize=8,
                 label=disp, color=color)

    ax2.axhline(54.0, color="gray", linestyle=":", linewidth=1.5, label="Base Propagation RTT (~54 ms)")
    ax2.set_xlabel("Number of Nodes (Competing Flows)", fontweight="bold", fontsize=12)
    ax2.set_ylabel("Mean Round-Trip Time (RTT) [ms]", fontweight="bold", fontsize=12)
    ax2.set_title("Mean RTT vs. Number of Nodes", fontweight="bold", fontsize=14, pad=12)
    ax2.set_xticks(node_counts)
    ax2.legend(loc="upper left", framealpha=0.9, fontsize=10)
    ax2.grid(True, linestyle="--", alpha=0.6)
    fig2.tight_layout()
    p2 = plots_dir / "mean_rtt_vs_nodes.png"
    fig2.savefig(p2, dpi=300)
    plt.close(fig2)

    # 3. Individual Plot: Packet Drops vs Number of Nodes
    fig3, ax3 = plt.subplots(figsize=(9, 6))
    for algo in algos:
        sub = summary_df[summary_df["algorithm"] == algo].sort_values("nodes")
        disp = ALGO_DISPLAY_NAMES.get(algo, algo)
        color = ALGO_COLORS.get(algo, None)
        marker = ALGO_MARKERS.get(algo, "o")
        ax3.plot(sub["nodes"], sub["total_queue_drops"], marker=marker, linewidth=2.4, markersize=8,
                 label=disp, color=color)

    ax3.set_xlabel("Number of Nodes (Competing Flows)", fontweight="bold", fontsize=12)
    ax3.set_ylabel("Total Bottleneck Queue Drops (packets)", fontweight="bold", fontsize=12)
    ax3.set_title("Packet Drops vs. Number of Nodes", fontweight="bold", fontsize=14, pad=12)
    ax3.set_xticks(node_counts)
    ax3.legend(loc="upper left", framealpha=0.9, fontsize=10)
    ax3.grid(True, linestyle="--", alpha=0.6)
    fig3.tight_layout()
    p3 = plots_dir / "packet_drops_vs_nodes.png"
    fig3.savefig(p3, dpi=300)
    plt.close(fig3)

    # 4. Individual Plot: Fairness Index vs Number of Nodes
    fig4, ax4 = plt.subplots(figsize=(9, 6))
    for algo in algos:
        sub = summary_df[summary_df["algorithm"] == algo].sort_values("nodes")
        disp = ALGO_DISPLAY_NAMES.get(algo, algo)
        color = ALGO_COLORS.get(algo, None)
        marker = ALGO_MARKERS.get(algo, "o")
        ax4.plot(sub["nodes"], sub["jains_fairness"], marker=marker, linewidth=2.4, markersize=8,
                 label=disp, color=color)

    ax4.axhline(1.0, color="gray", linestyle=":", linewidth=1.5, label="Perfect Fairness (1.0)")
    ax4.set_xlabel("Number of Nodes (Competing Flows)", fontweight="bold", fontsize=12)
    ax4.set_ylabel("Jain's Fairness Index", fontweight="bold", fontsize=12)
    ax4.set_title("Fairness Index vs. Number of Nodes", fontweight="bold", fontsize=14, pad=12)
    ax4.set_xticks(node_counts)
    ax4.set_ylim(0.4, 1.05)
    ax4.legend(loc="lower left", framealpha=0.9, fontsize=10)
    ax4.grid(True, linestyle="--", alpha=0.6)
    fig4.tight_layout()
    p4 = plots_dir / "fairness_index_vs_nodes.png"
    fig4.savefig(p4, dpi=300)
    plt.close(fig4)

    # Combined 2x2 Grid Plot
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("Comparative Evaluation Across Number of Nodes\n(NewReno, Cubic, HighSpeed, BBR, and TCP DQN)",
                 fontsize=16, fontweight="bold", y=0.98)

    # Panel 1: Throughput
    ax_t = axes[0, 0]
    for algo in algos:
        sub = summary_df[summary_df["algorithm"] == algo].sort_values("nodes")
        disp = ALGO_DISPLAY_NAMES.get(algo, algo)
        color = ALGO_COLORS.get(algo, None)
        marker = ALGO_MARKERS.get(algo, "o")
        ax_t.plot(sub["nodes"], sub["total_throughput_mbps"], marker=marker, linewidth=2.2, markersize=7,
                  label=disp, color=color)
    ax_t.axhline(bottleneck_mbps, color="black", linestyle="--", linewidth=1.3, label=f"Bottleneck ({bottleneck_mbps} Mbps)")
    ax_t.set_xlabel("Number of Nodes", fontweight="bold")
    ax_t.set_ylabel("Total Throughput (Mbps)", fontweight="bold")
    ax_t.set_title("(a) Throughput vs. Number of Nodes", fontweight="bold")
    ax_t.set_xticks(node_counts)
    ax_t.legend(loc="lower right", framealpha=0.9)
    ax_t.grid(True, linestyle="--", alpha=0.6)

    # Panel 2: Mean RTT
    ax_r = axes[0, 1]
    for algo in algos:
        sub = summary_df[summary_df["algorithm"] == algo].sort_values("nodes")
        disp = ALGO_DISPLAY_NAMES.get(algo, algo)
        color = ALGO_COLORS.get(algo, None)
        marker = ALGO_MARKERS.get(algo, "o")
        ax_r.plot(sub["nodes"], sub["mean_rtt_ms"], marker=marker, linewidth=2.2, markersize=7,
                  label=disp, color=color)
    ax_r.set_xlabel("Number of Nodes", fontweight="bold")
    ax_r.set_ylabel("Mean RTT (ms)", fontweight="bold")
    ax_r.set_title("(b) Mean RTT vs. Number of Nodes", fontweight="bold")
    ax_r.set_xticks(node_counts)
    ax_r.legend(loc="upper left", framealpha=0.9)
    ax_r.grid(True, linestyle="--", alpha=0.6)

    # Panel 3: Packet Drops
    ax_d = axes[1, 0]
    for algo in algos:
        sub = summary_df[summary_df["algorithm"] == algo].sort_values("nodes")
        disp = ALGO_DISPLAY_NAMES.get(algo, algo)
        color = ALGO_COLORS.get(algo, None)
        marker = ALGO_MARKERS.get(algo, "o")
        ax_d.plot(sub["nodes"], sub["total_queue_drops"], marker=marker, linewidth=2.2, markersize=7,
                  label=disp, color=color)
    ax_d.set_xlabel("Number of Nodes", fontweight="bold")
    ax_d.set_ylabel("Bottleneck Packet Drops", fontweight="bold")
    ax_d.set_title("(c) Packet Drops vs. Number of Nodes", fontweight="bold")
    ax_d.set_xticks(node_counts)
    ax_d.legend(loc="upper left", framealpha=0.9)
    ax_d.grid(True, linestyle="--", alpha=0.6)

    # Panel 4: Fairness Index
    ax_f = axes[1, 1]
    for algo in algos:
        sub = summary_df[summary_df["algorithm"] == algo].sort_values("nodes")
        disp = ALGO_DISPLAY_NAMES.get(algo, algo)
        color = ALGO_COLORS.get(algo, None)
        marker = ALGO_MARKERS.get(algo, "o")
        ax_f.plot(sub["nodes"], sub["jains_fairness"], marker=marker, linewidth=2.2, markersize=7,
                  label=disp, color=color)
    ax_f.axhline(1.0, color="gray", linestyle=":", linewidth=1.3, label="Ideal Fairness (1.0)")
    ax_f.set_xlabel("Number of Nodes", fontweight="bold")
    ax_f.set_ylabel("Jain's Fairness Index", fontweight="bold")
    ax_f.set_title("(d) Fairness Index vs. Number of Nodes", fontweight="bold")
    ax_f.set_xticks(node_counts)
    ax_f.set_ylim(0.4, 1.05)
    ax_f.legend(loc="lower left", framealpha=0.9)
    ax_f.grid(True, linestyle="--", alpha=0.6)

    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    p_combined = plots_dir / "multinode_metrics_comparison.png"
    fig.savefig(p_combined, dpi=300)
    plt.close(fig)

    print(f"\n[+] Saved individual plots to: {plots_dir}")
    print(f"    - {p1}")
    print(f"    - {p2}")
    print(f"    - {p3}")
    print(f"    - {p4}")
    print(f"[+] Saved consolidated 4-panel plot to: {p_combined}")


def main():
    args = parse_args()
    args.plots_dir = args.plots_dir.resolve()
    args.traces_dir = args.traces_dir.resolve()
    args.plots_dir.mkdir(parents=True, exist_ok=True)
    args.traces_dir.mkdir(parents=True, exist_ok=True)

    summary_csv = args.traces_dir / "multinode_sweep_summary.csv"

    if args.skip_sim and summary_csv.exists():
        print(f"Loading existing sweep data from {summary_csv}...")
        summary_df = pd.read_csv(summary_csv)
    else:
        summary_rows = []
        for n in args.node_counts:
            for algo in args.algorithms:
                flows_df, queue_df = run_simulation(algo, n, args)

                per_flow_throughput = []
                for fid in flows_df["flow_id"].unique():
                    f_slice = flows_df[flows_df["flow_id"] == fid]
                    # discard initial transient 0.5s if long enough
                    if len(f_slice) > 10:
                        f_slice = f_slice[f_slice["time_s"] >= 1.0]
                    mean_bps = f_slice["throughput_Bps"].mean()
                    per_flow_throughput.append((mean_bps * 8.0) / 1e6)

                total_throughput_mbps = sum(per_flow_throughput)
                fairness = jains_fairness_index(per_flow_throughput)
                total_drops = int(queue_df["cumulative_drops"].iloc[-1]) if not queue_df.empty else 0
                mean_rtt = float(flows_df["rtt_ms"][flows_df["rtt_ms"] > 0].mean())

                summary_rows.append({
                    "algorithm": algo,
                    "nodes": n,
                    "total_throughput_mbps": round(total_throughput_mbps, 2),
                    "mean_rtt_ms": round(mean_rtt, 2),
                    "total_queue_drops": int(total_drops),
                    "jains_fairness": round(fairness, 3),
                })

        summary_df = pd.DataFrame(summary_rows)
        summary_df.to_csv(summary_csv, index=False)
        print(f"\n[+] Saved sweep summary to: {summary_csv}")

    md_out = REPO_ROOT / "results" / "multinode_sweep_summary.md"
    with open(md_out, "w", encoding="utf-8") as f:
        f.write("# Multi-Node Network Congestion Sweep Summary\n\n")
        f.write(f"- **Evaluated Algorithms:** NewReno, Cubic, HighSpeed, BBR, TCP-DQN\n")
        f.write(f"- **Node Counts:** {sorted(summary_df['nodes'].unique())}\n")
        f.write(f"- **Bottleneck Bandwidth:** {args.bottleneck_mbps} Mbps\n")
        f.write(f"- **Bottleneck Queue Capacity:** {args.queue_packets} packets (DropTail FIFO)\n")
        f.write(f"- **Simulation Time:** {args.sim_time_s} seconds\n\n")
        f.write("### Benchmark Data Table\n\n")
        f.write(summary_df.to_markdown(index=False) + "\n\n")

    print(f"[+] Saved markdown summary to: {md_out}")
    print("\n" + summary_df.to_string(index=False))

    plot_metrics(summary_df, args.plots_dir, args.bottleneck_mbps)


if __name__ == "__main__":
    main()
