#include "tcp-dqn-env.h"

#include "ns3/log.h"
#include "ns3/simulator.h"

#include <algorithm>
#include <cmath>

NS_LOG_COMPONENT_DEFINE("TcpDqnEnv");

namespace ns3
{

NS_OBJECT_ENSURE_REGISTERED(TcpDqnEnv);

TcpDqnEnv::TcpDqnEnv()
{
    SetOpenGymInterface(OpenGymInterface::Get());
}

TcpDqnEnv::~TcpDqnEnv()
{
}

TypeId
TcpDqnEnv::GetTypeId()
{
    static TypeId tid = TypeId("ns3::TcpDqnEnv")
                            .SetParent<OpenGymEnv>()
                            .SetGroupName("TcpDqn")
                            .AddConstructor<TcpDqnEnv>()
                            .AddAttribute("StepTime",
                                          "Decision interval in seconds (paper: 0.1s).",
                                          TimeValue(Seconds(TcpDqnConstants::DEFAULT_TIME_STEP_S)),
                                          MakeTimeAccessor(&TcpDqnEnv::m_timeStep),
                                          MakeTimeChecker())
                            .AddAttribute("Alpha",
                                          "Reward mixing factor alpha in Eq. (6).",
                                          DoubleValue(TcpDqnConstants::DEFAULT_ALPHA),
                                          MakeDoubleAccessor(&TcpDqnEnv::m_alpha),
                                          MakeDoubleChecker<double>(0.0, 1.0));
    return tid;
}

void
TcpDqnEnv::DoDispose()
{
    m_tcb = nullptr;
    OpenGymEnv::DoDispose();
}

void
TcpDqnEnv::SetNodeId(uint32_t id)
{
    m_nodeId = id;
}

void
TcpDqnEnv::SetSocketUuid(uint32_t id)
{
    m_socketUuid = id;
}

void
TcpDqnEnv::SetFlowStartTime(Time t)
{
    m_flowStartTime = t;
}

void
TcpDqnEnv::ResetEpisode()
{
    m_throughputMax = 0.0;
    m_rttMinMs = 0.0;
    m_rttMaxMs = 0.0;
    m_rewardRangeReady = false;
    m_ackCount = 0;
    m_rttSampleCount = 0;
    m_rttSum = Seconds(0);
    m_bytesAckedInterval = 0;
    m_lostSegmentsInterval = 0;
    m_lastReward = 0.0f;
    m_pendingAction = TcpDqnConstants::ACTION_CENTER;
}

float
TcpDqnEnv::ComputeReward(double throughput,
                         double throughputMax,
                         double rttMs,
                         double rttMinMs,
                         double rttMaxMs,
                         double alpha)
{
    // Paper Eq. (6). T_min is undefined in the paper; we assume T_min = 0.
    constexpr double throughputMin = 0.0;

    const double tDenom = throughputMax - throughputMin;
    const double rDenom = rttMaxMs - rttMinMs;

    if (tDenom <= 0.0 || rDenom <= 0.0)
    {
        return 0.0f;
    }

    const double throughputTerm = alpha * (throughput - throughputMin) / tDenom;
    const double rttTerm = (1.0 - alpha) * (rttMs - rttMinMs) / rDenom;
    return static_cast<float>(throughputTerm - rttTerm);
}

int32_t
TcpDqnEnv::ActionIndexToDeltaSegments(uint32_t actionIndex)
{
    if (actionIndex >= TcpDqnConstants::ACTION_DIM)
    {
        actionIndex = TcpDqnConstants::ACTION_CENTER;
    }
    return static_cast<int32_t>(actionIndex) - static_cast<int32_t>(TcpDqnConstants::ACTION_CENTER);
}

uint32_t
TcpDqnEnv::ApplyCwndDelta(uint32_t cwndBytes, int32_t deltaSegments, uint32_t segmentSize)
{
    const int64_t deltaBytes = static_cast<int64_t>(deltaSegments) * segmentSize;
    const int64_t newCwnd = static_cast<int64_t>(cwndBytes) + deltaBytes;
    const int64_t minCwnd = static_cast<int64_t>(segmentSize);
    return static_cast<uint32_t>(std::max(minCwnd, newCwnd));
}

Ptr<OpenGymSpace>
TcpDqnEnv::GetActionSpace()
{
    return CreateObject<OpenGymDiscreteSpace>(TcpDqnConstants::ACTION_DIM);
}

Ptr<OpenGymSpace>
TcpDqnEnv::GetObservationSpace()
{
    std::vector<uint32_t> shape{TcpDqnConstants::OBS_DIM};
    return CreateObject<OpenGymBoxSpace>(TcpDqnConstants::OBS_LOW,
                                         TcpDqnConstants::OBS_HIGH,
                                         shape,
                                         TypeNameGet<double>());
}

bool
TcpDqnEnv::GetGameOver()
{
    return false;
}

void
TcpDqnEnv::ScheduleNextStep()
{
    Simulator::Schedule(m_timeStep, &TcpDqnEnv::ScheduleNextStep, this);
    Notify();
}

void
TcpDqnEnv::AccumulateIntervalMetrics()
{
    if (!m_tcb)
    {
        return;
    }
}

Ptr<OpenGymDataContainer>
TcpDqnEnv::GetObservation()
{
    std::vector<uint32_t> shape{TcpDqnConstants::OBS_DIM};
    Ptr<OpenGymBoxContainer<double>> box = CreateObject<OpenGymBoxContainer<double>>(shape);

    const double relTime = (Simulator::Now() - m_flowStartTime).GetSeconds();
    const uint32_t segmentSize = m_tcb ? m_tcb->m_segmentSize : 1460;
    const uint32_t cwndBytes = m_tcb ? static_cast<uint32_t>(m_tcb->m_cWnd.Get()) : segmentSize;
    const uint32_t cwndSegments = std::max(1u, cwndBytes / segmentSize);
    const uint32_t bytesInFlight = m_tcb ? static_cast<uint32_t>(m_tcb->m_bytesInFlight.Get()) : 0;

    double avgRttMs = 0.0;
    if (m_rttSampleCount > 0)
    {
        avgRttMs = m_rttSum.GetSeconds() * 1000.0 / static_cast<double>(m_rttSampleCount);
    }

    const double throughput = m_bytesAckedInterval / m_timeStep.GetSeconds();

    // Update episode extrema and compute reward for the completed interval
    if (throughput > m_throughputMax)
    {
        m_throughputMax = throughput;
    }
    if (m_rttSampleCount > 0)
    {
        if (!m_rewardRangeReady || avgRttMs < m_rttMinMs)
        {
            m_rttMinMs = avgRttMs;
        }
        if (!m_rewardRangeReady || avgRttMs > m_rttMaxMs)
        {
            m_rttMaxMs = avgRttMs;
        }
        m_rewardRangeReady = true;
    }

    m_lastReward = ComputeReward(throughput,
                                 m_throughputMax,
                                 avgRttMs,
                                 m_rttMinMs,
                                 m_rttMaxMs,
                                 m_alpha);

    box->AddValue(relTime);
    box->AddValue(static_cast<double>(cwndSegments));
    box->AddValue(static_cast<double>(bytesInFlight));
    box->AddValue(static_cast<double>(m_ackCount));
    box->AddValue(avgRttMs);
    box->AddValue(throughput);
    box->AddValue(static_cast<double>(m_lostSegmentsInterval));

    // Reset per-interval counters
    m_ackCount = 0;
    m_rttSampleCount = 0;
    m_rttSum = Seconds(0);
    m_bytesAckedInterval = 0;
    m_lostSegmentsInterval = 0;

    return box;
}

float
TcpDqnEnv::GetReward()
{
    return m_lastReward;
}

std::string
TcpDqnEnv::GetExtraInfo()
{
    return "tcp-dqn";
}

bool
TcpDqnEnv::ExecuteActions(Ptr<OpenGymDataContainer> action)
{
    Ptr<OpenGymDiscreteContainer> discrete = DynamicCast<OpenGymDiscreteContainer>(action);
    if (!discrete)
    {
        return false;
    }
    m_pendingAction = discrete->GetValue();
    return true;
}

void
TcpDqnEnv::BindTcb(Ptr<TcpSocketState> tcb)
{
    m_tcb = tcb;
    if (!m_started)
    {
        m_started = true;
        ScheduleNextStep();
    }
}

void
TcpDqnEnv::PktsAcked(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked, const Time& rtt)
{
    m_tcb = tcb;
    m_ackCount += segmentsAcked;
    m_rttSampleCount++;
    m_rttSum += rtt;
    m_bytesAckedInterval += static_cast<uint64_t>(segmentsAcked) * tcb->m_segmentSize;
}

void
TcpDqnEnv::CongestionStateSet(Ptr<TcpSocketState> tcb, TcpSocketState::TcpCongState_t newState)
{
    m_tcb = tcb;
    if (newState == TcpSocketState::CA_LOSS || newState == TcpSocketState::CA_RECOVERY)
    {
        m_lostSegmentsInterval++;
    }
}

uint32_t
TcpDqnEnv::ApplyAction(Ptr<TcpSocketState> tcb)
{
    m_tcb = tcb;
    const int32_t delta = ActionIndexToDeltaSegments(m_pendingAction);
    tcb->m_cWnd = ApplyCwndDelta(static_cast<uint32_t>(tcb->m_cWnd.Get()), delta, tcb->m_segmentSize);
    return static_cast<uint32_t>(tcb->m_cWnd.Get());
}

} // namespace ns3
