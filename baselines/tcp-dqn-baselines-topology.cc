#include "../helper/tcp-dqn-topology-helper.h"

#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/tcp-highspeed.h"
#include "ns3/tcp-socket-base.h"

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("TcpDqnBaselinesTopology");

static TcpDqnTraceState gTrace;
static std::ofstream gCsv;
static double gSampleIntervalS = 0.1;
static uint32_t gSegmentSize = 1460;

static void
OnCongestionWindow(uint32_t oldCwnd, uint32_t newCwnd)
{
    (void)oldCwnd;
    gTrace.lastCwndSegments = std::max(1u, newCwnd / gSegmentSize);
}

static void
OnRttChange(Time oldRtt, Time newRtt)
{
    (void)oldRtt;
    gTrace.lastRttMs = newRtt.GetSeconds() * 1000.0;
}

static void
OnTx(Ptr<const Packet> packet, const TcpHeader& header, Ptr<const TcpSocketBase> sock)
{
    (void)sock;
    (void)header;
    gTrace.bytesAckedSinceLast += packet->GetSize();
}

static void
OnCongState(TcpSocketState::TcpCongState_t oldState, TcpSocketState::TcpCongState_t newState)
{
    (void)oldState;
    if (newState == TcpSocketState::CA_LOSS || newState == TcpSocketState::CA_RECOVERY)
    {
        gTrace.cumulativeLostSegments++;
    }
}

static void
PeriodicSample()
{
    if (gCsv.is_open())
    {
        SampleTraceRow(gCsv, Simulator::Now().GetSeconds(), gTrace, gSampleIntervalS);
    }
    gTrace.bytesAckedSinceLast = 0;
    Simulator::Schedule(Seconds(gSampleIntervalS), &PeriodicSample);
}

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
    NS_FATAL_ERROR("Unknown transport_prot: " << name);
    return TcpNewReno::GetTypeId();
}

int
main(int argc, char* argv[])
{
    TcpDqnLinkConfig cfg;
    std::string transportProt = "NewReno";
    std::string traceDir = "results/traces";

    CommandLine cmd;
    cmd.AddValue("bandwidthMbps", "Bottleneck bandwidth in Mbps", cfg.bandwidthMbps);
    cmd.AddValue("baseRttMs", "Base RTT in ms (one-way delay is half)", cfg.baseRttMs);
    cmd.AddValue("lossRate", "Packet loss rate", cfg.lossRate);
    cmd.AddValue("queuePackets", "Bottleneck queue size in packets (0=auto BDP)", cfg.queuePackets);
    cmd.AddValue("segmentSize", "TCP segment size in bytes", cfg.segmentSize);
    cmd.AddValue("simTimeS", "Simulation duration in seconds", cfg.simTimeS);
    cmd.AddValue("seed", "RNG seed", cfg.seed);
    cmd.AddValue("transport_prot", "TCP variant: NewReno|Cubic|HighSpeed", transportProt);
    cmd.AddValue("traceDir", "Directory for CSV traces", traceDir);
    cmd.Parse(argc, argv);

    if (cfg.queuePackets == 0)
    {
        cfg.queuePackets = ComputeDefaultQueuePackets(cfg.bandwidthMbps, cfg.baseRttMs, cfg.segmentSize);
    }

    gSampleIntervalS = cfg.sampleIntervalS;
    gSegmentSize = cfg.segmentSize;

    SeedManager::SetSeed(cfg.seed);

    Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(GetTransportTypeId(transportProt)));

    NodeContainer sender;
    NodeContainer receiver;
    Ptr<RateErrorModel> errorModel;
    NetDeviceContainer devices = BuildTcpDqnTopology(sender, receiver, cfg, errorModel);

    InternetStackHelper stack;
    stack.Install(sender);
    stack.Install(receiver);
    InstallTcpDqnQueueDisc(devices, cfg);

    Ipv4AddressHelper address("10.1.1.0", "255.255.255.0");
    Ipv4InterfaceContainer interfaces = address.Assign(devices);
    const Ipv4Address receiverAddr = interfaces.GetAddress(1);

    const double startTime = 0.1;
    const double stopTime = startTime + cfg.simTimeS;
    InstallTcpDqnApps(sender, receiver, receiverAddr, cfg, startTime, stopTime);

    Simulator::Schedule(Seconds(startTime + 0.01), [=]() {
        Ptr<Node> node = sender.Get(0);
        Ptr<TcpL4Protocol> tcp = node->GetObject<TcpL4Protocol>();
        ObjectVectorValue socketVec;
        tcp->GetAttribute("SocketList", socketVec);
        if (socketVec.GetN() > 0)
        {
            Ptr<TcpSocketBase> sock = DynamicCast<TcpSocketBase>(socketVec.Get(0));
            if (sock)
            {
                sock->TraceConnectWithoutContext("CongestionWindow", MakeCallback(&OnCongestionWindow));
                sock->TraceConnectWithoutContext("RTT", MakeCallback(&OnRttChange));
                sock->TraceConnectWithoutContext("Tx", MakeCallback(&OnTx));
                sock->TraceConnectWithoutContext("CongState", MakeCallback(&OnCongState));
            }
        }
    });

    std::ostringstream tracePath;
    tracePath << traceDir << "/" << transportProt << "_" << cfg.seed << ".csv";
    gCsv.open(tracePath.str());
    gCsv << "time_s,cwnd_segments,rtt_ms,throughput_Bps_since_last_sample,cumulative_lost_segments\n";

    Simulator::Schedule(Seconds(startTime + cfg.sampleIntervalS), &PeriodicSample);
    Simulator::Stop(Seconds(stopTime));
    Simulator::Run();

    if (gCsv.is_open())
    {
        gCsv.close();
    }

    Simulator::Destroy();
    return 0;
}
