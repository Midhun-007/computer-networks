#!/usr/bin/env python3
"""Run alpha parameter sweep for TCP DQN across multiple competing flows and generate:
1. Throughput vs alpha
2. RTT vs alpha
3. Packet loss vs alpha
4. Fairness index vs alpha
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
    p = argparse.ArgumentParser(description="TCP DQN Alpha Parameter Sweep")
    p.add_argument("--alphas", type=float, nargs="+", default=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    p.add_argument("--n-senders", type=int, default=4, help="Number of competing TCP DQN flows")
    p.add_argument("--bottleneck-mbps", type=float, default=15.0)
    p.add_argument("--bottleneck-delay-ms", type=float, default=25.0)
    p.add_argument("--queue-packets", type=int, default=40)
    p.add_argument("--sim-time-s", type=float, default=15.0)
    p.add_argument("--plots-dir", type=Path, default=REPO_ROOT / "results" / "plots")
    p.add_argument("--traces-dir", type=Path, default=REPO_ROOT / "results" / "traces")
    p.add_argument("--skip-sim", action="store_true", help="Skip simulation and plot existing results")
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


def run_simulation(alpha: float, args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    ns3 = ns3_dir()
    prefix = f"alpha_sweep_{alpha:.2f}"
    cmd = [
        str(ns3 / "ns3"),
        "run",
        (
            f"tcp-dqn-multinode-topology "
            f"--nSenders={args.n_senders} "
            f"--bottleneckMbps={args.bottleneck_mbps} "
            f"--bottleneckDelayMs={args.bottleneck_delay_ms} "
            f"--queuePackets={args.queue_packets} "
            f"--simTimeS={args.sim_time_s} "
            f"--transport_prot=TcpDqn "
            f"--alpha={alpha} "
            f"--staggeredStarts=false "
            f"--tracePrefix={prefix} "
            f"--traceDir={args.traces_dir.resolve()}"
        ),
    ]
    print(f"\n---> Running TCP DQN simulation for alpha = {alpha:.2f} ({args.n_senders} senders)...")
    subprocess.run(cmd, cwd=ns3, check=True)

    flows_csv = args.traces_dir / f"{prefix}_flows.csv"
    queue_csv = args.traces_dir / f"{prefix}_queue.csv"

    flows_df = pd.read_csv(flows_csv)
    queue_df = pd.read_csv(queue_csv)
    return flows_df, queue_df


def plot_alpha_metrics(summary_df: pd.DataFrame, plots_dir: Path, bottleneck_mbps: float, n_senders: int):
    plots_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    alphas = summary_df["alpha"].values
    t_mbps = summary_df["total_throughput_mbps"].values
    rtt_ms = summary_df["mean_rtt_ms"].values
    drops = summary_df["total_queue_drops"].values
    fairness = summary_df["jains_fairness"].values

    primary_color = "#6f42c1"  # Deep Purple
    accent_blue = "#1f77b4"
    accent_red = "#d62728"
    accent_green = "#2ca02c"

    # 1. Throughput vs Alpha
    fig1, ax1 = plt.subplots(figsize=(9, 6))
    ax1.plot(alphas, t_mbps, marker="o", color=accent_blue, linewidth=2.5, markersize=8, label="TCP DQN Aggregate Throughput")
    ax1.fill_between(alphas, t_mbps, color=accent_blue, alpha=0.15)
    ax1.axhline(bottleneck_mbps, color="black", linestyle="--", linewidth=1.5, label=f"Bottleneck Capacity ({bottleneck_mbps} Mbps)")
    ax1.set_xlabel(r"Reward Weight $\alpha$ (Throughput Emphasis $\rightarrow$)", fontweight="bold", fontsize=12)
    ax1.set_ylabel("Total Bottleneck Throughput (Mbps)", fontweight="bold", fontsize=12)
    ax1.set_title(f"TCP DQN: Throughput vs. Alpha\n({n_senders} Competing Flows, {bottleneck_mbps} Mbps Bottleneck)", fontweight="bold", fontsize=13, pad=12)
    ax1.set_xticks(alphas)
    ax1.legend(loc="lower right", framealpha=0.9, fontsize=10)
    ax1.grid(True, linestyle="--", alpha=0.6)
    for a, t in zip(alphas, t_mbps):
        ax1.annotate(f"{t:.2f}", (a, t), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8.5, fontweight="bold")
    fig1.tight_layout()
    p1 = plots_dir / "tcp_dqn_throughput_vs_alpha.png"
    fig1.savefig(p1, dpi=300)
    plt.close(fig1)

    # 2. RTT vs Alpha
    fig2, ax2 = plt.subplots(figsize=(9, 6))
    base_rtt = 54.0
    ax2.plot(alphas, rtt_ms, marker="s", color=accent_red, linewidth=2.5, markersize=8, label="TCP DQN Mean RTT")
    ax2.axhline(base_rtt, color="gray", linestyle=":", linewidth=1.5, label=f"Base RTT (~{base_rtt:.1f} ms)")
    ax2.set_xlabel(r"Reward Weight $\alpha$ (Throughput Emphasis $\rightarrow$)", fontweight="bold", fontsize=12)
    ax2.set_ylabel("Mean Round-Trip Time (RTT) [ms]", fontweight="bold", fontsize=12)
    ax2.set_title(f"TCP DQN: Round-Trip Time (RTT) vs. Alpha\n({n_senders} Competing Flows, Base RTT = 54 ms)", fontweight="bold", fontsize=13, pad=12)
    ax2.set_xticks(alphas)
    ax2.legend(loc="upper left", framealpha=0.9, fontsize=10)
    ax2.grid(True, linestyle="--", alpha=0.6)
    for a, r in zip(alphas, rtt_ms):
        ax2.annotate(f"{r:.1f}", (a, r), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8.5, fontweight="bold")
    fig2.tight_layout()
    p2 = plots_dir / "tcp_dqn_rtt_vs_alpha.png"
    fig2.savefig(p2, dpi=300)
    plt.close(fig2)

    # 3. Packet Loss / Queue Drops vs Alpha
    fig3, ax3 = plt.subplots(figsize=(9, 6))
    ax3.plot(alphas, drops, marker="^", color="#e377c2", linewidth=2.5, markersize=8, label="Bottleneck Queue Drops")
    ax3.bar(alphas, drops, width=0.04, color="#e377c2", alpha=0.25, edgecolor="#e377c2")
    ax3.set_xlabel(r"Reward Weight $\alpha$ (Throughput Emphasis $\rightarrow$)", fontweight="bold", fontsize=12)
    ax3.set_ylabel("Total Bottleneck Packet Drops (packets)", fontweight="bold", fontsize=12)
    ax3.set_title(f"TCP DQN: Packet Loss / Drops vs. Alpha\n({n_senders} Competing Flows, 40-Packet Buffer)", fontweight="bold", fontsize=13, pad=12)
    ax3.set_xticks(alphas)
    ax3.legend(loc="upper left", framealpha=0.9, fontsize=10)
    ax3.grid(True, linestyle="--", alpha=0.6)
    for a, d in zip(alphas, drops):
        ax3.annotate(f"{d}", (a, d), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=8.5, fontweight="bold")
    fig3.tight_layout()
    p3 = plots_dir / "tcp_dqn_packet_loss_vs_alpha.png"
    fig3.savefig(p3, dpi=300)
    plt.close(fig3)

    # 4. Fairness Index vs Alpha
    fig4, ax4 = plt.subplots(figsize=(9, 6))
    ax4.plot(alphas, fairness, marker="D", color=accent_green, linewidth=2.5, markersize=8, label="Jain's Fairness Index")
    ax4.axhline(1.0, color="gray", linestyle=":", linewidth=1.5, label="Perfect Fairness (1.0)")
    ax4.set_xlabel(r"Reward Weight $\alpha$ (Throughput Emphasis $\rightarrow$)", fontweight="bold", fontsize=12)
    ax4.set_ylabel("Jain's Fairness Index (0 to 1)", fontweight="bold", fontsize=12)
    ax4.set_title(f"TCP DQN: Jain's Fairness Index vs. Alpha\n({n_senders} Competing Flows)", fontweight="bold", fontsize=13, pad=12)
    ax4.set_xticks(alphas)
    ax4.set_ylim(0.5, 1.05)
    ax4.legend(loc="lower left", framealpha=0.9, fontsize=10)
    ax4.grid(True, linestyle="--", alpha=0.6)
    for a, f in zip(alphas, fairness):
        ax4.annotate(f"{f:.3f}", (a, f), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8.5, fontweight="bold")
    fig4.tight_layout()
    p4 = plots_dir / "tcp_dqn_fairness_vs_alpha.png"
    fig4.savefig(p4, dpi=300)
    plt.close(fig4)

    # Combined 2x2 Grid Plot
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(
        r"TCP-DQN Performance Trade-Offs vs. Reward Parameter $\alpha$" + "\n"
        r"$r_t = \alpha \cdot \frac{T - T_{\min}}{T_{\max} - T_{\min}} - (1 - \alpha) \cdot \frac{RTT - RTT_{\min}}{RTT_{\max} - RTT_{\min}}$"
        f" ({n_senders} Competing Flows, {bottleneck_mbps} Mbps Bottleneck)",
        fontsize=15, fontweight="bold", y=0.98,
    )

    # Subplot (a): Throughput vs Alpha
    ax_a = axes[0, 0]
    ax_a.plot(alphas, t_mbps, marker="o", color=accent_blue, linewidth=2.4, markersize=8)
    ax_a.fill_between(alphas, t_mbps, color=accent_blue, alpha=0.15)
    ax_a.axhline(bottleneck_mbps, color="black", linestyle="--", linewidth=1.3, label=f"Capacity ({bottleneck_mbps} Mbps)")
    ax_a.set_xlabel(r"Reward Weight $\alpha$", fontweight="bold")
    ax_a.set_ylabel("Throughput (Mbps)", fontweight="bold")
    ax_a.set_title(r"(a) Throughput vs. $\alpha$", fontweight="bold")
    ax_a.set_xticks(alphas)
    ax_a.legend(loc="lower right")
    ax_a.grid(True, linestyle="--", alpha=0.6)

    # Subplot (b): RTT vs Alpha
    ax_b = axes[0, 1]
    ax_b.plot(alphas, rtt_ms, marker="s", color=accent_red, linewidth=2.4, markersize=8)
    ax_b.axhline(base_rtt, color="gray", linestyle=":", linewidth=1.3, label=f"Base RTT ({base_rtt:.1f} ms)")
    ax_b.set_xlabel(r"Reward Weight $\alpha$", fontweight="bold")
    ax_b.set_ylabel("Mean RTT (ms)", fontweight="bold")
    ax_b.set_title(r"(b) Mean RTT vs. $\alpha$", fontweight="bold")
    ax_b.set_xticks(alphas)
    ax_b.legend(loc="upper left")
    ax_b.grid(True, linestyle="--", alpha=0.6)

    # Subplot (c): Packet Loss vs Alpha
    ax_c = axes[1, 0]
    ax_c.plot(alphas, drops, marker="^", color="#e377c2", linewidth=2.4, markersize=8)
    ax_c.bar(alphas, drops, width=0.04, color="#e377c2", alpha=0.25)
    ax_c.set_xlabel(r"Reward Weight $\alpha$", fontweight="bold")
    ax_c.set_ylabel("Total Queue Drops (packets)", fontweight="bold")
    ax_c.set_title(r"(c) Packet Loss / Drops vs. $\alpha$", fontweight="bold")
    ax_c.set_xticks(alphas)
    ax_c.grid(True, linestyle="--", alpha=0.6)

    # Subplot (d): Fairness Index vs Alpha
    ax_d = axes[1, 1]
    ax_d.plot(alphas, fairness, marker="D", color=accent_green, linewidth=2.4, markersize=8)
    ax_d.axhline(1.0, color="gray", linestyle=":", linewidth=1.3, label="Perfect Fairness (1.0)")
    ax_d.set_xlabel(r"Reward Weight $\alpha$", fontweight="bold")
    ax_d.set_ylabel("Jain's Fairness Index", fontweight="bold")
    ax_d.set_title(r"(d) Fairness Index vs. $\alpha$", fontweight="bold")
    ax_d.set_xticks(alphas)
    ax_d.set_ylim(0.5, 1.05)
    ax_d.legend(loc="lower left")
    ax_d.grid(True, linestyle="--", alpha=0.6)

    fig.tight_layout(rect=[0, 0.03, 1, 0.94])
    p_combined = plots_dir / "tcp_dqn_alpha_comprehensive.png"
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

    summary_csv = args.traces_dir / "tcp_dqn_alpha_sweep_summary.csv"

    if args.skip_sim and summary_csv.exists():
        print(f"Loading existing alpha sweep data from {summary_csv}...")
        summary_df = pd.read_csv(summary_csv)
    else:
        summary_rows = []
        for alpha in args.alphas:
            flows_df, queue_df = run_simulation(alpha, args)

            per_flow_throughput = []
            for fid in flows_df["flow_id"].unique():
                f_slice = flows_df[flows_df["flow_id"] == fid]
                if len(f_slice) > 10:
                    f_slice = f_slice[f_slice["time_s"] >= 1.0]
                mean_bps = f_slice["throughput_Bps"].mean()
                per_flow_throughput.append((mean_bps * 8.0) / 1e6)

            total_throughput_mbps = sum(per_flow_throughput)
            fairness = jains_fairness_index(per_flow_throughput)
            total_drops = int(queue_df["cumulative_drops"].iloc[-1]) if not queue_df.empty else 0
            mean_rtt = float(flows_df["rtt_ms"][flows_df["rtt_ms"] > 0].mean())

            summary_rows.append({
                "alpha": alpha,
                "total_throughput_mbps": round(total_throughput_mbps, 2),
                "mean_rtt_ms": round(mean_rtt, 2),
                "total_queue_drops": int(total_drops),
                "jains_fairness": round(fairness, 3),
            })

        summary_df = pd.DataFrame(summary_rows)
        summary_df.to_csv(summary_csv, index=False)
        print(f"\n[+] Saved alpha sweep summary to: {summary_csv}")

    md_out = REPO_ROOT / "results" / "tcp_dqn_alpha_sweep_summary.md"
    with open(md_out, "w", encoding="utf-8") as f:
        f.write("# TCP-DQN Alpha Sensitivity Sweep Summary\n\n")
        f.write(f"- **Evaluated Alpha Values:** {args.alphas}\n")
        f.write(f"- **Senders:** {args.n_senders} competing TCP DQN flows\n")
        f.write(f"- **Bottleneck Bandwidth:** {args.bottleneck_mbps} Mbps\n")
        f.write(f"- **Bottleneck Queue Capacity:** {args.queue_packets} packets (DropTail FIFO)\n")
        f.write(f"- **Simulation Time:** {args.sim_time_s} seconds\n\n")
        f.write("### Benchmark Data Table\n\n")
        f.write(summary_df.to_markdown(index=False) + "\n\n")

    print(f"[+] Saved markdown summary to: {md_out}")
    print("\n" + summary_df.to_string(index=False))

    plot_alpha_metrics(summary_df, args.plots_dir, args.bottleneck_mbps, args.n_senders)


if __name__ == "__main__":
    main()
