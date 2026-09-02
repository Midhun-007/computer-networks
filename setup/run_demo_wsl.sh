#!/usr/bin/env bash
set -euo pipefail
cd ~/tcp-dqn-ns3/ns-3
export PATH=../.venv/bin:/usr/bin:/bin

cp '/mnt/d/vickram/NIT-TRICHY/SEM 5/projCN-1/ns3-module/tcp-dqn/helper/tcp-dqn-topology-helper.h' contrib/tcp-dqn/helper/
cp '/mnt/d/vickram/NIT-TRICHY/SEM 5/projCN-1/ns3-module/tcp-dqn/examples/tcp-dqn-topology.cc' contrib/tcp-dqn/examples/
cp '/mnt/d/vickram/NIT-TRICHY/SEM 5/projCN-1/baselines/tcp-dqn-baselines-topology.cc' contrib/tcp-dqn/examples/

./ns3 build tcp-dqn-baselines-topology tcp-dqn-topology

TRACE_DIR=~/tcp-dqn-ns3/results/traces
mkdir -p "$TRACE_DIR"
rm -f "$TRACE_DIR"/*.csv

for prot in NewReno Cubic HighSpeed; do
  echo "Running baseline: $prot"
  ./ns3 run "tcp-dqn-baselines-topology --simTimeS=10 --transport_prot=${prot} --traceDir=${TRACE_DIR}"
done

echo "--- Trace summary ---"
wc -l "$TRACE_DIR"/*.csv
echo "--- NewReno sample ---"
head -8 "$TRACE_DIR/NewReno_42.csv"
