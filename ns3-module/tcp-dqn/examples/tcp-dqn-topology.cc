#include "../helper/tcp-dqn-helper.h"
#include "../helper/tcp-dqn-topology-helper.h"

#include "ns3/ai-module.h"
#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/tcp-socket-base.h"

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("TcpDqnTopology");

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
PeriodicSample(std::string algoName, uint32_t seed)
{
    static double lastSampleTime = 0.0;
    const double now = Simulator::Now().GetSeconds();
    if (gCsv.is_open())
    {
        SampleTraceRow(gCsv, now, gTrace, gSampleIntervalS);
    }
    gTrace.bytesAckedSinceLast = 0;
    lastSampleTime = now;
    (void)lastSampleTime;
    Simulator::Schedule(Seconds(gSampleIntervalS), &PeriodicSample, algoName, seed);
}

int
main(int argc, char* argv[])
{
    TcpDqnLinkConfig cfg;
    std::string traceDir = "results/traces";
    double alpha = 0.5;
    uint32_t simSeed = 0;

    CommandLine cmd;
    cmd.AddValue("bandwidthMbps", "Bottleneck bandwidth in Mbps", cfg.bandwidthMbps);
    cmd.AddValue("baseRttMs", "Base RTT in ms (one-way delay is half)", cfg.baseRttMs);
    cmd.AddValue("lossRate", "Packet loss rate", cfg.lossRate);
    cmd.AddValue("queuePackets", "Bottleneck queue size in packets (0=auto BDP)", cfg.queuePackets);
    cmd.AddValue("segmentSize", "TCP segment size in bytes", cfg.segmentSize);
    cmd.AddValue("simTimeS", "Simulation duration in seconds", cfg.simTimeS);
    cmd.AddValue("seed", "RNG seed", cfg.seed);
    cmd.AddValue("alpha", "Reward alpha (Eq. 6)", alpha);
    cmd.AddValue("traceDir", "Directory for CSV traces", traceDir);
    cmd.AddValue("simSeed", "ns-3 run number", simSeed);
    cmd.Parse(argc, argv);

    if (cfg.queuePackets == 0)
    {
        cfg.queuePackets = ComputeDefaultQueuePackets(cfg.bandwidthMbps, cfg.baseRttMs, cfg.segmentSize);
    }

    gSampleIntervalS = cfg.sampleIntervalS;
    gSegmentSize = cfg.segmentSize;

    SeedManager::SetSeed(cfg.seed);
    SeedManager::SetRun(simSeed);

    TcpDqnHelper::SetAlpha(alpha);
    TcpDqnHelper::SetStepTime(cfg.sampleIntervalS);
    TcpDqnHelper::Install();

    Ptr<OpenGymInterface> openGymInterface = OpenGymInterface::Get();

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

    // Trace hooks on sender socket after apps start
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
    tracePath << traceDir << "/tcp_dqn_" << cfg.seed << ".csv";
    gCsv.open(tracePath.str());
    gCsv << "time_s,cwnd_segments,rtt_ms,throughput_Bps_since_last_sample,cumulative_lost_segments\n";

    Simulator::Schedule(Seconds(startTime + cfg.sampleIntervalS),
                        &PeriodicSample,
                        std::string("tcp_dqn"),
                        cfg.seed);

    Simulator::Stop(Seconds(stopTime));
    Simulator::Run();

    if (gCsv.is_open())
    {
        gCsv.close();
    }

    openGymInterface->NotifySimulationEnd();
    Simulator::Destroy();
    return 0;
}
