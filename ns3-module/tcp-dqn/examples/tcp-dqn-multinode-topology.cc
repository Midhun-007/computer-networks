#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/error-model.h"
#include "ns3/internet-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/traffic-control-module.h"
#include "ns3/tcp-bbr.h"
#include "ns3/tcp-cubic.h"
#include "ns3/tcp-highspeed.h"
#include "ns3/tcp-socket-base.h"

#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("TcpDqnMultiNodeTopology");

struct FlowTraceState
{
    uint32_t flowId{0};
    uint64_t cumulativeLostSegments{0};
    uint64_t bytesAckedSinceLast{0};
    uint32_t lastCwndSegments{0};
    double lastRttMs{0.0};
};

static std::vector<FlowTraceState> gFlowTraces;
static std::ofstream gFlowsCsv;
static std::ofstream gQueueCsv;
static double gSampleIntervalS = 0.1;
static uint32_t gSegmentSize = 1460;
static uint64_t gBottleneckDrops = 0;
static uint32_t gCurrentQueuePackets = 0;
static double gAlpha = 0.5;

static void
OnQueueDrop(Ptr<const QueueDiscItem> item)
{
    gBottleneckDrops++;
}

static void
OnQueuePackets(uint32_t oldValue, uint32_t newValue)
{
    gCurrentQueuePackets = newValue;
}

static void
OnFlowCwnd(uint32_t flowId, uint32_t oldCwnd, uint32_t newCwnd)
{
    (void)oldCwnd;
    if (flowId < gFlowTraces.size())
    {
        gFlowTraces[flowId].lastCwndSegments = std::max(1u, newCwnd / gSegmentSize);
    }
}

static void
OnFlowRtt(uint32_t flowId, Time oldRtt, Time newRtt)
{
    (void)oldRtt;
    if (flowId < gFlowTraces.size())
    {
        gFlowTraces[flowId].lastRttMs = newRtt.GetSeconds() * 1000.0;
    }
}

static void
OnFlowTx(uint32_t flowId, Ptr<const Packet> packet, const TcpHeader& header, Ptr<const TcpSocketBase> sock)
{
    (void)header;
    (void)sock;
    if (flowId < gFlowTraces.size())
    {
        gFlowTraces[flowId].bytesAckedSinceLast += packet->GetSize();
    }
}

static void
OnFlowCongState(uint32_t flowId, TcpSocketState::TcpCongState_t oldState, TcpSocketState::TcpCongState_t newState)
{
    (void)oldState;
    if (newState == TcpSocketState::CA_LOSS || newState == TcpSocketState::CA_RECOVERY)
    {
        if (flowId < gFlowTraces.size())
        {
            gFlowTraces[flowId].cumulativeLostSegments++;
        }
    }
}

static void
PeriodicSample()
{
    const double now = Simulator::Now().GetSeconds();

    if (gFlowsCsv.is_open())
    {
        for (size_t i = 0; i < gFlowTraces.size(); ++i)
        {
            const double throughput = gFlowTraces[i].bytesAckedSinceLast / gSampleIntervalS;
            gFlowsCsv << now << "," << i << ","
                      << gFlowTraces[i].lastCwndSegments << ","
                      << gFlowTraces[i].lastRttMs << ","
                      << throughput << ","
                      << gFlowTraces[i].cumulativeLostSegments << "\n";
            gFlowTraces[i].bytesAckedSinceLast = 0;
        }
    }

    if (gQueueCsv.is_open())
    {
        gQueueCsv << now << "," << gCurrentQueuePackets << "," << gBottleneckDrops << "\n";
    }

    Simulator::Schedule(Seconds(gSampleIntervalS), &PeriodicSample);
}

#include "../model/tcp-dqn-weights.h"

namespace ns3
{

class TcpDqnNativeOps : public TcpCongestionOps
{
public:
    static TypeId GetTypeId()
    {
        static TypeId tid = TypeId("ns3::TcpDqnNativeOps")
                                .SetParent<TcpCongestionOps>()
                                .SetGroupName("TcpDqn")
                                .AddConstructor<TcpDqnNativeOps>();
        return tid;
    }

    TcpDqnNativeOps() : TcpCongestionOps() {}

    TcpDqnNativeOps(const TcpDqnNativeOps& sock)
        : TcpCongestionOps(sock),
          m_started(false),
          m_tcb(nullptr),
          m_flowStartTime(Seconds(0)),
          m_ackCount(0),
          m_rttSampleCount(0),
          m_rttSum(Seconds(0)),
          m_bytesAckedInterval(0),
          m_lostSegmentsInterval(0),
          m_pendingAction(50)
    {
    }

    ~TcpDqnNativeOps() override = default;

    std::string GetName() const override { return "TcpDqn"; }

    Ptr<TcpCongestionOps> Fork() override
    {
        return CopyObject<TcpDqnNativeOps>(this);
    }

    uint32_t GetSsThresh(Ptr<const TcpSocketState> tcb, uint32_t bytesInFlight) override
    {
        (void)bytesInFlight;
        return std::max(static_cast<uint32_t>(tcb->m_ssThresh), static_cast<uint32_t>(tcb->m_cWnd.Get()));
    }

    void IncreaseWindow(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked) override
    {
        (void)segmentsAcked;
        InitIfNeeded(tcb);
        int32_t delta = static_cast<int32_t>(m_pendingAction) - 50;
        int64_t deltaBytes = static_cast<int64_t>(delta) * tcb->m_segmentSize;
        int64_t newCwnd = static_cast<int64_t>(tcb->m_cWnd.Get()) + deltaBytes;
        int64_t minCwnd = static_cast<int64_t>(tcb->m_segmentSize);
        tcb->m_cWnd = static_cast<uint32_t>(std::max(minCwnd, newCwnd));
    }

    void PktsAcked(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked, const Time& rtt) override
    {
        InitIfNeeded(tcb);
        m_ackCount += segmentsAcked;
        m_rttSampleCount++;
        m_rttSum += rtt;
        m_bytesAckedInterval += static_cast<uint64_t>(segmentsAcked) * tcb->m_segmentSize;
    }

    void CongestionStateSet(Ptr<TcpSocketState> tcb, TcpSocketState::TcpCongState_t newState) override
    {
        InitIfNeeded(tcb);
        if (newState == TcpSocketState::CA_LOSS || newState == TcpSocketState::CA_RECOVERY)
        {
            m_lostSegmentsInterval++;
        }
    }

private:
    void InitIfNeeded(Ptr<TcpSocketState> tcb)
    {
        if (!m_started)
        {
            m_started = true;
            m_tcb = tcb;
            m_flowStartTime = Simulator::Now();
            Simulator::Schedule(Seconds(0.1), &TcpDqnNativeOps::StepInterval, this);
        }
    }

    void StepInterval()
    {
        if (!m_tcb) return;

        const double relTime = (Simulator::Now() - m_flowStartTime).GetSeconds();
        const uint32_t segmentSize = m_tcb->m_segmentSize ? m_tcb->m_segmentSize : 1460;
        const uint32_t cwndBytes = static_cast<uint32_t>(m_tcb->m_cWnd.Get());
        const uint32_t cwndSegments = std::max(1u, cwndBytes / segmentSize);
        const uint32_t bytesInFlight = static_cast<uint32_t>(m_tcb->m_bytesInFlight.Get());

        double avgRttMs = 0.0;
        if (m_rttSampleCount > 0)
        {
            avgRttMs = m_rttSum.GetSeconds() * 1000.0 / static_cast<double>(m_rttSampleCount);
        }

        const double throughput = m_bytesAckedInterval / 0.1;

        float obs[TcpDqnModel::OBS_DIM];
        obs[0] = static_cast<float>(relTime);
        obs[1] = static_cast<float>(cwndSegments);
        obs[2] = static_cast<float>(bytesInFlight);
        obs[3] = static_cast<float>(m_ackCount);
        obs[4] = static_cast<float>(avgRttMs);
        obs[5] = static_cast<float>(throughput);
        obs[6] = static_cast<float>(m_lostSegmentsInterval);

        m_pendingAction = TcpDqnModel::PredictAction(obs, static_cast<float>(gAlpha));

        m_ackCount = 0;
        m_rttSampleCount = 0;
        m_rttSum = Seconds(0);
        m_bytesAckedInterval = 0;
        m_lostSegmentsInterval = 0;

        Simulator::Schedule(Seconds(0.1), &TcpDqnNativeOps::StepInterval, this);
    }

    bool m_started{false};
    Ptr<TcpSocketState> m_tcb{nullptr};
    Time m_flowStartTime{Seconds(0)};
    uint32_t m_ackCount{0};
    uint32_t m_rttSampleCount{0};
    Time m_rttSum{Seconds(0)};
    uint64_t m_bytesAckedInterval{0};
    uint64_t m_lostSegmentsInterval{0};
    uint32_t m_pendingAction{50};
};

NS_OBJECT_ENSURE_REGISTERED(TcpDqnNativeOps);

} // namespace ns3

static TypeId
GetTransportTypeId(const std::string& name)
{
    if (name == "NewReno")
    {
        return TcpNewReno::GetTypeId();
    }
    if (name == "Cubic")
    {
        return TcpCubic::GetTypeId();
    }
    if (name == "HighSpeed")
    {
        return TcpHighSpeed::GetTypeId();
    }
    if (name == "BBR" || name == "Bbr")
    {
        return TcpBbr::GetTypeId();
    }
    if (name == "TcpDqn" || name == "TCP-DQN" || name == "TCP_DQN" || name == "DQN" || name == "dqn")
    {
        return TcpDqnNativeOps::GetTypeId();
    }
    NS_FATAL_ERROR("Unknown transport_prot: " << name);
    return TcpNewReno::GetTypeId();
}

int
main(int argc, char* argv[])
{
    uint32_t nSenders = 4;
    double bottleneckMbps = 15.0;
    double bottleneckDelayMs = 25.0;
    double accessMbps = 100.0;
    double accessDelayMs = 2.0;
    uint32_t queuePackets = 40;
    double simTimeS = 20.0;
    uint32_t segmentSize = 1460;
    double lossRate = 0.0001;
    uint32_t seed = 42;
    std::string transportProt = "NewReno";
    std::string traceDir = "results/traces";
    std::string tracePrefix = "";
    bool staggeredStarts = true;

    CommandLine cmd;
    cmd.AddValue("nSenders", "Number of sender-receiver pairs", nSenders);
    cmd.AddValue("bottleneckMbps", "Bottleneck bandwidth in Mbps", bottleneckMbps);
    cmd.AddValue("bottleneckDelayMs", "Bottleneck one-way delay in ms", bottleneckDelayMs);
    cmd.AddValue("accessMbps", "Access links bandwidth in Mbps", accessMbps);
    cmd.AddValue("accessDelayMs", "Access links delay in ms", accessDelayMs);
    cmd.AddValue("queuePackets", "Bottleneck queue capacity in packets", queuePackets);
    cmd.AddValue("simTimeS", "Simulation duration in seconds", simTimeS);
    cmd.AddValue("segmentSize", "TCP MSS in bytes", segmentSize);
    cmd.AddValue("lossRate", "Random packet error rate on bottleneck", lossRate);
    cmd.AddValue("seed", "RNG seed", seed);
    cmd.AddValue("alpha", "Reward alpha parameter (0.0 to 1.0)", gAlpha);
    cmd.AddValue("transport_prot", "TCP variant: NewReno|Cubic|HighSpeed|BBR|TcpDqn", transportProt);
    cmd.AddValue("traceDir", "Output directory for CSV traces", traceDir);
    cmd.AddValue("tracePrefix", "Optional custom prefix for CSV trace files", tracePrefix);
    cmd.AddValue("staggeredStarts", "Whether flows start staggered", staggeredStarts);
    cmd.Parse(argc, argv);

    gSegmentSize = segmentSize;
    gFlowTraces.resize(nSenders);
    for (uint32_t i = 0; i < nSenders; ++i)
    {
        gFlowTraces[i].flowId = i;
    }

    SeedManager::SetSeed(seed);
    Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(GetTransportTypeId(transportProt)));
    Config::SetDefault("ns3::TcpSocket::SegmentSize", UintegerValue(segmentSize));

    // Nodes creation
    NodeContainer senders;
    senders.Create(nSenders);

    NodeContainer receivers;
    receivers.Create(nSenders);

    NodeContainer routers;
    routers.Create(2); // Router 0 (left), Router 1 (right)
    Ptr<Node> r0 = routers.Get(0);
    Ptr<Node> r1 = routers.Get(1);

    InternetStackHelper internet;
    internet.Install(senders);
    internet.Install(receivers);
    internet.Install(routers);

    // Bottleneck link R0 <-> R1
    PointToPointHelper p2pBottleneck;
    p2pBottleneck.SetDeviceAttribute("DataRate", StringValue(std::to_string(bottleneckMbps) + "Mbps"));
    p2pBottleneck.SetChannelAttribute("Delay", StringValue(std::to_string(bottleneckDelayMs) + "ms"));

    Ptr<RateErrorModel> em = CreateObject<RateErrorModel>();
    em->SetAttribute("ErrorRate", DoubleValue(lossRate));
    em->SetAttribute("ErrorUnit", StringValue("ERROR_UNIT_PACKET"));

    NetDeviceContainer bottleneckDevices = p2pBottleneck.Install(r0, r1);
    bottleneckDevices.Get(1)->SetAttribute("ReceiveErrorModel", PointerValue(em));

    // Bottleneck queue disc
    TrafficControlHelper tchBottleneck;
    tchBottleneck.SetRootQueueDisc("ns3::FifoQueueDisc",
                                   "MaxSize",
                                   QueueSizeValue(QueueSize(QueueSizeUnit::PACKETS, queuePackets)));
    QueueDiscContainer qDiscs = tchBottleneck.Install(bottleneckDevices);
    Ptr<QueueDisc> r0QueueDisc = qDiscs.Get(0); // Queue on R0 -> R1
    r0QueueDisc->TraceConnectWithoutContext("Drop", MakeCallback(&OnQueueDrop));
    r0QueueDisc->TraceConnectWithoutContext("PacketsInQueue", MakeCallback(&OnQueuePackets));

    Ipv4AddressHelper ipv4;
    ipv4.SetBase("10.0.1.0", "255.255.255.0");
    Ipv4InterfaceContainer bottleneckIfaces = ipv4.Assign(bottleneckDevices);

    // Access links S_i <-> R0 and R1 <-> D_i
    PointToPointHelper p2pAccess;
    p2pAccess.SetDeviceAttribute("DataRate", StringValue(std::to_string(accessMbps) + "Mbps"));
    p2pAccess.SetChannelAttribute("Delay", StringValue(std::to_string(accessDelayMs) + "ms"));

    TrafficControlHelper tchAccess;
    tchAccess.SetRootQueueDisc("ns3::FifoQueueDisc",
                              "MaxSize",
                              QueueSizeValue(QueueSize(QueueSizeUnit::PACKETS, 1000)));

    std::vector<Ipv4Address> receiverIpv4s(nSenders);

    for (uint32_t i = 0; i < nSenders; ++i)
    {
        // Sender i to R0
        NetDeviceContainer sDevice = p2pAccess.Install(senders.Get(i), r0);
        tchAccess.Install(sDevice);
        std::ostringstream sSubnet;
        sSubnet << "10.1." << (i + 1) << ".0";
        ipv4.SetBase(sSubnet.str().c_str(), "255.255.255.0");
        ipv4.Assign(sDevice);

        // R1 to Receiver i
        NetDeviceContainer rDevice = p2pAccess.Install(r1, receivers.Get(i));
        tchAccess.Install(rDevice);
        std::ostringstream rSubnet;
        rSubnet << "10.2." << (i + 1) << ".0";
        ipv4.SetBase(rSubnet.str().c_str(), "255.255.255.0");
        Ipv4InterfaceContainer rIfaces = ipv4.Assign(rDevice);
        receiverIpv4s[i] = rIfaces.GetAddress(1); // Receiver IP
    }

    Ipv4GlobalRoutingHelper::PopulateRoutingTables();

    // Install Applications
    for (uint32_t i = 0; i < nSenders; ++i)
    {
        const uint16_t port = 50000 + i;
        PacketSinkHelper sink("ns3::TcpSocketFactory",
                              InetSocketAddress(Ipv4Address::GetAny(), port));
        ApplicationContainer sinkApp = sink.Install(receivers.Get(i));
        sinkApp.Start(Seconds(0.0));
        sinkApp.Stop(Seconds(simTimeS));

        BulkSendHelper source("ns3::TcpSocketFactory",
                              InetSocketAddress(receiverIpv4s[i], port));
        source.SetAttribute("MaxBytes", UintegerValue(0));
        source.SetAttribute("SendSize", UintegerValue(segmentSize));
        ApplicationContainer client = source.Install(senders.Get(i));

        double start = staggeredStarts ? (0.2 + i * 2.0) : 0.2;
        client.Start(Seconds(start));
        client.Stop(Seconds(simTimeS));

        // Connect trace hooks for flow i after its start time
        Simulator::Schedule(Seconds(start + 0.05), [=]() {
            Ptr<Node> node = senders.Get(i);
            Ptr<TcpL4Protocol> tcp = node->GetObject<TcpL4Protocol>();
            ObjectVectorValue socketVec;
            tcp->GetAttribute("SocketList", socketVec);
            if (socketVec.GetN() > 0)
            {
                Ptr<TcpSocketBase> sock = DynamicCast<TcpSocketBase>(socketVec.Get(0));
                if (sock)
                {
                    sock->TraceConnectWithoutContext("CongestionWindow",
                                                     MakeBoundCallback(&OnFlowCwnd, i));
                    sock->TraceConnectWithoutContext("RTT",
                                                     MakeBoundCallback(&OnFlowRtt, i));
                    sock->TraceConnectWithoutContext("Tx",
                                                     MakeBoundCallback(&OnFlowTx, i));
                    sock->TraceConnectWithoutContext("CongState",
                                                     MakeBoundCallback(&OnFlowCongState, i));
                }
            }
        });
    }

    // Open CSV trace files
    std::ostringstream flowsPath;
    if (!tracePrefix.empty())
    {
        flowsPath << traceDir << "/" << tracePrefix << "_flows.csv";
    }
    else
    {
        flowsPath << traceDir << "/multinode_flows_" << transportProt << "_n" << nSenders << ".csv";
    }
    gFlowsCsv.open(flowsPath.str());
    gFlowsCsv << "time_s,flow_id,cwnd_segments,rtt_ms,throughput_Bps,cumulative_lost_segments\n";

    std::ostringstream queuePath;
    if (!tracePrefix.empty())
    {
        queuePath << traceDir << "/" << tracePrefix << "_queue.csv";
    }
    else
    {
        queuePath << traceDir << "/multinode_queue_" << transportProt << "_n" << nSenders << ".csv";
    }
    gQueueCsv.open(queuePath.str());
    gQueueCsv << "time_s,packets_in_queue,cumulative_drops\n";

    Simulator::Schedule(Seconds(0.2), &PeriodicSample);

    std::cout << "Starting multi-node congestion simulation: " << nSenders
              << " flows, " << bottleneckMbps << " Mbps bottleneck, algorithm: "
              << transportProt << "...\n";

    Simulator::Stop(Seconds(simTimeS));
    Simulator::Run();

    if (gFlowsCsv.is_open())
    {
        gFlowsCsv.close();
    }
    if (gQueueCsv.is_open())
    {
        gQueueCsv.close();
    }

    std::cout << "Multi-node simulation completed. Total bottleneck queue drops: "
              << gBottleneckDrops << "\n";

    Simulator::Destroy();
    return 0;
}
