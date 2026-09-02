#!/usr/bin/env bash
# Sync Windows project -> WSL, rebuild, run baselines, plot, optional DQN smoke test.
set -euo pipefail

WIN_SRC='/mnt/d/vickram/NIT-TRICHY/SEM 5/projCN-1'
WSL_ROOT=~/tcp-dqn-ns3

echo "==> Syncing project files to ${WSL_ROOT}"
rsync -a --delete \
  --exclude '.venv' --exclude 'ns-3' --exclude '.pytest_cache' --exclude 'results/traces' \
  "${WIN_SRC}/" "${WSL_ROOT}/"

cd "${WSL_ROOT}/ns-3"
export PATH="${WSL_ROOT}/.venv/bin:/usr/bin:/bin"
source "${WSL_ROOT}/.venv/bin/activate"

echo "==> Rebuilding examples"
./ns3 build tcp-dqn-baselines-topology tcp-dqn-topology

TRACE_DIR="${WSL_ROOT}/results/traces"
PLOT_DIR="${WSL_ROOT}/results/plots"
mkdir -p "${TRACE_DIR}" "${PLOT_DIR}"
rm -f "${TRACE_DIR}"/*.csv

echo "==> Running baselines (30s each)"
for prot in NewReno Cubic HighSpeed; do
  echo "  ${prot}..."
  ./ns3 run "tcp-dqn-baselines-topology --simTimeS=30 --transport_prot=${prot} --traceDir=${TRACE_DIR}"
done

echo "==> Trace throughput check"
python3 - <<'PY'
import pandas as pd
from pathlib import Path
for csv in sorted(Path.home().joinpath("tcp-dqn-ns3/results/traces").glob("*.csv")):
    df = pd.read_csv(csv)
    tp = df["throughput_Bps_since_last_sample"].mean()
    print(f"  {csv.stem}: mean throughput = {tp/1e6:.2f} Mbps")
PY

echo "==> Generating plots"
cd "${WSL_ROOT}"
python3 python/scripts/evaluate.py --baselines-only --skip-run --sim-time-s 30

echo "==> DQN smoke test (20 timesteps, 15s sim)"
python3 python/scripts/train.py --timesteps 20 --sim-time-s 15 || echo "DQN smoke test failed (see log above)"

echo "==> Copying results to Windows project"
mkdir -p "${WIN_SRC}/results/traces" "${WIN_SRC}/results/plots" "${WIN_SRC}/results/models"
cp -f "${TRACE_DIR}"/*.csv "${WIN_SRC}/results/traces/" 2>/dev/null || true
cp -f "${PLOT_DIR}"/*.png "${WIN_SRC}/results/plots/" 2>/dev/null || true
cp -f "${WSL_ROOT}/results/models/"* "${WIN_SRC}/results/models/" 2>/dev/null || true
cp -f "${WSL_ROOT}/results/summary.md" "${WIN_SRC}/results/" 2>/dev/null || true

echo "==> DONE"
