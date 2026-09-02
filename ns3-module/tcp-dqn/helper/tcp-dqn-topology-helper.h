#ifndef TCP_DQN_TOPOLOGY_HELPER_H
#define TCP_DQN_TOPOLOGY_HELPER_H

#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/error-model.h"
#include "ns3/internet-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/traffic-control-module.h"

#include <fstream>
#include <string>

namespace ns3
{

struct TcpDqnLinkConfig
{
    double bandwidthMbps{67.8};
    double baseRttMs{56.0};
    double lossRate{0.0001};
    uint32_t queuePackets{325};
    uint32_t segmentSize{1460};
    double simTimeS{600.0};
    uint32_t seed{42};
    double sampleIntervalS{0.1};
};

struct TcpDqnTraceState
{
    uint64_t cumulativeLostSegments{0};
    uint64_t lastCumulativeLost{0};
    uint64_t bytesAckedSinceLast{0};
    uint32_t lastCwndSegments{0};
    double lastRttMs{0.0};
};

inline uint32_t
ComputeDefaultQueuePackets(double bandwidthMbps, double baseRttMs, uint32_t segmentSize)
{
    const double bdpBytes = (bandwidthMbps * 1e6 / 8.0) * (baseRttMs / 1000.0);
    return static_cast<uint32_t>(std::max(10.0, bdpBytes / segmentSize));
}

inline NetDeviceContainer
BuildTcpDqnTopology(NodeContainer& sender,
                    NodeContainer& receiver,
                    const TcpDqnLinkConfig& cfg,
                    Ptr<RateErrorModel>& errorModel)
{
    sender.Create(1);
    receiver.Create(1);

    PointToPointHelper p2p;
    const std::string rate = std::to_string(cfg.bandwidthMbps) + "Mbps";
    const std::string delay = std::to_string(cfg.baseRttMs / 2.0) + "ms";
    p2p.SetDeviceAttribute("DataRate", StringValue(rate));
    p2p.SetChannelAttribute("Delay", StringValue(delay));

    Ptr<RateErrorModel> em = CreateObject<RateErrorModel>();
    em->SetAttribute("ErrorRate", DoubleValue(cfg.lossRate));
    em->SetAttribute("ErrorUnit", StringValue("ERROR_UNIT_PACKET"));
    errorModel = em;

    NetDeviceContainer devices = p2p.Install(sender.Get(0), receiver.Get(0));
    devices.Get(1)->SetAttribute("ReceiveErrorModel", PointerValue(em));

    return devices;
}

inline void
InstallTcpDqnQueueDisc(const NetDeviceContainer& devices, const TcpDqnLinkConfig& cfg)
{
    TrafficControlHelper tch;
    tch.SetRootQueueDisc("ns3::FifoQueueDisc");
    const uint32_t qPkts =
        cfg.queuePackets > 0 ? cfg.queuePackets : ComputeDefaultQueuePackets(cfg.bandwidthMbps,
                                                                             cfg.baseRttMs,
                                                                             cfg.segmentSize);
    Config::SetDefault("ns3::FifoQueueDisc::MaxSize",
                       QueueSizeValue(QueueSize(QueueSizeUnit::PACKETS, qPkts)));
    tch.Install(devices);
}

inline void
InstallTcpDqnApps(NodeContainer& sender,
                  NodeContainer& receiver,
                  Ipv4Address receiverAddr,
                  const TcpDqnLinkConfig& cfg,
                  double startTimeS,
                  double stopTimeS)
{
    const uint16_t port = 50000;
    PacketSinkHelper sink("ns3::TcpSocketFactory",
                          InetSocketAddress(Ipv4Address::GetAny(), port));
    ApplicationContainer sinkApp = sink.Install(receiver.Get(0));
    sinkApp.Start(Seconds(0.0));
    sinkApp.Stop(Seconds(stopTimeS));

    Config::SetDefault("ns3::TcpSocket::SegmentSize", UintegerValue(cfg.segmentSize));
    BulkSendHelper source("ns3::TcpSocketFactory",
                          InetSocketAddress(receiverAddr, port));
    source.SetAttribute("MaxBytes", UintegerValue(0));
    source.SetAttribute("SendSize", UintegerValue(cfg.segmentSize));
    ApplicationContainer client = source.Install(sender.Get(0));
    client.Start(Seconds(startTimeS));
    client.Stop(Seconds(stopTimeS));
}

inline void
SampleTraceRow(std::ofstream& csv,
               double timeS,
               const TcpDqnTraceState& state,
               double sampleIntervalS)
{
    const double throughput = state.bytesAckedSinceLast / sampleIntervalS;
    csv << timeS << "," << state.lastCwndSegments << "," << state.lastRttMs << ","
        << throughput << "," << state.cumulativeLostSegments << "\n";
}

} // namespace ns3

#endif // TCP_DQN_TOPOLOGY_HELPER_H
