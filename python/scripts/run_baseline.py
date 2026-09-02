#!/usr/bin/env python3
"""Run a single baseline ns-3 simulation for debugging."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "python"))

from tcp_dqn.config import LinkConfig, ns3_dir


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--transport_prot", choices=["NewReno", "Cubic", "HighSpeed"], default="NewReno")
    p.add_argument("--simTimeS", type=float, default=10.0)
    p.add_argument("--link-config", type=Path, default=None)
    args = p.parse_args()

    link = LinkConfig.from_yaml(args.link_config)
    link.sim_time_s = args.simTimeS
    ns3 = ns3_dir()
    traces_dir = REPO_ROOT / "results" / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(ns3 / "ns3"),
        "run",
        "tcp-dqn-baselines-topology -- "
        f"--transport_prot={args.transport_prot} "
        f"--bandwidthMbps={link.bandwidth_mbps} "
        f"--baseRttMs={link.base_rtt_ms} "
        f"--lossRate={link.loss_rate} "
        f"--queuePackets={link.queue_packets} "
        f"--segmentSize={link.segment_size} "
        f"--simTimeS={link.sim_time_s} "
        f"--seed={link.seed} "
        f"--traceDir={traces_dir}",
    ]
    subprocess.run(cmd, cwd=ns3, check=True)
    print(f"Trace: {traces_dir / f'{args.transport_prot}_{link.seed}.csv'}")


if __name__ == "__main__":
    main()
