#ifndef TCP_DQN_HELPER_H
#define TCP_DQN_HELPER_H

#include "ns3/tcp-l4-protocol.h"

namespace ns3
{

/**
 * Install TcpDqn congestion control as the default socket type.
 */
class TcpDqnHelper
{
  public:
    static void Install();
    static void SetAlpha(double alpha);
    static void SetStepTime(double stepTimeS);
};

} // namespace ns3

#endif // TCP_DQN_HELPER_H
