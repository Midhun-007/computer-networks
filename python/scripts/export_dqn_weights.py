#!/usr/bin/env python3
"""Export trained SB3 DQN model weights to a C++ header file for fast native inference in ns-3."""

from pathlib import Path
import numpy as np
from stable_baselines3 import DQN

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = REPO_ROOT / "results" / "models" / "tcp_dqn.zip"
HEADER_PATH = REPO_ROOT / "ns3-module" / "tcp-dqn" / "model" / "tcp-dqn-weights.h"
HEADER_PATH_NS3 = REPO_ROOT / "ns-3" / "contrib" / "tcp-dqn" / "model" / "tcp-dqn-weights.h"

def export_weights():
    model = DQN.load(str(MODEL_PATH), device="cpu")
    q_net = model.policy.q_net.q_net

    w0 = q_net[0].weight.detach().numpy() # (64, 7)
    b0 = q_net[0].bias.detach().numpy()   # (64,)
    w2 = q_net[2].weight.detach().numpy() # (64, 64)
    b2 = q_net[2].bias.detach().numpy()   # (64,)
    w4 = q_net[4].weight.detach().numpy() # (101, 64)
    b4 = q_net[4].bias.detach().numpy()   # (101,)

    lines = []
    lines.append("#ifndef TCP_DQN_WEIGHTS_H")
    lines.append("#define TCP_DQN_WEIGHTS_H")
    lines.append("")
    lines.append("// Auto-generated weights from trained SB3 DQN model (tcp_dqn.zip)")
    lines.append("#include <cstdint>")
    lines.append("#include <algorithm>")
    lines.append("#include <cmath>")
    lines.append("")
    lines.append("namespace ns3 {")
    lines.append("namespace TcpDqnModel {")
    lines.append("")
    lines.append("constexpr int OBS_DIM = 7;")
    lines.append("constexpr int HIDDEN_DIM = 64;")
    lines.append("constexpr int ACTION_DIM = 101;")
    lines.append("")

    # W0
    lines.append(f"static const float W0[{w0.shape[0]}][{w0.shape[1]}] = {{")
    for row in w0:
        lines.append("    {" + ", ".join(f"{v:.8e}f" for v in row) + "},")
    lines.append("};")
    lines.append("")

    # B0
    lines.append(f"static const float B0[{b0.shape[0]}] = {{")
    lines.append("    " + ", ".join(f"{v:.8e}f" for v in b0))
    lines.append("};")
    lines.append("")

    # W2
    lines.append(f"static const float W2[{w2.shape[0]}][{w2.shape[1]}] = {{")
    for row in w2:
        lines.append("    {" + ", ".join(f"{v:.8e}f" for v in row) + "},")
    lines.append("};")
    lines.append("")

    # B2
    lines.append(f"static const float B2[{b2.shape[0]}] = {{")
    lines.append("    " + ", ".join(f"{v:.8e}f" for v in b2))
    lines.append("};")
    lines.append("")

    # W4
    lines.append(f"static const float W4[{w4.shape[0]}][{w4.shape[1]}] = {{")
    for row in w4:
        lines.append("    {" + ", ".join(f"{v:.8e}f" for v in row) + "},")
    lines.append("};")
    lines.append("")

    # B4
    lines.append(f"static const float B4[{b4.shape[0]}] = {{")
    lines.append("    " + ", ".join(f"{v:.8e}f" for v in b4))
    lines.append("};")
    lines.append("")

    # Inference function
    lines.append("inline uint32_t PredictAction(const float obs[OBS_DIM], float alpha = 0.5f)")
    lines.append("{")
    lines.append("    float h1[HIDDEN_DIM];")
    lines.append("    for (int i = 0; i < HIDDEN_DIM; ++i) {")
    lines.append("        float sum = B0[i];")
    lines.append("        for (int j = 0; j < OBS_DIM; ++j) {")
    lines.append("            sum += W0[i][j] * obs[j];")
    lines.append("        }")
    lines.append("        h1[i] = std::max(0.0f, sum);")
    lines.append("    }")
    lines.append("")
    lines.append("    float h2[HIDDEN_DIM];")
    lines.append("    for (int i = 0; i < HIDDEN_DIM; ++i) {")
    lines.append("        float sum = B2[i];")
    lines.append("        for (int j = 0; j < HIDDEN_DIM; ++j) {")
    lines.append("            sum += W2[i][j] * h1[j];")
    lines.append("        }")
    lines.append("        h2[i] = std::max(0.0f, sum);")
    lines.append("    }")
    lines.append("")
    lines.append("    float bestQ = -1e30f;")
    lines.append("    uint32_t bestAction = 50;")
    lines.append("    const float alphaWeight = 30.0f;")
    lines.append("    for (int i = 0; i < ACTION_DIM; ++i) {")
    lines.append("        float q = B4[i];")
    lines.append("        for (int j = 0; j < HIDDEN_DIM; ++j) {")
    lines.append("            q += W4[i][j] * h2[j];")
    lines.append("        }")
    lines.append("        float delta = static_cast<float>(i - 50);")
    lines.append("        q += (alpha - 0.5f) * alphaWeight * delta;")
    lines.append("        if (q > bestQ) {")
    lines.append("            bestQ = q;")
    lines.append("            bestAction = static_cast<uint32_t>(i);")
    lines.append("        }")
    lines.append("    }")
    lines.append("    return bestAction;")
    lines.append("}")
    lines.append("")
    lines.append("} // namespace TcpDqnModel")
    lines.append("} // namespace ns3")
    lines.append("")
    lines.append("#endif // TCP_DQN_WEIGHTS_H")

    code = "\n".join(lines)
    HEADER_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEADER_PATH.write_text(code, encoding="utf-8")
    HEADER_PATH_NS3.parent.mkdir(parents=True, exist_ok=True)
    HEADER_PATH_NS3.write_text(code, encoding="utf-8")
    print(f"Exported weights to {HEADER_PATH} and {HEADER_PATH_NS3}")

if __name__ == "__main__":
    export_weights()
