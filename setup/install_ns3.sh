#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
NS3_TAG="$(tr -d '[:space:]' < "${SCRIPT_DIR}/ns3_version.txt")"
NS3_DIR="${REPO_ROOT}/ns-3"
BUILD_DIR="${REPO_ROOT}/build"

APT_PACKAGES=(
    build-essential cmake ninja-build git python3-dev python3-pip python3-venv
    g++ pkg-config sqlite3 libsqlite3-dev
    libboost-all-dev libprotobuf-dev protobuf-compiler pybind11-dev
)

check_apt_packages() {
    local missing=()
    for pkg in "${APT_PACKAGES[@]}"; do
        if ! dpkg -s "$pkg" &>/dev/null; then
            missing+=("$pkg")
        fi
    done
    if [ ${#missing[@]} -gt 0 ]; then
        echo "Missing APT packages: ${missing[*]}"
        echo "Install with:"
        echo "  sudo apt update && sudo apt install -y ${APT_PACKAGES[*]}"
        if [ "$(id -u)" -eq 0 ]; then
            apt-get update
            apt-get install -y "${APT_PACKAGES[@]}"
        else
            exit 1
        fi
    fi
}

check_apt_packages

mkdir -p "${BUILD_DIR}"

if [ ! -d "${NS3_DIR}/.git" ]; then
    echo "Cloning ns-3 ${NS3_TAG}..."
    git clone --depth 1 --branch "${NS3_TAG}" https://gitlab.com/nsnam/ns-3-dev.git "${NS3_DIR}"
else
    echo "ns-3 directory exists; fetching ${NS3_TAG}..."
    git -C "${NS3_DIR}" fetch --depth 1 origin "refs/tags/${NS3_TAG}:refs/tags/${NS3_TAG}" || true
    git -C "${NS3_DIR}" checkout "${NS3_TAG}"
fi

# ns3-ai lives at contrib/ai (current upstream layout)
if [ ! -d "${NS3_DIR}/contrib/ai/.git" ]; then
    echo "Cloning ns3-ai into contrib/ai..."
    git clone --depth 1 https://github.com/hust-diangroup/ns3-ai.git "${NS3_DIR}/contrib/ai"
fi

# Copy (not symlink) tcp-dqn module for NTFS/WSL compatibility
echo "Installing tcp-dqn contrib module..."
rm -rf "${NS3_DIR}/contrib/tcp-dqn"
cp -r "${REPO_ROOT}/ns3-module/tcp-dqn" "${NS3_DIR}/contrib/tcp-dqn"

# Copy baseline topology into contrib for unified build
mkdir -p "${NS3_DIR}/contrib/tcp-dqn/examples"
cp "${REPO_ROOT}/baselines/tcp-dqn-baselines-topology.cc" \
    "${NS3_DIR}/contrib/tcp-dqn/examples/tcp-dqn-baselines-topology.cc"

# Python venv (recreate if copied from Windows or missing activate script)
if [ ! -f "${REPO_ROOT}/.venv/bin/activate" ]; then
    rm -rf "${REPO_ROOT}/.venv"
    python3 -m venv "${REPO_ROOT}/.venv"
fi
# shellcheck disable=SC1091
source "${REPO_ROOT}/.venv/bin/activate"
pip install --upgrade pip
pip install -r "${REPO_ROOT}/requirements.txt"
# ns-3.48 requires CMake >= 3.25; Ubuntu 22.04 ships 3.22
pip install "cmake>=3.25"
export PATH="${REPO_ROOT}/.venv/bin:${PATH}"

PYTHON_EXE="$(which python)"
echo "Using Python: ${PYTHON_EXE}"

cd "${NS3_DIR}"

echo "Configuring ns-3..."
./ns3 configure --enable-examples -- -DPython_EXECUTABLE="${PYTHON_EXE}" -DPython3_EXECUTABLE="${PYTHON_EXE}"

echo "Building ns3-ai core library..."
./ns3 build ai

echo "Installing ns3-ai Python interfaces..."
pip install -e contrib/ai/python_utils
pip install -e contrib/ai/model/gym-interface/py

# echo "Building ns3-ai RL-TCP reference example (verification step)..."
# ./ns3 build ns3ai_rltcp_gym

echo "Building tcp-dqn module and examples..."
./ns3 build tcp-dqn
./ns3 build tcp-dqn-topology
./ns3 build tcp-dqn-baselines-topology

echo "Running quick topology smoke test (10s)..."
./ns3 run "tcp-dqn-baselines-topology --simTimeS=10 --transport_prot=NewReno"

echo ""
echo "=== Setup complete ==="
echo "ns-3:     ${NS3_DIR} (${NS3_TAG})"
echo "Activate: source ${REPO_ROOT}/.venv/bin/activate"
echo "Train:    python ${REPO_ROOT}/python/scripts/train.py --timesteps 60000"
