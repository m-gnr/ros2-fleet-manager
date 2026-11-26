#include <atomic>

#include "clearance.hpp"
#include "nav2_core/controller.hpp"
#include "nav2_core/exceptions.hpp"
#include "pluginlib/class_list_macros.hpp"

namespace fleet_nav2_escape
{
class ClearanceController : public nav2_core::Controller
{
public:
  void configure(const rclcpp_lifecycle::LifecycleNode::WeakPtr & parent, std::string name,
    std::shared_ptr<tf2_ros::Buffer> tf,
    std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap) override
  {
    node_ = parent.lock();
    tf_ = std::move(tf);
    costmap_ = std::move(costmap);
    const auto topics = node_->declare_parameter<std::vector<std::string>>(name + ".physical_topics");
    const auto radii = node_->declare_parameter<std::vector<double>>(name + ".radii");
    const auto self = node_->declare_parameter<int>(name + ".self_index");
    if (self < 0 || static_cast<size_t>(self) >= radii.size()) {
      throw std::invalid_argument("Invalid recovery robot index");
    }
    self_ = self;
    const auto hulls = node_->declare_parameter<std::vector<std::string>>(name + ".physical_hulls");
    fleet_.subscribe(*node_, topics, radii, hulls);
    radius_ = radii[self_];
    const auto qos = rclcpp::QoS(1).reliable().transient_local();
    global_sub_ = node_->create_subscription<Grid>("global_costmap/costmap_raw", qos,
      [this](Grid::ConstSharedPtr msg) {std::atomic_store(&global_, std::move(msg));});
    local_sub_ = node_->create_subscription<Grid>("local_costmap/costmap_raw", qos,
      [this](Grid::ConstSharedPtr msg) {std::atomic_store(&local_, std::move(msg));});
    global_obstacles_sub_ = node_->create_subscription<Grid>("global_costmap/recovery_obstacle_costmap", qos,
      [this](Grid::ConstSharedPtr msg) {std::atomic_store(&global_obstacles_, std::move(msg));});
    local_obstacles_sub_ = node_->create_subscription<Grid>("local_costmap/recovery_obstacle_costmap", qos,
      [this](Grid::ConstSharedPtr msg) {std::atomic_store(&local_obstacles_, std::move(msg));});
  }

  void cleanup() override
  {
    global_sub_.reset();
    local_sub_.reset();
    global_obstacles_sub_.reset();
    local_obstacles_sub_.reset();
  }

  void activate() override {}
  void deactivate() override {}

  void setPlan(const nav_msgs::msg::Path & path) override
  {
    if (path.poses.size() != 2 || path.header.frame_id.empty()) {
      throw nav2_core::PlannerException("Expected one bounded clearance segment");
    }
    target_ = path.poses.back();
    target_.header.frame_id = path.header.frame_id;
    exited_.fill(false);
    reverse_ = std::cos(tf2::getYaw(target_.pose.orientation) - std::atan2(
      target_.pose.position.y - path.poses.front().pose.position.y,
      target_.pose.position.x - path.poses.front().pose.position.x)) < 0.0;
  }

  void setSpeedLimit(const double & limit, const bool & percentage) override
  {
    speed_limit_ = limit > 0 ? std::min(max_speed, percentage ? max_speed * limit / 100 : limit) :
      max_speed;
  }

  geometry_msgs::msg::TwistStamped computeVelocityCommands(const Pose & local_pose,
    const geometry_msgs::msg::Twist &, nav2_core::GoalChecker *) override
  {
    const auto global = std::atomic_load(&global_), local = std::atomic_load(&local_);
    const auto global_obstacles = std::atomic_load(&global_obstacles_);
    const auto local_obstacles = std::atomic_load(&local_obstacles_);
    const auto now = node_->now();
    if (!global || !local || global->header.frame_id != target_.header.frame_id ||
      local->header.frame_id != local_pose.header.frame_id ||
      !recent(global->header.stamp, now, 1.5) || !recent(local->header.stamp, now, 0.7) ||
      !obstacles_current(global_obstacles, *global, now, 1.5) ||
      !obstacles_current(local_obstacles, *local, now, 0.7))
    {
      throw nav2_core::PlannerException("Clearance costmaps unavailable");
    }

    const auto robots = fleet_.snapshot();
    if (!robots[self_].pose) {
      throw nav2_core::PlannerException("Physical pose unavailable");
    }
    Pose pose;
    geometry_msgs::msg::TransformStamped local_from_map, map_from_world;
    try {
      const auto map_from_local = tf_->lookupTransform(global->header.frame_id,
        local_pose.header.frame_id, tf2::TimePointZero);
      local_from_map = tf_->lookupTransform(local_pose.header.frame_id,
        global->header.frame_id, tf2::TimePointZero);
      map_from_world = tf_->lookupTransform(global->header.frame_id,
        robots[self_].pose->header.frame_id, tf2::TimePointZero);
      tf2::doTransform(local_pose, pose, map_from_local);
    } catch (const tf2::TransformException &) {
      throw nav2_core::PlannerException("Clearance transform unavailable");
    }
    const auto checked = check_clearance({*global, *local, *global_obstacles, *local_obstacles},
      local_from_map, map_from_world, pose,
      target_.pose.position, tf2::getYaw(target_.pose.orientation), radius_,
      robots, self_, now, exited_);
    if (checked.failure) {
      throw nav2_core::PlannerException(checked.failure);
    }
    exited_ = checked.exited;

    const auto remaining = distance(pose.pose.position, target_.pose.position);
    const double end_yaw = tf2::getYaw(target_.pose.orientation);
    const double bearing = std::atan2(target_.pose.position.y - pose.pose.position.y,
      target_.pose.position.x - pose.pose.position.x);
    constexpr double pi = 3.141592653589793;
    const bool arrived = remaining <= clearance_goal_tolerance * 0.8;
    const double yaw = arrived ? end_yaw : bearing + (reverse_ ? pi : 0.0);
    const double error = std::remainder(yaw - tf2::getYaw(pose.pose.orientation), 2 * pi);
    geometry_msgs::msg::TwistStamped command;
    command.header.frame_id = costmap_->getBaseFrameID();
    command.header.stamp = now;
    command.twist.angular.z = std::clamp(2.0 * error, -0.45, 0.45);
    if (!arrived && std::abs(error) < 0.10) {
      const double speed = std::min(speed_limit_.load(), 0.7 * remaining);
      command.twist.linear.x = reverse_ ? -speed : speed;
    }
    return command;
  }

private:
  static constexpr double max_speed = 0.10;
  std::atomic<double> speed_limit_{max_speed};
  rclcpp_lifecycle::LifecycleNode::SharedPtr node_;
  std::shared_ptr<tf2_ros::Buffer> tf_;
  std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_;
  std::array<bool, 2> exited_{};
  Grid::ConstSharedPtr global_, local_, global_obstacles_, local_obstacles_;
  PhysicalFleet fleet_;
  rclcpp::Subscription<Grid>::SharedPtr global_sub_, local_sub_, global_obstacles_sub_,
    local_obstacles_sub_;
  Pose target_;
  size_t self_{0};
  double radius_{0.0};
  bool reverse_{false};
};
}  // namespace fleet_nav2_escape

PLUGINLIB_EXPORT_CLASS(fleet_nav2_escape::ClearanceController, nav2_core::Controller)
