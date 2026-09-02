#ifndef TCP_DQN_ENV_H
#define TCP_DQN_ENV_H

#include "tcp-dqn-constants.h"

#include "ns3/ai-module.h"
#include "ns3/tcp-socket-base.h"
#include "ns3/tcp-socket-state.h"

namespace ns3
{

/**
 * OpenGym environment for TCP-DQN (Wang et al. 2021).
 *
 * Observation (7 features, every 0.1s):
 *   0 relative connection time (s)
 *   1 cwnd (segments)
 *   2 bytes in flight
 *   3 ACK count since last interval
 *   4 average RTT over interval (ms)
 *   5 throughput over interval (bytes/s)
 *   6 lost segments over interval
 *
 * Action: Discrete(101) index i; delta segments n = i - 50.
 */
class TcpDqnEnv : public OpenGymEnv
{
  public:
    TcpDqnEnv();
    ~TcpDqnEnv() override;
    static TypeId GetTypeId();
    void DoDispose() override;

    void SetNodeId(uint32_t id);
    void SetSocketUuid(uint32_t id);
    void SetFlowStartTime(Time t);
    void ResetEpisode();

    // OpenGym interface
    Ptr<OpenGymSpace> GetActionSpace() override;
    Ptr<OpenGymSpace> GetObservationSpace() override;
    bool GetGameOver() override;
    Ptr<OpenGymDataContainer> GetObservation() override;
    float GetReward() override;
    std::string GetExtraInfo() override;
    bool ExecuteActions(Ptr<OpenGymDataContainer> action) override;

    // TCP congestion-control callbacks (called from TcpDqnCongestionOps)
    void BindTcb(Ptr<TcpSocketState> tcb);
    void PktsAcked(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked, const Time& rtt);
    void CongestionStateSet(Ptr<TcpSocketState> tcb, TcpSocketState::TcpCongState_t newState);
    uint32_t ApplyAction(Ptr<TcpSocketState> tcb);

    // Exposed for unit tests
    static float ComputeReward(double throughput,
                               double throughputMax,
                               double rttMs,
                               double rttMinMs,
                               double rttMaxMs,
                               double alpha);
    static int32_t ActionIndexToDeltaSegments(uint32_t actionIndex);
    static uint32_t ApplyCwndDelta(uint32_t cwndBytes, int32_t deltaSegments, uint32_t segmentSize);

  private:
    void ScheduleNextStep();
    void AccumulateIntervalMetrics();

    uint32_t m_nodeId{0};
    uint32_t m_socketUuid{0};
    Time m_flowStartTime{Seconds(0)};
    Time m_timeStep{Seconds(TcpDqnConstants::DEFAULT_TIME_STEP_S)};
    double m_alpha{TcpDqnConstants::DEFAULT_ALPHA};

    Ptr<TcpSocketState> m_tcb;
    bool m_started{false};

    // Interval accumulators (reset each step)
    uint64_t m_ackCount{0};
    uint64_t m_rttSampleCount{0};
    Time m_rttSum{Seconds(0)};
    uint64_t m_bytesAckedInterval{0};
    uint64_t m_lostSegmentsInterval{0};

    // Episode trackers for reward Eq. (6)
    // T_min is not defined in the paper; we assume 0 (documented in ComputeReward).
    double m_throughputMax{0.0};
    double m_rttMinMs{0.0};
    double m_rttMaxMs{0.0};
    bool m_rewardRangeReady{false};

    float m_lastReward{0.0f};
    uint32_t m_pendingAction{TcpDqnConstants::ACTION_CENTER};
};

} // namespace ns3

#endif // TCP_DQN_ENV_H
