#include <gtest/gtest.h>
#include <rcl/time.h>
#include <thread>
#include "../src/peer_robot_layer.cpp"

// Actual native layer and ROS callback, with no actuator/world or motion grants.
class PeerLayerTest : public ::testing::Test
{
protected:
  void SetUp() override
  {
    if (!rclcpp::ok()) rclcpp::init(0, nullptr);
    executor = std::make_unique<rclcpp::executors::SingleThreadedExecutor>();
    rclcpp::NodeOptions options;
    options.arguments({"--ros-args", "-r", "/tf:=tf", "-r", "__ns:=/alpha/global_costmap"});
    options.parameter_overrides({
      rclcpp::Parameter("peer.robot_ids", std::vector<std::string>{"alpha", "beta", "gamma"}),
      rclcpp::Parameter("peer.tf_topics", std::vector<std::string>{"/alpha/tf", "/beta/tf", "/gamma/tf"}),
      rclcpp::Parameter("peer.radii", std::vector<double>{.3, .4, .25}),
      rclcpp::Parameter("peer.self_id", "alpha"), rclcpp::Parameter("peer.map_frame", "map"),
      rclcpp::Parameter("peer.pose_age_sec", .8), rclcpp::Parameter("peer.transport_sec", .3),
      rclcpp::Parameter("peer.localization_age_sec", .8),
      rclcpp::Parameter("peer.future_tolerance_sec", 1.),
    });
    node = std::make_shared<nav2_util::LifecycleNode>("peer_test", "", options);
    ASSERT_EQ(rcl_enable_ros_time_override(node->get_clock()->get_clock_handle()), RCL_RET_OK);
    setClock(1'000'000'000);
    map = std::make_unique<nav2_costmap_2d::LayeredCostmap>(grid_frame, false, false);
    map->resizeMap(100, 100, .1, -5., -5.);
    layer = std::make_shared<fleet_perception::PeerRobotLayer>();
    group = node->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive, false);
    executor->add_callback_group(group, node->get_node_base_interface());
    layer->initialize(map.get(), "peer", nullptr, node, group);
    map->addPlugin(layer);
    writer = node->create_publisher<tf2_msgs::msg::TFMessage>("/alpha/tf", 100);
    writer->on_activate();
    for (auto topic : {"/beta/tf", "/gamma/tf"}) {
      auto publisher = node->create_publisher<tf2_msgs::msg::TFMessage>(topic, 100);
      publisher->on_activate(); other_writers.push_back(publisher);
    }
    const auto end = std::chrono::steady_clock::now() + std::chrono::seconds(2);
    while (writer->get_subscription_count() == 0 && std::chrono::steady_clock::now() < end) pump();
    ASSERT_GT(writer->get_subscription_count(), 0u);
  }
  void TearDown() override
  {
    if (group) executor->remove_callback_group(group);
    writer.reset(); other_writers.clear(); layer.reset(); map.reset(); group.reset(); node.reset();
    executor.reset();
  }
  void pump()
  {
    executor->spin_some();
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  }
  void setClock(int64_t value)
  {
    now = value;
    ASSERT_EQ(rcl_set_ros_time_override(node->get_clock()->get_clock_handle(), now), RCL_RET_OK);
  }
  geometry_msgs::msg::TransformStamped edge(std::string parent, std::string child,
    int64_t stamp, double x = 0., double y = 0.)
  {
    geometry_msgs::msg::TransformStamped t;
    t.header.frame_id = parent; t.child_frame_id = child;
    t.header.stamp = rclcpp::Time(stamp);
    t.transform.translation.x = x; t.transform.translation.y = y;
    t.transform.rotation.w = 1.;
    return t;
  }
  void send(tf2_msgs::msg::TFMessage packet)
  {
    writer->publish(packet);
    for (auto & publisher : other_writers) publisher->publish(packet);
    for (int i = 0; i < 6; ++i) pump();
    map->updateMap(0., 0., 0.);
  }
  void fresh(double bx = 2., double by = 0.)
  {
    tf2_msgs::msg::TFMessage packet;
    for (auto id : {"alpha", "beta", "gamma"}) {
      packet.transforms.push_back(edge("map", std::string(id) + "/odom", now));
      packet.transforms.push_back(edge(std::string(id) + "/odom", std::string(id) + "/base_link", now,
        std::string(id) == "beta" ? bx : (std::string(id) == "gamma" ? -2. : 0.),
        std::string(id) == "beta" ? by : 0.));
    }
    send(packet);
  }
  unsigned char cost(double x, double y)
  {
    unsigned int col, row;
    EXPECT_TRUE(map->getCostmap()->worldToMap(x, y, col, row));
    return map->getCostmap()->getCost(col, row);
  }
  int64_t now;
  std::string grid_frame{"map"};
  nav2_util::LifecycleNode::SharedPtr node;
  std::unique_ptr<nav2_costmap_2d::LayeredCostmap> map;
  std::shared_ptr<fleet_perception::PeerRobotLayer> layer;
  rclcpp_lifecycle::LifecyclePublisher<tf2_msgs::msg::TFMessage>::SharedPtr writer;
  std::vector<rclcpp_lifecycle::LifecyclePublisher<tf2_msgs::msg::TFMessage>::SharedPtr> other_writers;
  rclcpp::CallbackGroup::SharedPtr group;
  std::unique_ptr<rclcpp::executors::SingleThreadedExecutor> executor;
};

TEST_F(PeerLayerTest, MarksBothPeersAndExcludesSelf)
{
  fresh();
  ASSERT_TRUE(layer->isCurrent());
  EXPECT_EQ(cost(2., 0.), nav2_costmap_2d::LETHAL_OBSTACLE);
  EXPECT_EQ(cost(-2., 0.), nav2_costmap_2d::LETHAL_OBSTACLE);
  EXPECT_NE(cost(0., 0.), nav2_costmap_2d::LETHAL_OBSTACLE);
  EXPECT_EQ(cost(2.39, .01), nav2_costmap_2d::LETHAL_OBSTACLE);
  EXPECT_NE(cost(2.55, .01), nav2_costmap_2d::LETHAL_OBSTACLE);
}

TEST_F(PeerLayerTest, MovingPeerClearsOldBounds)
{
  fresh(); setClock(now + 100'000'000); fresh(2., 2.);
  ASSERT_TRUE(layer->isCurrent());
  EXPECT_NE(cost(2., 0.), nav2_costmap_2d::LETHAL_OBSTACLE);
  EXPECT_EQ(cost(2., 2.), nav2_costmap_2d::LETHAL_OBSTACLE);
}

TEST_F(PeerLayerTest, StaleReceiptAndDuplicateDoNotCertifyFreshnessOrClearOccupancy)
{
  fresh(); ASSERT_TRUE(layer->isCurrent());
  std::this_thread::sleep_for(std::chrono::milliseconds(310));
  fresh();  // Same advancing-source stamp is deliberately rejected.
  EXPECT_FALSE(layer->isCurrent());
  EXPECT_EQ(cost(2., 0.), nav2_costmap_2d::LETHAL_OBSTACLE);
  layer->reset(); EXPECT_FALSE(layer->isClearable());
  map->updateMap(0., 0., 0.);
  EXPECT_EQ(cost(2., 0.), nav2_costmap_2d::LETHAL_OBSTACLE);
}

TEST_F(PeerLayerTest, SourceAgeAndWrongParentCannotPass)
{
  fresh(); setClock(now + 900'000'000); map->updateMap(0., 0., 0.);
  EXPECT_FALSE(layer->isCurrent());
  fresh(); ASSERT_TRUE(layer->isCurrent());
  tf2_msgs::msg::TFMessage packet;
  packet.transforms.push_back(edge("wrong", "beta/base_link", now + 1)); send(packet);
  EXPECT_FALSE(layer->isCurrent());
  EXPECT_EQ(cost(2., 0.), nav2_costmap_2d::LETHAL_OBSTACLE);
}

TEST_F(PeerLayerTest, FutureAndReorderedMeasurementsCannotMovePeer)
{
  fresh();
  tf2_msgs::msg::TFMessage packet;
  packet.transforms.push_back(edge("beta/odom", "beta/base_link", now - 1, 4.));
  packet.transforms.push_back(edge("beta/odom", "beta/base_link", now + 500'000'000, 4.));
  send(packet);
  EXPECT_EQ(cost(2., 0.), nav2_costmap_2d::LETHAL_OBSTACLE);
  EXPECT_NE(cost(4., 0.), nav2_costmap_2d::LETHAL_OBSTACLE);
}

TEST_F(PeerLayerTest, RewindInvalidatesAllHistoryAndHoldsLastOccupancy)
{
  fresh(); setClock(now - 500'000'000); map->updateMap(0., 0., 0.);
  EXPECT_FALSE(layer->isCurrent());
  EXPECT_EQ(cost(2., 0.), nav2_costmap_2d::LETHAL_OBSTACLE);
  fresh(2., 2.); EXPECT_TRUE(layer->isCurrent());
  EXPECT_NE(cost(2., 0.), nav2_costmap_2d::LETHAL_OBSTACLE);
}

TEST_F(PeerLayerTest, MissingChainAndInvalidQuaternionStayUncurrent)
{
  fresh();
  tf2_msgs::msg::TFMessage packet;
  auto t = edge("beta/odom", "beta/base_link", now + 1, 4.);
  t.transform.rotation.w = 0.; packet.transforms.push_back(t); send(packet);
  EXPECT_FALSE(layer->isCurrent());
  EXPECT_EQ(cost(2., 0.), nav2_costmap_2d::LETHAL_OBSTACLE);
}

TEST_F(PeerLayerTest, MissingExactTimeHistoryDoesNotUseLatestTransform)
{
  tf2_msgs::msg::TFMessage packet;
  for (auto id : {"alpha", "beta", "gamma"}) {
    packet.transforms.push_back(edge("map", std::string(id) + "/odom", now + 500'000'000));
    packet.transforms.push_back(edge(std::string(id) + "/odom", std::string(id) + "/base_link", now, 2.));
  }
  send(packet);
  EXPECT_FALSE(layer->isCurrent());
  EXPECT_NE(cost(2., 0.), nav2_costmap_2d::LETHAL_OBSTACLE);
}

TEST_F(PeerLayerTest, ClipsPartialDiscAndNeverClearsAnotherLayer)
{
  fresh(-5.2, 0.);
  ASSERT_TRUE(layer->isCurrent());
  EXPECT_EQ(cost(-4.95, 0.), nav2_costmap_2d::LETHAL_OBSTACLE);
  auto grid = map->getCostmap();
  grid->setCost(50, 50, nav2_costmap_2d::LETHAL_OBSTACLE);
  layer->updateCosts(*grid, 0, 0, 100, 100);
  EXPECT_EQ(grid->getCost(50, 50), nav2_costmap_2d::LETHAL_OBSTACLE);
}

class PeerLayerLocalTest : public PeerLayerTest
{
  void SetUp() override {grid_frame = "alpha/odom"; PeerLayerTest::SetUp();}
};

TEST_F(PeerLayerLocalTest, TransformsPeersThroughSharedMapIntoOwnOdometry)
{
  fresh(); setClock(now + 100'000'000);
  tf2_msgs::msg::TFMessage packet;
  for (auto id : {"alpha", "beta", "gamma"}) {
    packet.transforms.push_back(edge("map", std::string(id) + "/odom", now,
      std::string(id) == "alpha" ? 1. : 0., std::string(id) == "alpha" ? 1. : 0.));
    packet.transforms.push_back(edge(std::string(id) + "/odom", std::string(id) + "/base_link", now,
      std::string(id) == "beta" ? 2. : -2., 0.));
  }
  send(packet);
  ASSERT_TRUE(layer->isCurrent());
  EXPECT_EQ(cost(1., -1.), nav2_costmap_2d::LETHAL_OBSTACLE);
  EXPECT_NE(cost(2., 0.), nav2_costmap_2d::LETHAL_OBSTACLE);
}
