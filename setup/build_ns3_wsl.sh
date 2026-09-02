#!/usr/bin/env bash
set -euo pipefail
cd ~/tcp-dqn-ns3/ns-3
source ../.venv/bin/activate
export PATH="$HOME/tcp-dqn-ns3/.venv/bin:$PATH"
PY="$(which python)"
if [ ! -f cmake-cache/CMakeCache.txt ]; then
  ./ns3 configure --enable-examples --enable-tests -- -DPython_EXECUTABLE="$PY" -DPython3_EXECUTABLE="$PY"
fi
./ns3 build ai
pip install -q -e contrib/ai/python_utils
pip install -q -e contrib/ai/model/gym-interface/py
./ns3 build tcp-dqn tcp-dqn-topology tcp-dqn-baselines-topology
echo "BUILD_OK"
