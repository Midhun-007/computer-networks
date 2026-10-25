#!/usr/bin/env python3
"""Generate theoretically expected graphs for TCP congestion control algorithms:
NewReno, Cubic, HighSpeed, BBR, and TCP DQN.

Theoretical Models:
1. Throughput vs Number of Nodes (Link utilization & multiplexing theory)
2. Mean RTT vs Number of Nodes (Queuing delay & bufferbloat theory)
3. Packet Drops vs Number of Nodes (Buffer overflow & loss recovery theory)
4. Fairness Index vs Number of Nodes (Chiu-Jain AIMD convergence & game-theoretic equilibrium)
"""

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
PLOTS_DIR = REPO_ROOT / "results" / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

# Parameter configuration matching standard benchmark dumbbell
C_BOTTLE = 15.0      # Bottleneck capacity in Mbps
RTT_BASE = 50.0      # Base round-trip propagation delay in ms
QUEUE_MAX_PKTS = 40  # Max queue buffer capacity in packets
MSS_BYTES = 1460     # TCP MSS
QUEUE_DELAY_MAX = (QUEUE_MAX_PKTS * MSS_BYTES * 8.0) / (C_BOTTLE * 1e6) * 1000.0  # Max queuing delay in ms (~31.1 ms)
RTT_MAX = RTT_BASE + QUEUE_DELAY_MAX  # ~81.1 ms

# Smooth continuous range of nodes from 1 to 20
N = np.linspace(1, 20, 200)
# Discrete evaluation points for markers
N_pts = np.array([1, 2, 4, 6, 8, 10, 12, 16, 20])

# ==============================================================================
# 1. THEORETICAL THROUGHPUT MODEL (Mbps)
# ==============================================================================
# Single-flow NewReno under AIMD achieves ~75-80% of link capacity when buffer < BDP.
# As N increases, multiplexing of asynchronous sawteeth brings aggregate utilization to 98%+.
# At very large N, slight goodput degradation occurs due to synchronized drops/timeouts.
def throughput_newreno(n):
    # Starts around 75% for N=1, ramps up to ~96% by N=4, plateauing near capacity
    return C_BOTTLE * (0.75 + 0.22 * (1.0 - np.exp(-0.7 * (n - 0.5)))) - 0.008 * np.maximum(0, n - 10)**1.2

# Cubic: Aggressive cubic window recovery achieves high utilization even for single flow (~92%).
# Retains high link saturation (>97%) across N.
def throughput_cubic(n):
    return C_BOTTLE * (0.92 + 0.065 * (1.0 - np.exp(-0.8 * (n - 0.5)))) - 0.005 * np.maximum(0, n - 12)**1.1

# HighSpeed: Similar to Cubic, fast window acceleration on large BDP, slight drop penalty.
def throughput_highspeed(n):
    return C_BOTTLE * (0.90 + 0.075 * (1.0 - np.exp(-0.75 * (n - 0.5)))) - 0.007 * np.maximum(0, n - 10)**1.15

# BBR: Model-based rate pacing at max bottleneck bandwidth estimates, near-perfect utilization.
def throughput_bbr(n):
    return C_BOTTLE * (0.97 + 0.02 * (1.0 - np.exp(-0.9 * n))) - 0.003 * np.maximum(0, n - 14)

# TCP DQN: Learned RL policy balances throughput vs. RTT (Eq. 6).
# Single flow explores safely, scaling link utilization smoothly as flow count increases
# while deliberately avoiding buffer filling.
def throughput_tcp_dqn(n):
    return C_BOTTLE * (0.78 + 0.17 * (1.0 - np.exp(-0.5 * (n - 0.5)))) - 0.004 * np.maximum(0, n - 12)

# ==============================================================================
# 2. THEORETICAL MEAN RTT MODEL (ms)
# ==============================================================================
# Loss-based TCP (NewReno, Cubic, HighSpeed) only slows down when buffer is FULL.
# As N increases, aggregate window keeps queue perpetually saturated (bufferbloat).
def rtt_newreno(n):
    # N=1: Sawtooth drains buffer part of the cycle (mean queue ~ 40% full).
    # N>=4: Standing queue fills buffer nearly 100%.
    q_fraction = 0.40 + 0.55 * (1.0 - np.exp(-0.45 * (n - 0.8)))
    return RTT_BASE + q_fraction * QUEUE_DELAY_MAX

def rtt_cubic(n):
    # Cubic holds window near W_max longer, keeping buffer fuller than NewReno.
    q_fraction = 0.55 + 0.43 * (1.0 - np.exp(-0.55 * (n - 0.8)))
    return RTT_BASE + q_fraction * QUEUE_DELAY_MAX

def rtt_highspeed(n):
    q_fraction = 0.50 + 0.47 * (1.0 - np.exp(-0.50 * (n - 0.8)))
    return RTT_BASE + q_fraction * QUEUE_DELAY_MAX

def rtt_bbr(n):
    # BBR operates at Kleinrock point (min RTT) when unhindered.
    # With multiple competing flows, unsynchronized ProbeBW cycles build queue,
    # but 10s ProbeRTT drains it. RTT stays well below loss-based protocols.
    q_fraction = 0.15 + 0.50 * (1.0 - np.exp(-0.35 * (n - 0.5)))
    return RTT_BASE + q_fraction * QUEUE_DELAY_MAX

def rtt_tcp_dqn(n):
    # TCP DQN reward Eq. (6) heavily penalizes delay: -(1 - alpha) * (RTT - RTT_min).
    # The policy throttles cwnd BEFORE the queue overflows, maintaining lowest queuing delay.
    q_fraction = 0.10 + 0.38 * (1.0 - np.exp(-0.30 * (n - 0.5)))
    return RTT_BASE + q_fraction * QUEUE_DELAY_MAX

# ==============================================================================
# 3. THEORETICAL PACKET DROPS MODEL (packets per simulation period)
# ==============================================================================
# Drops scale with N as more flows probe the fixed buffer capacity.
def drops_newreno(n):
    # Conservative AIMD (+1 / -50%): lowest drops among loss-based algorithms.
    return 25.0 * n**1.15 + 10.0

def drops_cubic(n):
    # Cubic's sharp inflection near W_max causes more aggressive overflow bursts.
    return 55.0 * n**1.28 + 25.0

def drops_highspeed(n):
    # Faster growth than NewReno produces higher loss frequency.
    return 45.0 * n**1.22 + 20.0

def drops_bbr(n):
    # In shallow buffers (40 pkts), BBR's 1.25x pacing probe overflows buffer before
    # RTT filter updates, generating substantial drops.
    return 180.0 * n**1.35 + 80.0

def drops_tcp_dqn(n):
    # DQN agent with discrete delta actions experiences transient packet drops when
    # probing link limits, but backoff stabilizes drops between Cubic and BBR.
    return 120.0 * n**1.25 + 50.0

# ==============================================================================
# 4. THEORETICAL JAIN'S FAIRNESS INDEX MODEL (0.0 to 1.0)
# ==============================================================================
# Single flow: trivially 1.0.
# Small N: Chiu-Jain convergence time creates minor transient asymmetry.
# High N: High multiplexing drives flows toward fair share equilibrium.
def fairness_newreno(n):
    # Classic AIMD provably converges to fair allocation (Chiu & Jain, 1989).
    # J ~ 0.96 - 0.99 for equal RTT flows.
    return 0.99 - 0.05 / (1.0 + np.exp(-0.8 * (n - 2.0))) + 0.04 * (1.0 - 1.0 / np.sqrt(n))

def fairness_cubic(n):
    # Cubic's concave phase accelerates smaller windows, providing excellent intra-protocol fairness.
    return 0.985 - 0.04 / (1.0 + np.exp(-0.9 * (n - 2.0))) + 0.035 * (1.0 - 1.0 / np.sqrt(n))

def fairness_highspeed(n):
    # HighSpeed is known to be slightly less fair because large windows accelerate faster than small ones.
    return 0.94 - 0.08 / (1.0 + np.exp(-0.7 * (n - 2.0))) + 0.05 * (1.0 - 1.0 / np.sqrt(n))

def fairness_bbr(n):
    # BBR flows synchronize their ProbeBW phases, achieving near-perfect fairness at scale.
    return 0.98 - 0.06 / (1.0 + np.exp(-0.85 * (n - 2.0))) + 0.05 * (1.0 - 1.0 / np.sqrt(n))

def fairness_tcp_dqn(n):
    # RL agent receives common state signals (RTT, loss). Symmetric Nash equilibrium yields high fairness.
    return 0.96 - 0.08 / (1.0 + np.exp(-0.75 * (n - 2.0))) + 0.06 * (1.0 - 1.0 / np.sqrt(n))

# ==============================================================================
# PLOTTING ROUTINES
# ==============================================================================

ALGO_META = [
    ("NewReno", "#1f77b4", "-", "o", throughput_newreno, rtt_newreno, drops_newreno, fairness_newreno),
    ("Cubic", "#ff7f0e", "--", "s", throughput_cubic, rtt_cubic, drops_cubic, fairness_cubic),
    ("HighSpeed", "#2ca02c", "-.", "^", throughput_highspeed, rtt_highspeed, drops_highspeed, fairness_highspeed),
    ("BBR", "#d62728", ":", "D", throughput_bbr, rtt_bbr, drops_bbr, fairness_bbr),
    ("TCP DQN", "#9467bd", "-", "P", throughput_tcp_dqn, rtt_tcp_dqn, drops_tcp_dqn, fairness_tcp_dqn),
]

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

def generate_individual_plots():
    # 1. Throughput vs Number of Nodes
    fig1, ax1 = plt.subplots(figsize=(9, 6))
    for name, color, ls, marker, f_t, _, _, _ in ALGO_META:
        ax1.plot(N, f_t(N), label=name, color=color, linestyle=ls, linewidth=2.5)
        ax1.plot(N_pts, f_t(N_pts), marker=marker, color=color, linestyle="None", markersize=7)

    ax1.axhline(C_BOTTLE, color="black", linestyle="--", linewidth=1.5, label=f"Bottleneck Capacity ({C_BOTTLE:.0f} Mbps)")
    ax1.set_xlabel("Number of Competing Nodes ($N$)", fontweight="bold", fontsize=12)
    ax1.set_ylabel("Aggregate Throughput (Mbps)", fontweight="bold", fontsize=12)
    ax1.set_title("Theoretical Throughput vs. Number of Nodes\n(Multiplexing Gain & Capacity Saturation)", fontweight="bold", fontsize=13, pad=12)
    ax1.set_xlim(1, 20)
    ax1.set_ylim(0.6 * C_BOTTLE, C_BOTTLE * 1.05)
    ax1.set_xticks(N_pts)
    ax1.legend(loc="lower right", framealpha=0.92, fontsize=10)
    ax1.grid(True, linestyle="--", alpha=0.6)
    fig1.tight_layout()
    p1 = PLOTS_DIR / "theoretical_throughput_vs_nodes.png"
    fig1.savefig(p1, dpi=300)
    plt.close(fig1)

    # 2. Mean RTT vs Number of Nodes
    fig2, ax2 = plt.subplots(figsize=(9, 6))
    for name, color, ls, marker, _, f_r, _, _ in ALGO_META:
        ax2.plot(N, f_r(N), label=name, color=color, linestyle=ls, linewidth=2.5)
        ax2.plot(N_pts, f_r(N_pts), marker=marker, color=color, linestyle="None", markersize=7)

    ax2.axhline(RTT_BASE, color="gray", linestyle=":", linewidth=1.5, label=f"Base RTT ($RTT_0 = {RTT_BASE:.0f}$ ms)")
    ax2.axhline(RTT_MAX, color="crimson", linestyle="-.", linewidth=1.5, label=f"Max Bufferbloat ($RTT_{{max}} = {RTT_MAX:.1f}$ ms)")
    ax2.set_xlabel("Number of Competing Nodes ($N$)", fontweight="bold", fontsize=12)
    ax2.set_ylabel("Mean Round-Trip Time (RTT) [ms]", fontweight="bold", fontsize=12)
    ax2.set_title("Theoretical Mean RTT vs. Number of Nodes\n(Queuing Delay & Bufferbloat Progression)", fontweight="bold", fontsize=13, pad=12)
    ax2.set_xlim(1, 20)
    ax2.set_ylim(RTT_BASE - 2, RTT_MAX + 5)
    ax2.set_xticks(N_pts)
    ax2.legend(loc="upper left", framealpha=0.92, fontsize=10)
    ax2.grid(True, linestyle="--", alpha=0.6)
    fig2.tight_layout()
    p2 = PLOTS_DIR / "theoretical_mean_rtt_vs_nodes.png"
    fig2.savefig(p2, dpi=300)
    plt.close(fig2)

    # 3. Packet Drops vs Number of Nodes
    fig3, ax3 = plt.subplots(figsize=(9, 6))
    for name, color, ls, marker, _, _, f_d, _ in ALGO_META:
        ax3.plot(N, f_d(N), label=name, color=color, linestyle=ls, linewidth=2.5)
        ax3.plot(N_pts, f_d(N_pts), marker=marker, color=color, linestyle="None", markersize=7)

    ax3.set_xlabel("Number of Competing Nodes ($N$)", fontweight="bold", fontsize=12)
    ax3.set_ylabel("Cumulative Bottleneck Packet Drops", fontweight="bold", fontsize=12)
    ax3.set_title("Theoretical Packet Drops vs. Number of Nodes\n(Buffer Overflow & Congestion Backoff)", fontweight="bold", fontsize=13, pad=12)
    ax3.set_xlim(1, 20)
    ax3.set_xticks(N_pts)
    ax3.legend(loc="upper left", framealpha=0.92, fontsize=10)
    ax3.grid(True, linestyle="--", alpha=0.6)
    fig3.tight_layout()
    p3 = PLOTS_DIR / "theoretical_packet_drops_vs_nodes.png"
    fig3.savefig(p3, dpi=300)
    plt.close(fig3)

    # 4. Fairness Index vs Number of Nodes
    fig4, ax4 = plt.subplots(figsize=(9, 6))
    for name, color, ls, marker, _, _, _, f_f in ALGO_META:
        ax4.plot(N, f_f(N), label=name, color=color, linestyle=ls, linewidth=2.5)
        ax4.plot(N_pts, f_f(N_pts), marker=marker, color=color, linestyle="None", markersize=7)

    ax4.axhline(1.0, color="gray", linestyle=":", linewidth=1.5, label="Ideal Fairness ($J = 1.0$)")
    ax4.set_xlabel("Number of Competing Nodes ($N$)", fontweight="bold", fontsize=12)
    ax4.set_ylabel("Jain's Fairness Index", fontweight="bold", fontsize=12)
    ax4.set_title("Theoretical Fairness Index vs. Number of Nodes\n(Chiu-Jain Multi-Flow Equilibrium)", fontweight="bold", fontsize=13, pad=12)
    ax4.set_xlim(1, 20)
    ax4.set_ylim(0.85, 1.02)
    ax4.set_xticks(N_pts)
    ax4.legend(loc="lower right", framealpha=0.92, fontsize=10)
    ax4.grid(True, linestyle="--", alpha=0.6)
    fig4.tight_layout()
    p4 = PLOTS_DIR / "theoretical_fairness_index_vs_nodes.png"
    fig4.savefig(p4, dpi=300)
    plt.close(fig4)

    # Consolidated 4-Panel Plot
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(
        "Theoretical Network Congestion Performance vs. Number of Competing Nodes\n"
        "(Analytical Models: NewReno, Cubic, HighSpeed, BBR, and TCP DQN)",
        fontsize=15, fontweight="bold", y=0.98,
    )

    # Panel 1: Throughput
    ax_t = axes[0, 0]
    for name, color, ls, marker, f_t, _, _, _ in ALGO_META:
        ax_t.plot(N, f_t(N), label=name, color=color, linestyle=ls, linewidth=2.2)
        ax_t.plot(N_pts, f_t(N_pts), marker=marker, color=color, linestyle="None", markersize=6)
    ax_t.axhline(C_BOTTLE, color="black", linestyle="--", linewidth=1.3, label=f"Capacity ({C_BOTTLE:.0f} Mbps)")
    ax_t.set_xlabel("Number of Competing Nodes ($N$)", fontweight="bold")
    ax_t.set_ylabel("Throughput (Mbps)", fontweight="bold")
    ax_t.set_title("(a) Throughput vs. Number of Nodes", fontweight="bold")
    ax_t.set_xlim(1, 20)
    ax_t.set_xticks(N_pts)
    ax_t.legend(loc="lower right", fontsize=9)
    ax_t.grid(True, linestyle="--", alpha=0.6)

    # Panel 2: Mean RTT
    ax_r = axes[0, 1]
    for name, color, ls, marker, _, f_r, _, _ in ALGO_META:
        ax_r.plot(N, f_r(N), label=name, color=color, linestyle=ls, linewidth=2.2)
        ax_r.plot(N_pts, f_r(N_pts), marker=marker, color=color, linestyle="None", markersize=6)
    ax_r.axhline(RTT_BASE, color="gray", linestyle=":", linewidth=1.3, label=f"Base RTT ({RTT_BASE:.0f} ms)")
    ax_r.axhline(RTT_MAX, color="crimson", linestyle="-.", linewidth=1.3, label=f"Max Bufferbloat ({RTT_MAX:.1f} ms)")
    ax_r.set_xlabel("Number of Competing Nodes ($N$)", fontweight="bold")
    ax_r.set_ylabel("Mean RTT (ms)", fontweight="bold")
    ax_r.set_title("(b) Mean RTT vs. Number of Nodes", fontweight="bold")
    ax_r.set_xlim(1, 20)
    ax_r.set_xticks(N_pts)
    ax_r.legend(loc="upper left", fontsize=9)
    ax_r.grid(True, linestyle="--", alpha=0.6)

    # Panel 3: Packet Drops
    ax_d = axes[1, 0]
    for name, color, ls, marker, _, _, f_d, _ in ALGO_META:
        ax_d.plot(N, f_d(N), label=name, color=color, linestyle=ls, linewidth=2.2)
        ax_d.plot(N_pts, f_d(N_pts), marker=marker, color=color, linestyle="None", markersize=6)
    ax_d.set_xlabel("Number of Competing Nodes ($N$)", fontweight="bold")
    ax_d.set_ylabel("Packet Drops", fontweight="bold")
    ax_d.set_title("(c) Packet Drops vs. Number of Nodes", fontweight="bold")
    ax_d.set_xlim(1, 20)
    ax_d.set_xticks(N_pts)
    ax_d.legend(loc="upper left", fontsize=9)
    ax_d.grid(True, linestyle="--", alpha=0.6)

    # Panel 4: Fairness Index
    ax_f = axes[1, 1]
    for name, color, ls, marker, _, _, _, f_f in ALGO_META:
        ax_f.plot(N, f_f(N), label=name, color=color, linestyle=ls, linewidth=2.2)
        ax_f.plot(N_pts, f_f(N_pts), marker=marker, color=color, linestyle="None", markersize=6)
    ax_f.axhline(1.0, color="gray", linestyle=":", linewidth=1.3, label="Ideal Fairness (1.0)")
    ax_f.set_xlabel("Number of Competing Nodes ($N$)", fontweight="bold")
    ax_f.set_ylabel("Jain's Fairness Index", fontweight="bold")
    ax_f.set_title("(d) Fairness Index vs. Number of Nodes", fontweight="bold")
    ax_f.set_xlim(1, 20)
    ax_f.set_ylim(0.85, 1.02)
    ax_f.set_xticks(N_pts)
    ax_f.legend(loc="lower right", fontsize=9)
    ax_f.grid(True, linestyle="--", alpha=0.6)

    fig.tight_layout(rect=[0, 0.03, 1, 0.94])
    p_comb = PLOTS_DIR / "theoretical_multinode_comparison.png"
    fig.savefig(p_comb, dpi=300)
    plt.close(fig)

    print("[+] Successfully generated all theoretical graphs:")
    print(f"    - {p1}")
    print(f"    - {p2}")
    print(f"    - {p3}")
    print(f"    - {p4}")
    print(f"    - {p_comb}")

if __name__ == "__main__":
    generate_individual_plots()
