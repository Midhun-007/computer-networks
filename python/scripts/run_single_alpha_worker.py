#!/usr/bin/env python3
"""Worker script to execute a single TCP-DQN evaluation run for a given alpha in a clean process."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from stable_baselines3 import DQN

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "python"))

from tcp_dqn.config import DqnConfig, LinkConfig
from tcp_dqn.env import TcpDqnNs3Env


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--alpha", type=float, required=True)
    p.add_argument("--sim-time-s", type=float, default=20.0)
    p.add_argument("--model", type=Path, default=REPO_ROOT / "results" / "models" / "tcp_dqn.zip")
    p.add_argument("--traces-dir", type=Path, default=REPO_ROOT / "results" / "traces")
    p.add_argument("--out-csv", type=Path, required=True)
    p.add_argument("--stats-json", type=Path, required=True)
    return p.parse_args()


def main():
    args = parse_args()
    args.model = args.model.resolve()
    args.traces_dir = args.traces_dir.resolve()
    args.out_csv = args.out_csv.resolve()
    args.stats_json = args.stats_json.resolve()

    link = LinkConfig()
    link.sim_time_s = args.sim_time_s
    dqn_cfg = DqnConfig()
    dqn_cfg.alpha = args.alpha

    env = TcpDqnNs3Env(link_cfg=link, dqn_cfg=dqn_cfg)
    model = DQN.load(str(args.model), env=env)

    obs, _ = env.reset()
    done = False
    step_rewards = []

    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done, _, _ = env.step(int(action))
        step_rewards.append(float(reward))

    env.close()

    trace_file = args.traces_dir / f"tcp_dqn_{link.seed}.csv"
    df = pd.read_csv(trace_file)
    df["alpha"] = args.alpha
    df["step_reward"] = pd.Series(step_rewards)
    df.to_csv(args.out_csv, index=False)

    mean_t_bps = df["throughput_Bps_since_last_sample"].mean()
    mean_t_mbps = (mean_t_bps * 8.0) / 1e6
    mean_rtt = df["rtt_ms"].mean()
    mean_cwnd = df["cwnd_segments"].mean()
    mean_rew = float(pd.Series(step_rewards).mean()) if len(step_rewards) > 0 else 0.0
    lost_segs = int(df["cumulative_lost_segments"].iloc[-1]) if "cumulative_lost_segments" in df.columns else 0

    stats = {
        "alpha": args.alpha,
        "mean_throughput_mbps": float(mean_t_mbps),
        "mean_throughput_Bps": float(mean_t_bps),
        "mean_rtt_ms": float(mean_rtt),
        "mean_cwnd_segments": float(mean_cwnd),
        "mean_reward": float(mean_rew),
        "lost_segments": int(lost_segs),
    }

    with open(args.stats_json, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"Alpha {args.alpha:.2f} finished: Throughput={mean_t_mbps:.2f} Mbps, RTT={mean_rtt:.2f} ms, Reward={mean_rew:.3f}")


if __name__ == "__main__":
    main()
