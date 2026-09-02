#include "../model/tcp-dqn-env.h"

#include "ns3/test.h"

using namespace ns3;

class TcpDqnTestSuite : public TestSuite
{
  public:
    TcpDqnTestSuite();
};

class TcpDqnActionMappingTest : public TestCase
{
  public:
    TcpDqnActionMappingTest();
    void DoRun() override;
};

class TcpDqnRewardTest : public TestCase
{
  public:
    TcpDqnRewardTest();
    void DoRun() override;
};

TcpDqnActionMappingTest::TcpDqnActionMappingTest()
    : TestCase("TCP-DQN action index to cwnd delta mapping")
{
}

void
TcpDqnActionMappingTest::DoRun()
{
    NS_TEST_ASSERT_MSG_EQ(TcpDqnEnv::ActionIndexToDeltaSegments(0), -50, "index 0 -> -50 segments");
    NS_TEST_ASSERT_MSG_EQ(TcpDqnEnv::ActionIndexToDeltaSegments(50), 0, "index 50 -> 0 segments");
    NS_TEST_ASSERT_MSG_EQ(TcpDqnEnv::ActionIndexToDeltaSegments(100), 50, "index 100 -> +50 segments");

    const uint32_t seg = 1460;
    NS_TEST_ASSERT_MSG_EQ(TcpDqnEnv::ApplyCwndDelta(seg, -50, seg),
                          static_cast<uint32_t>(seg),
                          "cwnd cannot drop below one segment");
    NS_TEST_ASSERT_MSG_EQ(TcpDqnEnv::ApplyCwndDelta(10 * seg, 50, seg),
                          static_cast<uint32_t>(60 * seg),
                          "cwnd increases by 50 segments");
}

TcpDqnRewardTest::TcpDqnRewardTest()
    : TestCase("TCP-DQN reward parity with Python fixtures")
{
}

void
TcpDqnRewardTest::DoRun()
{
    // divide-by-zero guard on first interval
    NS_TEST_ASSERT_MSG_EQ(TcpDqnEnv::ComputeReward(100.0, 0.0, 50.0, 40.0, 60.0, 0.5),
                          0.0f,
                          "zero range returns 0");

    const float r1 = TcpDqnEnv::ComputeReward(800.0, 1000.0, 55.0, 50.0, 60.0, 0.5);
    const float r2 = TcpDqnEnv::ComputeReward(900.0, 1000.0, 52.0, 50.0, 60.0, 0.5);
    NS_TEST_ASSERT_MSG_GT(r2, r1, "higher throughput should not decrease reward");

    const float alpha1 = TcpDqnEnv::ComputeReward(1000.0, 1000.0, 55.0, 50.0, 60.0, 1.0);
    NS_TEST_ASSERT_MSG_GT(alpha1, 0.9f, "alpha=1 emphasizes throughput");

    const float alpha0 = TcpDqnEnv::ComputeReward(500.0, 1000.0, 60.0, 50.0, 60.0, 0.0);
    NS_TEST_ASSERT_MSG_LT(alpha0, 0.01f, "alpha=0 emphasizes RTT penalty at max RTT");
}

TcpDqnTestSuite::TcpDqnTestSuite()
    : TestSuite("tcp-dqn", UNIT)
{
    AddTestCase(new TcpDqnActionMappingTest, TestCase::QUICK);
    AddTestCase(new TcpDqnRewardTest, TestCase::QUICK);
}

static TcpDqnTestSuite g_tcpDqnTestSuite;
