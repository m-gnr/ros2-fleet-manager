#include <iostream>
#include <stdexcept>
#include <string>

#include "../src/clearance.hpp"

using namespace fleet_nav2_escape;

namespace
{
Grid grid()
{
  Grid result;
  result.header.frame_id = "map";
  result.metadata.resolution = 0.05;
  result.metadata.size_x = result.metadata.size_y = 60;
  result.metadata.origin.position.x = result.metadata.origin.position.y = -1.5;
  result.data.resize(60 * 60);
  for (size_t y = 0; y < 60; ++y) {
    for (size_t x = 0; x < 60; ++x) {
      result.data[y * 60 + x] = x <= 22 ? 254 : (x <= 31 ? 253 : 0);
    }
  }
  return result;
}

void require(bool result, const char * label)
{
  if (!result) {
    throw std::runtime_error(label);
  }
}
}  // namespace

int main()
{
  const rclcpp::Time now(5, 0, RCL_ROS_TIME);
  auto own = std::make_shared<Pose>();
  own->header.frame_id = "world";
  own->header.stamp = now;
  own->pose.orientation.w = 1.0;
  auto peer = std::make_shared<Pose>(*own);
  peer->pose.position.x = -0.72;
  const auto hull = collision_hull("-.25;-.20;.25;-.20;.25;.20;-.25;.20");
  const std::vector<PhysicalRobot> robots{
    {own, 0.30, Steady::now(), hull}, {peer, 0.30, Steady::now(), hull}};
  geometry_msgs::msg::TransformStamped transform;
  transform.transform.rotation.w = 1.0;
  auto map_from_world = transform;
  map_from_world.header.frame_id = "map";
  map_from_world.child_frame_id = "world";
  auto global = grid();
  const auto local = global;
  Point target;
  target.x = 0.35;
  const auto check = [&](std::array<bool, 2> exited = {}) {
      return check_clearance({global, local, global, local}, transform, map_from_world, *own, target, 0.0, 0.30, robots, 0, now, exited);
    };

  require(!check().failure, "a full footprint can leave the initial band");
  require(check({true, true}).failure != nullptr, "the band cannot be re-entered");
  const auto static_obstacles = global;
  global.data[30 * 60 + 24] = 254;
  require(check().failure != nullptr, "a static lethal square under the starting footprint is rejected");
  require(!check_clearance({global, local, static_obstacles, local}, transform, map_from_world,
    *own, target, 0.0, 0.30, robots, 0, now).failure,
    "a projected peer edge uses verified physical clearance inside the initial band");
  global.data[30 * 60 + 30] = 254;
  require(check_clearance({global, local, static_obstacles, local}, transform, map_from_world,
    *own, target, 0.0, 0.30, robots, 0, now).failure != nullptr,
    "a raw lethal center is rejected even when physical clearance is available");
  global = grid();
  target.x = -0.15;
  require(check().failure != nullptr, "approaching a lethal obstacle is rejected");
  target.x = 0.35;
  global.data[30 * 60 + 34] = 255;
  require(check().failure != nullptr, "unknown cells under the footprint are rejected");
  global = grid();
  global.data[30 * 60 + 34] = 254;
  require(check().failure != nullptr, "lethal cells under the footprint are rejected");
  global = grid();
  peer->pose.position.x = 0.95;
  require(check().failure != nullptr, "retreat toward another nearby peer is rejected");
  peer->pose.position.x = -0.49;
  require(check().failure != nullptr, "physical peer overlap is rejected");
  peer->pose.position.x = -0.59;
  require(!check().failure, "separated physical hulls can leave with overlapping circular bounds");
  peer->pose.position.x = -0.72;
  peer->header.stamp = rclcpp::Time(4, 0, RCL_ROS_TIME);
  require(check().failure != nullptr, "stale physical pose is rejected");
  std::cout << "12 clearance checks passed\n";
}
