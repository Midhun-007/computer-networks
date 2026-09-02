#ifndef TCP_DQN_CONSTANTS_H
#define TCP_DQN_CONSTANTS_H

#include <cstdint>

namespace ns3
{

namespace TcpDqnConstants
{

constexpr uint32_t OBS_DIM = 7;
constexpr uint32_t ACTION_DIM = 101;
constexpr uint32_t ACTION_CENTER = 50;
constexpr double OBS_LOW = 0.0;
constexpr double OBS_HIGH = 1e9;
constexpr double DEFAULT_ALPHA = 0.5;
constexpr double DEFAULT_TIME_STEP_S = 0.1;

} // namespace TcpDqnConstants

} // namespace ns3

#endif // TCP_DQN_CONSTANTS_H
