#include "tcp-dqn-congestion-ops.h"

#include "ns3/log.h"
#include "ns3/traced-value.h"

NS_LOG_COMPONENT_DEFINE("TcpDqnCongestionOps");

namespace ns3
{

namespace
{

uint32_t
Val(uint32_t v)
{
    return v;
}

template <typename T>
uint32_t
Val(const TracedValue<T>& v)
{
    return static_cast<uint32_t>(v.Get());
}

} // namespace

NS_OBJECT_ENSURE_REGISTERED(TcpDqnCongestionOps);

TypeId
TcpDqnCongestionOps::GetTypeId()
{
    static TypeId tid = TypeId("ns3::TcpDqnCongestionOps")
                            .SetParent<TcpCongestionOps>()
                            .SetGroupName("TcpDqn")
                            .AddConstructor<TcpDqnCongestionOps>();
    return tid;
}

TcpDqnCongestionOps::TcpDqnCongestionOps()
    : TcpCongestionOps()
{
}

TcpDqnCongestionOps::TcpDqnCongestionOps(const TcpDqnCongestionOps& sock)
    : TcpCongestionOps(sock)
    , m_env(sock.m_env)
{
}

TcpDqnCongestionOps::~TcpDqnCongestionOps()
{
    m_env = nullptr;
}

std::string
TcpDqnCongestionOps::GetName() const
{
    return "TcpDqn";
}

uint64_t
TcpDqnCongestionOps::GenerateUuid()
{
    static uint64_t uuid = 0;
    uuid++;
    return uuid;
}

void
TcpDqnCongestionOps::CreateEnv()
{
    if (m_env)
    {
        return;
    }
    m_env = CreateObject<TcpDqnEnv>();
    m_env->SetSocketUuid(static_cast<uint32_t>(GenerateUuid()));
}

uint32_t
TcpDqnCongestionOps::GetSsThresh(Ptr<const TcpSocketState> tcb, uint32_t bytesInFlight)
{
    if (!m_env)
    {
        CreateEnv();
    }
    if (m_env)
    {
        m_env->BindTcb(ConstCast<TcpSocketState>(tcb));
    }
    (void)bytesInFlight;
    return std::max(Val(tcb->m_ssThresh), Val(tcb->m_cWnd));
}

void
TcpDqnCongestionOps::IncreaseWindow(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked)
{
    if (!m_env)
    {
        CreateEnv();
    }
    if (m_env)
    {
        m_env->BindTcb(tcb);
        m_env->ApplyAction(tcb);
    }
    (void)segmentsAcked;
}

void
TcpDqnCongestionOps::PktsAcked(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked, const Time& rtt)
{
    if (!m_env)
    {
        CreateEnv();
    }
    if (m_env)
    {
        m_env->PktsAcked(tcb, segmentsAcked, rtt);
    }
}

void
TcpDqnCongestionOps::CongestionStateSet(Ptr<TcpSocketState> tcb,
                                        TcpSocketState::TcpCongState_t newState)
{
    if (!m_env)
    {
        CreateEnv();
    }
    if (m_env)
    {
        m_env->CongestionStateSet(tcb, newState);
    }
}

Ptr<TcpCongestionOps>
TcpDqnCongestionOps::Fork()
{
    Ptr<TcpDqnCongestionOps> copy = CopyObject<TcpDqnCongestionOps>(this);
    copy->m_env = nullptr;
    return copy;
}

} // namespace ns3
