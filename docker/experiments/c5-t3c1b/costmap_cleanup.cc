// Version-pinned experimental backport of Navigation2 #4323.
// Only the lifecycle cleanup symbol is replaced; stock planners/controllers
// and all actuator/permit code stay in the installed Humble binaries.
#include <nav2_costmap_2d/costmap_2d_ros.hpp>

namespace nav2_costmap_2d {
nav2_util::CallbackReturn Costmap2DROS::on_cleanup(const rclcpp_lifecycle::State &) {
  executor_thread_.reset();
  RCLCPP_INFO(get_logger(), "C5_CLEANUP_CALLBACKS_JOINED");
  costmap_publisher_.reset();
  clear_costmap_service_.reset();
  layered_costmap_.reset();
  tf_listener_.reset();
  tf_buffer_.reset();
  footprint_sub_.reset();
  footprint_pub_.reset();
  return nav2_util::CallbackReturn::SUCCESS;
}
}  // namespace nav2_costmap_2d
