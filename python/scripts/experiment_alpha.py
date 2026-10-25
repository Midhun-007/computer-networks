#!/usr/bin/env python3
"""Experiment script to evaluate the effect of varying reward alpha in TCP-DQN."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "python"))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate TCP-DQN under different alpha values")
    p.add_argument("--alphas", type=float, nargs="+", default=[0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0])
    p.add_argument("--sim-time-s", type=float, default=20.0, help="Simulation duration in seconds")
    p.add_argument("--model", type=Path, default=REPO_ROOT / "results" / "models" / "tcp_dqn.zip")
    p.add_argument("--plots-dir", type=Path, default=REPO_ROOT / "results" / "plots")
    p.add_argument("--traces-dir", type=Path, default=REPO_ROOT / "results" / "traces")
    return p.parse_args()


def generate_alpha_plots(results_summary: pd.DataFrame, out_dir: Path) -> Path:
    """Generate comprehensive 4-panel analysis plot of alpha variations."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "alpha_sensitivity_analysis.png"

    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Impact of Reward Parameter α on TCP-DQN Performance\n"
                 r"$r_t = \alpha \cdot \frac{T - T_{min}}{T_{max} - T_{min}} - (1 - \alpha) \cdot \frac{RTT - RTT_{min}}{RTT_{max} - RTT_{min}}$",
                 fontsize=14, fontweight="bold", y=0.98)

    alphas = results_summary["alpha"].values
    throughput_mbps = results_summary["mean_throughput_mbps"].values
    mean_rtt = results_summary["mean_rtt_ms"].values
    mean_cwnd = results_summary["mean_cwnd_segments"].values
    mean_rewards = results_summary["mean_reward"].values

    # Panel 1: Throughput vs Alpha
    ax1 = axes[0, 0]
    ax1.plot(alphas, throughput_mbps, marker="o", color="#1f77b4", linewidth=2.5, markersize=8)
    ax1.fill_between(alphas, throughput_mbps, color="#1f77b4", alpha=0.15)
    ax1.set_xlabel(r"Reward Weight $\alpha$ (Throughput Emphasis $\rightarrow$)", fontweight="bold")
    ax1.set_ylabel("Mean Throughput (Mbps)", fontweight="bold", color="#1f77b4")
    ax1.set_title("Throughput vs. Alpha", fontweight="bold", fontsize=12)
    ax1.grid(True, linestyle="--", alpha=0.6)
    for a, t in zip(alphas, throughput_mbps):
        ax1.annotate(f"{t:.2f} Mbps", (a, t), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9)

    # Panel 2: Mean RTT and Queuing Delay vs Alpha
    ax2 = axes[0, 1]
    base_rtt = 56.0  # base RTT in link_default.yaml
    ax2.plot(alphas, mean_rtt, marker="s", color="#d62728", linewidth=2.5, markersize=8, label="Mean RTT")
    ax2.axhline(base_rtt, color="gray", linestyle=":", label=f"Base RTT ({base_rtt} ms)")
    ax2.set_xlabel(r"Reward Weight $\alpha$ (Throughput Emphasis $\rightarrow$)", fontweight="bold")
    ax2.set_ylabel("Mean RTT (ms)", fontweight="bold", color="#d62728")
    ax2.set_title("Round-Trip Time & Bufferbloat vs. Alpha", fontweight="bold", fontsize=12)
    ax2.legend(loc="upper left")
    ax2.grid(True, linestyle="--", alpha=0.6)
    for a, r in zip(alphas, mean_rtt):
        ax2.annotate(f"{r:.2f} ms", (a, r), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9)

    # Panel 3: Mean Reward vs Alpha
    ax3 = axes[1, 0]
    ax3.plot(alphas, mean_rewards, marker="^", color="#2ca02c", linewidth=2.5, markersize=8)
    ax3.set_xlabel(r"Reward Weight $\alpha$", fontweight="bold")
    ax3.set_ylabel("Mean Step Reward", fontweight="bold", color="#2ca02c")
    ax3.set_title("Mean Step Reward vs. Alpha", fontweight="bold", fontsize=12)
    ax3.grid(True, linestyle="--", alpha=0.6)
    for a, rew in zip(alphas, mean_rewards):
        ax3.annotate(f"{rew:.3f}", (a, rew), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9)

    # Panel 4: Pareto Trade-off Curve (Throughput vs. RTT)
    ax4 = axes[1, 1]
    scatter = ax4.scatter(mean_rtt, throughput_mbps, c=alphas, cmap="viridis", s=180, edgecolors="black", zorder=5)
    cbar = fig.colorbar(scatter, ax=ax4)
    cbar.set_label(r"$\alpha$ value", fontweight="bold")
    ax4.plot(mean_rtt, throughput_mbps, linestyle="--", color="#7f7f7f", alpha=0.7, zorder=3)
    ax4.set_xlabel("Mean RTT (ms) - Lower is Better", fontweight="bold")
    ax4.set_ylabel("Mean Throughput (Mbps) - Higher is Better", fontweight="bold")
    ax4.set_title("Pareto Trade-Off Frontier (Throughput vs. Latency)", fontweight="bold", fontsize=12)
    ax4.grid(True, linestyle="--", alpha=0.6)
    for a, r, t in zip(alphas, mean_rtt, throughput_mbps):
        ax4.annotate(f"α={a}", (r, t), textcoords="offset points", xytext=(8, -4), fontsize=9, fontweight="bold")

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"\n[+] Saved sensitivity analysis plot to: {out_path}")
    return out_path


def main() -> None:
    args = parse_args()
    args.model = args.model.resolve()
    args.plots_dir = args.plots_dir.resolve()
    args.traces_dir = args.traces_dir.resolve()
    args.plots_dir.mkdir(parents=True, exist_ok=True)
    args.traces_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    worker_script = REPO_ROOT / "python" / "scripts" / "run_single_alpha_worker.py"

    for alpha in args.alphas:
        out_csv = args.traces_dir / f"tcp_dqn_alpha_{alpha:.2f}.csv"
        stats_json = args.traces_dir / f"tcp_dqn_alpha_{alpha:.2f}_stats.json"

        cmd = [
            sys.executable,
            str(worker_script),
            f"--alpha={alpha}",
            f"--sim-time-s={args.sim_time_s}",
            f"--model={args.model}",
            f"--traces-dir={args.traces_dir}",
            f"--out-csv={out_csv}",
            f"--stats-json={stats_json}",
        ]

        print(f"\n---> Starting isolated run for alpha = {alpha:.2f}...")
        subprocess.run(cmd, check=True)

        with open(stats_json, "r", encoding="utf-8") as f:
            stats = json.load(f)
        summary_rows.append(stats)

    summary_df = pd.DataFrame(summary_rows)
    csv_out = args.traces_dir / "alpha_experiments_summary.csv"
    summary_df.to_csv(csv_out, index=False)
    print(f"\n[+] Saved summary table to: {csv_out}")
    print("\n" + summary_df.to_string(index=False))

    plot_path = generate_alpha_plots(summary_df, args.plots_dir)


if __name__ == "__main__":
    main()
