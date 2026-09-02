# ns3-ai Bridge Notes (ground truth)

This document records the **actual** ns3-ai integration surface used by this project.
Do not guess these values across releases — verify against your installed `contrib/ai`.

## ns-3 version

- Pinned in `setup/ns3_version.txt`: **ns-3.48**

## ns3-ai location

Upstream installs ns3-ai as an ns-3 contrib module at:

```
ns-3/contrib/ai/
```

(not `contrib/ns3-ai`).

## Python packages

After `./ns3 configure` and `./ns3 build ai`:

```bash
pip install -e contrib/ai/python_utils
pip install -e contrib/ai/model/gym-interface/py
```

| Item | Value |
|------|-------|
| Import | `import ns3ai_gym_env` |
| Gym registration | `ns3ai_gym_env/Ns3-v0` |
| Factory call | `gym.make("ns3ai_gym_env/Ns3-v0", targetName=..., ns3Path=..., ns3Settings={...})` |

## Reference example (build before adapting)

```bash
cd ns-3
./ns3 build ns3ai_rltcp_gym
cd contrib/ai/examples/rl-tcp/use-gym
python run_rl_tcp.py --use_rl --result --show_log --seed=10
```

## C++ OpenGym base classes

| Header | Symbols |
|--------|---------|
| `ns3/ai-module.h` | `OpenGymEnv`, `OpenGymInterface`, `OpenGymBoxSpace`, `OpenGymDiscreteSpace`, `OpenGymBoxContainer`, `OpenGymDiscreteContainer` |

Our `TcpDqnEnv` subclasses `OpenGymEnv` exactly like ns3-ai's `TcpTimeStepEnv`.

## TCP-DQN target binary

| CMake target | Role |
|--------------|------|
| `tcp-dqn-topology` | RL-controlled simulation (OpenGym) |
| `tcp-dqn-baselines-topology` | NewReno / Cubic / HighSpeed baselines |

Python `targetName` for training: **`tcp-dqn-topology`**.

## Shared memory cleanup

If a run fails to start because shared memory is busy:

```bash
cd ns-3/contrib/ai
./freeshm.sh
```

## Version-specific quirks

- ns3-ai RL-TCP uses **16-dimensional** uint64 observations; TCP-DQN uses **7-dimensional** float64 observations per the paper.
- ns3-ai RL-TCP actions are a 2-D uint32 box `[ssThresh, cWnd]`; TCP-DQN uses `Discrete(101)` per Eq. (5).
- `ns3Path` passed to `gym.make` must be the absolute path to the `ns-3` directory containing the `./ns3` wrapper.
