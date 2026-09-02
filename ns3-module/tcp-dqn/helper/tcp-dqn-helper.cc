#include "tcp-dqn-helper.h"

#include "../model/tcp-dqn-congestion-ops.h"
#include "../model/tcp-dqn-env.h"

#include "ns3/config.h"

namespace ns3
{

void
TcpDqnHelper::Install()
{
    Config::SetDefault("ns3::TcpL4Protocol::SocketType",
                       TypeIdValue(TcpDqnCongestionOps::GetTypeId()));
}

void
TcpDqnHelper::SetAlpha(double alpha)
{
    Config::SetDefault("ns3::TcpDqnEnv::Alpha", DoubleValue(alpha));
}

void
TcpDqnHelper::SetStepTime(double stepTimeS)
{
    Config::SetDefault("ns3::TcpDqnEnv::StepTime", TimeValue(Seconds(stepTimeS)));
}

} // namespace ns3
