#ifndef TCP_DQN_CONGESTION_OPS_H
#define TCP_DQN_CONGESTION_OPS_H

#include "tcp-dqn-env.h"

#include "ns3/tcp-congestion-ops.h"
#include "ns3/tcp-socket-base.h"

namespace ns3
{

/**
 * TCP congestion operations that delegate cwnd control to TcpDqnEnv (Eq. 5).
 */
class TcpDqnCongestionOps : public TcpCongestionOps
{
  public:
    static TypeId GetTypeId();
    TcpDqnCongestionOps();
    TcpDqnCongestionOps(const TcpDqnCongestionOps& sock);
    ~TcpDqnCongestionOps() override;

    std::string GetName() const override;
    uint32_t GetSsThresh(Ptr<const TcpSocketState> tcb, uint32_t bytesInFlight) override;
    void IncreaseWindow(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked) override;
    void PktsAcked(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked, const Time& rtt) override;
    void CongestionStateSet(Ptr<TcpSocketState> tcb, TcpSocketState::TcpCongState_t newState) override;
    Ptr<TcpCongestionOps> Fork() override;

  private:
    void CreateEnv();

    static uint64_t GenerateUuid();
    Ptr<TcpDqnEnv> m_env;
};

} // namespace ns3

#endif // TCP_DQN_CONGESTION_OPS_H
