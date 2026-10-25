#!/usr/bin/env python3
"""Evaluate trained TCP-DQN vs ns-3 TCP baselines."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "python"))

from stable_baselines3 import DQN

from tcp_dqn.config import DqnConfig, LinkConfig, ns3_dir
from tcp_dqn.env import TcpDqnNs3Env
from tcp_dqn.metrics import (
    load_trace,
    plot_cdf,
    plot_loss_bars,
    plot_time_series,
    summarize_trace,
    write_summary_md,
)

BASELINES = ["NewReno", "Cubic", "HighSpeed"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate TCP-DQN and baselines")
    p.add_argument("--model", type=Path, default=REPO_ROOT / "results" / "models" / "tcp_dqn.zip")
    p.add_argument("--link-config", type=Path, default=None)
    p.add_argument("--dqn-config", type=Path, default=None)
    p.add_argument("--plots-dir", type=Path, default=REPO_ROOT / "results" / "plots")
    p.add_argument("--traces-dir", type=Path, default=REPO_ROOT / "results" / "traces")
    p.add_argument("--summary-out", type=Path, default=REPO_ROOT / "results" / "summary.md")
    p.add_argument("--baselines-only", action="store_true", help="Skip DQN eval even if model exists")
    p.add_argument("--skip-run", action="store_true", help="Load existing traces only")
    p.add_argument("--sim-time-s", type=float, default=None, help="Override simulation duration")
    return p.parse_args()

def run_baseline(ns3: Path, prot: str, link: LinkConfig, traces_dir: Path) -> Path:
    args = (
        f"--transport_prot={prot} "
        f"--bandwidthMbps={link.bandwidth_mbps} "
        f"--baseRttMs={link.base_rtt_ms} "
        f"--lossRate={link.loss_rate} "
        f"--queuePackets={link.queue_packets} "
        f"--segmentSize={link.segment_size} "
        f"--simTimeS={link.sim_time_s} "
        f"--seed={link.seed} "
        f"--traceDir={traces_dir}"
    )

    cmd = [
        str(ns3 / "ns3"),
        "run",
        f"tcp-dqn-baselines-topology {args}",
    ]

    subprocess.run(cmd, cwd=ns3, check=True)
    return traces_dir / f"{prot}_{link.seed}.csv"

def run_dqn_eval(model_path: Path, link: LinkConfig, dqn: DqnConfig, traces_dir: Path) -> Path:
    env = TcpDqnNs3Env(link_cfg=link, dqn_cfg=dqn)
    model = DQN.load(str(model_path), env=env)
    obs, _ = env.reset()
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, _, done, _, _ = env.step(int(action))
    env.close()
    return traces_dir / f"tcp_dqn_{link.seed}.csv"


def main() -> None:
    args = parse_args()
    args.model = args.model.resolve()
    args.plots_dir = args.plots_dir.resolve()
    args.traces_dir = args.traces_dir.resolve()
    args.summary_out = args.summary_out.resolve()
    link = LinkConfig.from_yaml(args.link_config)
    dqn = DqnConfig.from_yaml(args.dqn_config)
    if args.sim_time_s is not None:
        link.sim_time_s = args.sim_time_s
    ns3 = ns3_dir()
    args.traces_dir.mkdir(parents=True, exist_ok=True)

    traces = {}
    if not args.baselines_only and args.model.exists() and not args.skip_run:
        traces["TCP-DQN"] = load_trace(run_dqn_eval(args.model, link, dqn, args.traces_dir))
    elif not args.baselines_only and args.model.exists() and args.skip_run:
        dqn_trace = args.traces_dir / f"tcp_dqn_{link.seed}.csv"
        if dqn_trace.exists():
            traces["TCP-DQN"] = load_trace(dqn_trace)
    elif not args.baselines_only:
        print(f"Warning: model not found at {args.model}; skipping DQN eval run")

    for prot in BASELINES:
        path = args.traces_dir / f"{prot}_{link.seed}.csv"
        if args.skip_run and path.exists():
            traces[prot] = load_trace(path)
        else:
            traces[prot] = load_trace(run_baseline(ns3, prot, link, args.traces_dir))

    plot_time_series(
        traces,
        "throughput_Bps_since_last_sample",
        "Throughput (B/s)",
        args.plots_dir / "throughput_comparison.png",
        "Throughput comparison",
    )
    plot_cdf(
        traces,
        "throughput_Bps_since_last_sample",
        args.plots_dir / "throughput_cdf.png",
        "Throughput CDF",
    )
    plot_time_series(
        traces,
        "rtt_ms",
        "RTT (ms)",
        args.plots_dir / "rtt_comparison.png",
        "RTT comparison",
    )
    plot_cdf(traces, "rtt_ms", args.plots_dir / "rtt_cdf.png", "RTT CDF")

    summaries = {name: summarize_trace(df, link.sim_time_s) for name, df in traces.items()}
    plot_loss_bars(summaries, args.plots_dir / "packet_loss_comparison.png")
    write_summary_md(summaries, args.summary_out, BASELINES)

    print(f"Plots written to {args.plots_dir}")
    print(f"Summary written to {args.summary_out}")


if __name__ == "__main__":
    main()
