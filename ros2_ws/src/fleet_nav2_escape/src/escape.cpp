#include <fcntl.h>
#include <sys/file.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <optional>
#include <map>
#include <sstream>
#include <utility>

#include "behaviortree_cpp_v3/bt_factory.h"
#include "clearance.hpp"
#include "nav2_behavior_tree/plugins/action/follow_path_action.hpp"
#include "nav2_msgs/action/compute_path_to_pose.hpp"
#include "nav2_msgs/msg/costmap.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "tf2/utils.h"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"
#include "tf2_ros/buffer.h"

namespace fleet_nav2_escape
{
using namespace std::chrono_literals;
using Clock = std::chrono::steady_clock;
using Path = nav_msgs::msg::Path;
using Compute = nav2_msgs::action::ComputePathToPose;
using Follow = nav2_msgs::action::FollowPath;
using ResultCode = rclcpp_action::ResultCode;
using Status = BT::NodeStatus;

std::vector<std::string> split_port(const std::string & value, char delimiter = ';')
{
  std::vector<std::string> parts;
  std::istringstream input(value);
  for (std::string part; std::getline(input, part, delimiter);) {
    parts.push_back(part);
  }
  return parts;
}

std::string goal_id(const rclcpp_action::GoalUUID & uuid)
{
  constexpr char hex[] = "0123456789abcdef";
  std::string result;
  result.reserve(uuid.size() * 2);
  for (const auto byte : uuid) {
    result.push_back(hex[byte >> 4]);
    result.push_back(hex[byte & 0xf]);
  }
  return result;
}

class FleetFollowPath : public nav2_behavior_tree::FollowPathAction
{
public:
  FleetFollowPath(const std::string & name, const BT::NodeConfiguration & conf)
  : FollowPathAction(name, "follow_path", conf) {}

  static BT::PortsList providedPorts()
  {
    auto ports = FollowPathAction::providedPorts();
    ports.insert(BT::OutputPort<std::string>("aborted"));
    return ports;
  }

  void on_tick() override
  {
    setOutput("aborted", std::string("none"));
    FollowPathAction::on_tick();
  }

  Status on_aborted() override
  {
    setOutput("aborted", goal_id(result_.goal_id));
    return Status::FAILURE;
  }

  Status on_cancelled() override {return Status::FAILURE;}
};

// All warehouse navigators run in one simulation container. A dirty file keeps
// the session closed if a process dies or an escape goal has no terminal result.
class EscapeLease
{
public:
  ~EscapeLease() {release();}

  bool acquire(const std::string & path)
  {
    fd_ = open(path.c_str(), O_CREAT | O_RDWR | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd_ < 0) {
      return false;
    }
    char state = 0;
    if (flock(fd_, LOCK_EX | LOCK_NB) != 0 || pread(fd_, &state, 1, 0) != 0) {
      release();
      return false;
    }
    return true;
  }

  bool mark_motion() {return pwrite(fd_, "1", 1, 0) == 1;}
  void confirm_terminal()
  {
    if (fd_ >= 0) {
      ftruncate(fd_, 0);
    }
  }

  void release()
  {
    if (fd_ >= 0) {
      close(std::exchange(fd_, -1));
    }
  }

private:
  int fd_{-1};
};

struct GridBlock
{
  const char * reason;
  int cost;
  double x, y;
};

std::optional<GridBlock> blocked_cell(const Grid & grid, const Point & point, double footprint)
{
  const auto & meta = grid.metadata;
  const auto & origin = meta.origin.position;
  const double step = meta.resolution;
  const double radius = footprint + step * std::sqrt(0.5);
  if (!std::isfinite(point.x) || !std::isfinite(point.y) || !(step > 0) ||
    point.x - radius < origin.x || point.y - radius < origin.y ||
    point.x + radius >= origin.x + meta.size_x * step ||
    point.y + radius >= origin.y + meta.size_y * step ||
    grid.data.size() != static_cast<size_t>(meta.size_x) * meta.size_y)
  {
    return GridBlock{"outside_or_invalid_grid", -1, point.x, point.y};
  }
  const int cx = (point.x - origin.x) / step;
  const int cy = (point.y - origin.y) / step;
  // Raw Nav2 costs: 253 is inscribed, 254 lethal and 255 unknown.
  const int center_cost = grid.data[cy * meta.size_x + cx];
  if (center_cost >= 253) {
    return GridBlock{
      "center_cost", center_cost, origin.x + (cx + 0.5) * step, origin.y + (cy + 0.5) * step};
  }
  for (int y = (point.y - radius - origin.y) / step;
    y <= (point.y + radius - origin.y) / step; ++y)
  {
    for (int x = (point.x - radius - origin.x) / step;
      x <= (point.x + radius - origin.x) / step; ++x)
    {
      const int cost = grid.data[y * meta.size_x + x];
      const double cell_x = origin.x + (x + 0.5) * step;
      const double cell_y = origin.y + (y + 0.5) * step;
      if (cost >= 254 && std::hypot(cell_x - point.x, cell_y - point.y) <= radius) {
        return GridBlock{"footprint_cost", cost, cell_x, cell_y};
      }
    }
  }
  return std::nullopt;
}

class FleetEscape : public BT::StatefulActionNode
{
public:
  FleetEscape(const std::string & name, const BT::NodeConfiguration & conf)
  : BT::StatefulActionNode(name, conf),
    node_(conf.blackboard->get<rclcpp::Node::SharedPtr>("node"))
  {
    group_ = node_->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive, false);
    executor_.add_callback_group(group_, node_->get_node_base_interface());
    planner_ = rclcpp_action::create_client<Compute>(node_, "compute_path_to_pose", group_);
    controller_ = rclcpp_action::create_client<Follow>(node_, "follow_path", group_);
    rclcpp::SubscriptionOptions options;
    options.callback_group = group_;
    const auto grid_qos = rclcpp::QoS(1).reliable().transient_local();
    global_sub_ = node_->create_subscription<Grid>(
      "global_costmap/costmap_raw", grid_qos,
      [this](Grid::ConstSharedPtr grid) {global_ = std::move(grid);}, options);
    local_sub_ = node_->create_subscription<Grid>(
      "local_costmap/costmap_raw", grid_qos,
      [this](Grid::ConstSharedPtr grid) {local_ = std::move(grid);}, options);
    global_obstacles_sub_ = node_->create_subscription<Grid>(
      "global_costmap/recovery_obstacle_costmap", grid_qos,
      [this](Grid::ConstSharedPtr grid) {global_obstacles_ = std::move(grid);}, options);
    local_obstacles_sub_ = node_->create_subscription<Grid>(
      "local_costmap/recovery_obstacle_costmap", grid_qos,
      [this](Grid::ConstSharedPtr grid) {local_obstacles_ = std::move(grid);}, options);
    const auto topic = getInput<std::string>("odom_topic").value();
    odom_sub_ = node_->create_subscription<nav_msgs::msg::Odometry>(
      topic, rclcpp::SensorDataQoS().keep_last(1),
      [this](nav_msgs::msg::Odometry::ConstSharedPtr odom) {odom_ = std::move(odom);}, options);
    const auto topics = split_port(getInput<std::string>("physical_topics").value());
    std::vector<double> radii;
    for (const auto & part : split_port(getInput<std::string>("physical_radii").value())) {
      radii.push_back(std::stod(part));
    }
    self_ = getInput<unsigned>("self_index").value();
    if (self_ >= radii.size()) {
      throw std::invalid_argument("Invalid clearance robot index");
    }
    const auto hulls = split_port(getInput<std::string>("physical_hulls").value(), '|');
    fleet_.subscribe(*node_, topics, radii, hulls, options);
  }

  static BT::PortsList providedPorts()
  {
    return {
      BT::InputPort<Pose>("goal"), BT::InputPort<std::string>("aborted"),
      BT::InputPort<double>("radius"), BT::InputPort<double>("footprint"),
      BT::InputPort<std::string>("base_frame"), BT::InputPort<std::string>("odom_topic"),
      BT::InputPort<std::string>("lease"), BT::InputPort<std::string>("physical_topics"),
      BT::InputPort<std::string>("physical_radii"), BT::InputPort<unsigned>("self_index"),
      BT::InputPort<std::string>("physical_hulls")
    };
  }

  Status onStart() override
  {
    aborted_ = getInput<std::string>("aborted").value();
    if (aborted_ == "none") {
      return Status::FAILURE;
    }
    original_ = getInput<Pose>("goal").value();
    radius_ = getInput<double>("radius").value();
    footprint_ = getInput<double>("footprint").value();
    if (!std::isfinite(radius_) || radius_ < minimum_candidate_radius || !std::isfinite(footprint_) ||
      footprint_ <= 0.0 || !planner_->action_server_is_ready() ||
      !controller_->action_server_is_ready())
    {
      return fail("configuration or Nav2 action unavailable");
    }
    tf_ = config().blackboard->get<std::shared_ptr<tf2_ros::Buffer>>("tf_buffer");
    base_ = getInput<std::string>("base_frame").value();
    candidate_index_ = 0;
    rejections_.fill(0);
    plans_received_ = 0;
    clearance_mode_ = false;
    physical_start_.reset();
    phase_ = Phase::settling;
    deadline_ = Clock::now() + 3s;
    RCLCPP_INFO(node_->get_logger(), "FLEET_ESCAPE_TRIGGER aborted_follow=%s", aborted_.c_str());
    return onRunning();
  }

  Status onRunning() override
  {
    executor_.spin_some();
    if (getInput<Pose>("goal").value() != original_) {
      return fail("original goal changed");
    }
    if (Clock::now() > deadline_) {
      if (phase_ == Phase::planning) {
        reject(Rejection::planner, "planner did not respond before search deadline");
        log_search();
      }
      return fail("escape timed out");
    }
    const auto pose = current_pose();
    if (phase_ == Phase::settling) {
      if (!pose || !stopped()) {
        return Status::RUNNING;
      }
      const auto local_point = transform_point(pose->pose.position, local_from_map_);
      const bool in_band = ClearanceMap(*global_).sample(pose->pose.position, footprint_).cost == 253 ||
        ClearanceMap(*local_).sample(local_point, footprint_).cost == 253;
      if (in_band) {
        const auto robots = fleet_.snapshot();
        if (!robots[self_].pose ||
          !obstacles_current(global_obstacles_, *global_, node_->now(), 1.5) ||
          !obstacles_current(local_obstacles_, *local_, node_->now(), 0.7))
        {
          return Status::RUNNING;
        }
        start_ = *pose;
        return depart_band(*pose, robots);
      }
      start_ = *pose;
      return plan_next(*pose);
    }
    if (!pose) {
      return fail("TF, odometry or costmap unavailable");
    }

    switch (phase_) {
      case Phase::planning:
        return poll_plan(*pose);
      case Phase::driving:
        return poll_drive();
      case Phase::arriving: {
        if (!stopped()) {
          return Status::RUNNING;
        }
        const double tolerance = clearance_mode_ ? clearance_goal_tolerance : arrival_tolerance;
        if (distance(pose->pose.position, target_.pose.position) > tolerance ||
          distance(pose->pose.position, start_.pose.position) <
          distance(target_.pose.position, start_.pose.position) - tolerance ||
          (clearance_mode_ && blockage(pose->pose.position)))
        {
          return fail("escape displacement or arrival not verified");
        }
        if (clearance_mode_) {
          const auto robots = fleet_.snapshot();
          const auto & current = robots[self_].pose;
          if (!physical_start_ || !current ||
            current->header.frame_id != physical_start_->header.frame_id ||
            !recent(current->header.stamp, node_->now(), 0.30) ||
            !(distance(current->pose.position, physical_start_->pose.position) >=
            distance(target_.pose.position, start_.pose.position) - 2 * clearance_goal_tolerance))
          {
            return fail("Gazebo escape displacement not verified");
          }
          RCLCPP_INFO(node_->get_logger(), "FLEET_CLEARANCE_PHYSICAL moved_m=%.3f",
            distance(current->pose.position, physical_start_->pose.position));
        }
        RCLCPP_INFO(node_->get_logger(),
          "FLEET_ESCAPE_ARRIVED follow=%s x=%.3f y=%.3f moved=%.3f original_x=%.3f original_y=%.3f "
          "sim_ns=%lld",
          escape_id_.c_str(), pose->pose.position.x, pose->pose.position.y,
          distance(pose->pose.position, start_.pose.position), original_.pose.position.x,
          original_.pose.position.y, static_cast<long long>(node_->now().nanoseconds()));
        lease_.confirm_terminal();
        lease_.release();
        return Status::SUCCESS;
      }
      case Phase::settling:
        break;
    }
    return Status::FAILURE;
  }

  void onHalted() override
  {
    stop_pending_motion();
    reset_plan();
    lease_.release();
  }

private:
  enum class Phase {settling, planning, driving, arriving};
  enum class Rejection {candidate, planner, start, route, invalid};
  static constexpr std::array<const char *, 5> rejection_names{
    "candidate_blocked", "planner_no_path", "route_start_blocked", "route_blocked", "route_invalid"};
  static constexpr double arrival_tolerance = 0.25;
  static constexpr double minimum_candidate_radius = 0.40;

  struct Blockage
  {
    const char * grid;
    GridBlock cell;
  };

  bool fresh(const builtin_interfaces::msg::Time & stamp, double max_age) const
  {
    const rclcpp::Time now = node_->now();
    const rclcpp::Time time(stamp, now.get_clock_type());
    const double age = (now - time).seconds();
    return time.nanoseconds() > 0 && age >= -0.1 && age <= max_age;
  }

  bool stopped() const
  {
    const auto & twist = odom_->twist.twist;
    return std::hypot(twist.linear.x, twist.linear.y) <= 0.01 &&
           std::abs(twist.angular.z) <= 0.01;
  }

  std::optional<Pose> current_pose()
  {
    if (!odom_ || !global_ || !local_ || !fresh(odom_->header.stamp, 1.0) ||
      !fresh(global_->header.stamp, 2.0) || !fresh(local_->header.stamp, 1.0) ||
      global_->header.frame_id != original_.header.frame_id ||
      local_->header.frame_id != odom_->header.frame_id || odom_->child_frame_id != base_)
    {
      return std::nullopt;
    }
    try {
      const auto transform = tf_->lookupTransform(global_->header.frame_id, base_, tf2::TimePointZero);
      local_from_map_ = tf_->lookupTransform(
        local_->header.frame_id, global_->header.frame_id, tf2::TimePointZero);
      if (!fresh(transform.header.stamp, 1.0)) {
        return std::nullopt;
      }
      Pose pose;
      pose.header = transform.header;
      pose.pose.position.x = transform.transform.translation.x;
      pose.pose.position.y = transform.transform.translation.y;
      pose.pose.orientation = transform.transform.rotation;
      return pose;
    } catch (const tf2::TransformException &) {
      return std::nullopt;
    }
  }

  std::optional<Blockage> blockage(const Point & point) const
  {
    if (const auto block = blocked_cell(*global_, point, footprint_)) {
      return Blockage{"global", *block};
    }
    geometry_msgs::msg::PointStamped map_point, local_point;
    map_point.point = point;
    tf2::doTransform(map_point, local_point, local_from_map_);
    if (const auto block = blocked_cell(*local_, local_point.point, footprint_)) {
      return Blockage{"local", *block};
    }
    return std::nullopt;
  }

  void reject(Rejection reason, const char * detail, const Point & sample = Point{},
    const std::optional<Blockage> & block = std::nullopt)
  {
    const auto index = static_cast<size_t>(reason);
    ++rejections_[index];
    const Blockage no_cell{"none", {"none", -1, 0.0, 0.0}};
    const auto & hit = block ? *block : no_cell;
    RCLCPP_INFO(node_->get_logger(),
      "FLEET_ESCAPE_REJECT aborted_follow=%s candidate=%zu radius_m=%.3f target=(%.3f,%.3f) "
      "reason=%s detail=%s sample_map=(%.3f,%.3f) grid=%s check=%s raw_cost=%d cell=(%.3f,%.3f)",
      aborted_.c_str(), candidate_index_, candidate_radius_, target_.pose.position.x,
      target_.pose.position.y, rejection_names[index], detail, sample.x, sample.y,
      hit.grid, hit.cell.reason, hit.cell.cost, hit.cell.x, hit.cell.y);
  }

  void log_search() const
  {
    RCLCPP_INFO(node_->get_logger(),
      "FLEET_ESCAPE_SEARCH aborted_follow=%s attempted=%zu nav2_paths=%zu "
      "candidate_blocked=%zu planner_no_path=%zu route_start_blocked=%zu route_blocked=%zu "
      "route_invalid=%zu",
      aborted_.c_str(), candidate_index_, plans_received_, rejections_[0], rejections_[1],
      rejections_[2], rejections_[3], rejections_[4]);
  }

  bool clear_route(const Path & route, const Pose & pose)
  {
    const double stride = 0.5 * std::min(global_->metadata.resolution, local_->metadata.resolution);
    if (route.header.frame_id != pose.header.frame_id || !(stride > 0) ||
      !(distance(route.poses.back().pose.position, target_.pose.position) <= 0.10))
    {
      reject(Rejection::invalid, "route frame, resolution or endpoint mismatch");
      return false;
    }
    Point from = pose.pose.position;
    if (const auto block = blockage(from)) {
      reject(Rejection::start, "measured robot position", from, block);
      return false;
    }
    double length = 0.0;
    for (const auto & waypoint : route.poses) {
      const Point & to = waypoint.pose.position;
      const double segment = distance(from, to);
      length += segment;
      if (waypoint.header.frame_id != route.header.frame_id || !std::isfinite(length) ||
        length > 2.0 * radius_)
      {
        reject(Rejection::invalid, "waypoint frame or route length");
        return false;
      }
      const int samples = std::max(1, static_cast<int>(std::ceil(segment / stride)));
      // The previous endpoint (including the measured start) was checked above.
      for (int i = 1; i <= samples; ++i) {
        const double fraction = static_cast<double>(i) / samples;
        Point point;
        point.x = from.x + fraction * (to.x - from.x);
        point.y = from.y + fraction * (to.y - from.y);
        if (const auto block = blockage(point)) {
          reject(Rejection::route, "route sample after measured start", point, block);
          return false;
        }
      }
      from = to;
    }
    if (const auto block = blockage(target_.pose.position)) {
      reject(Rejection::candidate, "target blocked on updated costmap", target_.pose.position, block);
      return false;
    }
    return true;
  }

  Status depart_band(const Pose & pose, const std::vector<PhysicalRobot> & robots)
  {
    constexpr double pi = 3.141592653589793;
    constexpr std::array<int, 16> headings{0, 8, 1, -1, 7, -7, 2, -2, 6, -6, 3, -3, 5, -5, 4, -4};
    const auto now = node_->now();
    geometry_msgs::msg::TransformStamped map_from_world;
    try {
      map_from_world = tf_->lookupTransform(
        pose.header.frame_id, robots[self_].pose->header.frame_id, tf2::TimePointZero);
    } catch (const tf2::TransformException &) {
      return fail("Gazebo world transform unavailable");
    }
    const double heading = tf2::getYaw(pose.pose.orientation);
    std::map<std::string, size_t> rejected;
    for (const double length : {0.30, 0.45, 0.60, radius_}) {
      if (length > radius_) {
        continue;
      }
      for (const int direction : headings) {
        const double yaw = heading + direction * pi / 8;
        const auto candidate = offset(pose.pose.position, length * std::cos(yaw), length * std::sin(yaw));
        // The stop tolerance must also lie outside the band.
        const auto near_end = offset(candidate, -0.07 * std::cos(yaw), -0.07 * std::sin(yaw));
        if (blockage(near_end) || blockage(candidate)) {
          ++rejected["normal exit blocked"];
          continue;
        }
        const double facing = yaw + (std::cos(yaw - heading) < 0.0 ? pi : 0.0);
        const auto checked = check_clearance(
          {*global_, *local_, *global_obstacles_, *local_obstacles_}, local_from_map_,
          map_from_world, pose, candidate,
          facing, footprint_, robots, self_, now);
        if (checked.failure) {
          ++rejected[checked.failure];
          continue;
        }
        target_ = pose;
        target_.pose.position = candidate;
        tf2::Quaternion orientation;
        orientation.setRPY(0, 0, facing);
        target_.pose.orientation = tf2::toMsg(orientation);
        Path segment;
        segment.header = pose.header;
        segment.poses = {pose, target_};
        clearance_mode_ = true;
        physical_start_ = robots[self_].pose;
        RCLCPP_INFO(node_->get_logger(),
          "FLEET_CLEARANCE_SELECTED distance_m=%.3f physical_peer_gap_m=%.3f",
          length, checked.physical_gap);
        return dispatch(segment);
      }
    }
    for (const auto & item : rejected) {
      RCLCPP_WARN(node_->get_logger(), "FLEET_CLEARANCE_REJECT count=%zu reason=%s",
        item.second, item.first.c_str());
    }
    return fail("no safe departure from inscribed band");
  }

  Status plan_next(const Pose & pose)
  {
    constexpr double pi = 3.141592653589793;
    constexpr std::array<double, 8> headings{pi/2, -pi/2, pi/4, -pi/4, 0, 3*pi/4, -3*pi/4, pi};
    constexpr size_t rings = 3;
    while (candidate_index_ < headings.size() * rings) {
      const size_t ring = candidate_index_ / headings.size();
      const double distance_step = (radius_ - minimum_candidate_radius) / (rings - 1);
      candidate_radius_ = radius_ - ring * distance_step;
      const double yaw = tf2::getYaw(start_.pose.orientation) +
        headings[candidate_index_++ % headings.size()];
      target_ = start_;
      target_.header.stamp = node_->now();
      target_.pose.position.x += candidate_radius_ * std::cos(yaw);
      target_.pose.position.y += candidate_radius_ * std::sin(yaw);
      tf2::Quaternion orientation;
      orientation.setRPY(0, 0, yaw);
      target_.pose.orientation = tf2::toMsg(orientation);
      if (const auto block = blockage(target_.pose.position)) {
        reject(Rejection::candidate, "candidate footprint", target_.pose.position, block);
        continue;
      }
      Compute::Goal goal;
      goal.start = pose;
      goal.goal = target_;
      goal.use_start = true;
      goal.planner_id = "GridBased";
      plan_ack_ = planner_->async_send_goal(goal);
      if (phase_ == Phase::settling) {
        deadline_ = Clock::now() + 5s;
      }
      phase_ = Phase::planning;
      return Status::RUNNING;
    }
    log_search();
    return fail("no traversable escape candidate");
  }

  template<typename Future>
  static bool ready(const Future & future)
  {
    return future.valid() && future.wait_for(0s) == std::future_status::ready;
  }

  Status poll_plan(const Pose & pose)
  {
    if (ready(plan_ack_)) {
      const auto handle = plan_ack_.get();
      plan_ack_ = {};
      if (!handle) {
        reject(Rejection::planner, "planner rejected goal request");
        return plan_next(pose);
      }
      plan_result_ = planner_->async_get_result(handle);
    }
    if (!ready(plan_result_)) {
      return Status::RUNNING;
    }
    const auto result = plan_result_.get();
    plan_result_ = {};
    if (result.code != ResultCode::SUCCEEDED || !result.result || result.result->path.poses.empty()) {
      reject(Rejection::planner, "planner action failed or returned an empty path");
      return plan_next(pose);
    }
    ++plans_received_;
    if (!clear_route(result.result->path, pose)) {
      return plan_next(pose);
    }
    log_search();
    return dispatch(result.result->path);
  }

  Status dispatch(const Path & path)
  {
    if (!stopped()) {
      return fail("stop unconfirmed");
    }
    if (!lease_.acquire(getInput<std::string>("lease").value()) || !lease_.mark_motion()) {
      return fail("escape occupied or prior motion unconfirmed");
    }
    Follow::Goal goal;
    goal.path = path;
    goal.controller_id = clearance_mode_ ? "FleetClearance" : "FollowPath";
    goal.goal_checker_id = clearance_mode_ ? "clearance_goal_checker" : "general_goal_checker";
    drive_ack_ = controller_->async_send_goal(goal);
    phase_ = Phase::driving;
    deadline_ = Clock::now() + 2s;
    RCLCPP_INFO(node_->get_logger(),
      "FLEET_ESCAPE_DISPATCH aborted_follow=%s start=(%.3f,%.3f) target=(%.3f,%.3f) "
      "poses=%zu sim_ns=%lld",
      aborted_.c_str(), start_.pose.position.x, start_.pose.position.y,
      target_.pose.position.x, target_.pose.position.y, goal.path.poses.size(),
      static_cast<long long>(node_->now().nanoseconds()));
    return Status::RUNNING;
  }

  Status poll_drive()
  {
    if (ready(drive_ack_)) {
      drive_handle_ = drive_ack_.get();
      drive_ack_ = {};
      if (!drive_handle_) {
        lease_.confirm_terminal();
        return fail("controller rejected escape goal");
      }
      escape_id_ = goal_id(drive_handle_->get_goal_id());
      drive_result_ = controller_->async_get_result(drive_handle_);
      deadline_ = Clock::now() + 45s;
      RCLCPP_INFO(node_->get_logger(), "FLEET_ESCAPE_ACCEPTED follow=%s", escape_id_.c_str());
    }
    if (!ready(drive_result_)) {
      return Status::RUNNING;
    }
    const auto code = drive_result_.get().code;
    drive_result_ = {};
    drive_handle_.reset();
    if (code == ResultCode::UNKNOWN) {
      return fail("escape result unconfirmed");
    }
    if (code != ResultCode::SUCCEEDED) {
      confirm_stopped();
      return fail("escape FollowPath failed");
    }
    phase_ = Phase::arriving;
    deadline_ = Clock::now() + 2s;
    return Status::RUNNING;
  }

  void stop_pending_motion()
  {
    if (drive_ack_.valid() &&
      executor_.spin_until_future_complete(drive_ack_, 500ms) == rclcpp::FutureReturnCode::SUCCESS)
    {
      drive_handle_ = drive_ack_.get();
      if (drive_handle_) {
        drive_result_ = controller_->async_get_result(drive_handle_);
      } else {
        lease_.confirm_terminal();
      }
    }
    if (drive_handle_) {
      if (!ready(drive_result_)) {
        try {
          controller_->async_cancel_goal(drive_handle_);
        } catch (const rclcpp_action::exceptions::UnknownGoalHandleError &) {
          // The result can arrive before the cancel call reaches the server.
        }
      }
      if (executor_.spin_until_future_complete(drive_result_, 1s) ==
        rclcpp::FutureReturnCode::SUCCESS && drive_result_.get().code != ResultCode::UNKNOWN)
      {
        confirm_stopped();
      }
    }
    drive_ack_ = {};
    drive_handle_.reset();
    drive_result_ = {};
  }

  void confirm_stopped()
  {
    executor_.spin_some();
    if (odom_ && fresh(odom_->header.stamp, 1.0) && stopped()) {
      lease_.confirm_terminal();
    }
  }

  void reset_plan()
  {
    // ComputePathToPose cannot move the robot. Do not cancel another client's goal.
    plan_ack_ = {};
    plan_result_ = {};
  }

  Status fail(const char * reason)
  {
    stop_pending_motion();
    reset_plan();
    lease_.release();
    RCLCPP_WARN(node_->get_logger(), "FLEET_ESCAPE_FAILED aborted_follow=%s reason=%s",
      aborted_.c_str(), reason);
    return Status::FAILURE;
  }

  rclcpp::Node::SharedPtr node_;
  rclcpp::CallbackGroup::SharedPtr group_;
  rclcpp::executors::SingleThreadedExecutor executor_;
  rclcpp_action::Client<Compute>::SharedPtr planner_;
  rclcpp_action::Client<Follow>::SharedPtr controller_;
  rclcpp::Subscription<Grid>::SharedPtr global_sub_, local_sub_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
  rclcpp::Subscription<Grid>::SharedPtr global_obstacles_sub_, local_obstacles_sub_;
  Grid::ConstSharedPtr global_, local_, global_obstacles_, local_obstacles_;
  nav_msgs::msg::Odometry::ConstSharedPtr odom_;
  std::shared_ptr<tf2_ros::Buffer> tf_;
  geometry_msgs::msg::TransformStamped local_from_map_;
  std::shared_future<rclcpp_action::ClientGoalHandle<Compute>::SharedPtr> plan_ack_;
  std::shared_future<rclcpp_action::ClientGoalHandle<Compute>::WrappedResult> plan_result_;
  std::shared_future<rclcpp_action::ClientGoalHandle<Follow>::SharedPtr> drive_ack_;
  std::shared_future<rclcpp_action::ClientGoalHandle<Follow>::WrappedResult> drive_result_;
  rclcpp_action::ClientGoalHandle<Follow>::SharedPtr drive_handle_;
  EscapeLease lease_;
  PhysicalFleet fleet_;
  Pose::ConstSharedPtr physical_start_;
  size_t self_{0};
  bool clearance_mode_{false};
  Clock::time_point deadline_;
  Phase phase_{Phase::settling};
  Pose original_, start_, target_;
  std::string aborted_, escape_id_, base_;
  size_t candidate_index_{0}, plans_received_{0};
  std::array<size_t, rejection_names.size()> rejections_{};
  double radius_{0.0}, footprint_{0.0}, candidate_radius_{0.0};
};
}  // namespace fleet_nav2_escape

BT_REGISTER_NODES(factory)
{
  factory.registerNodeType<fleet_nav2_escape::FleetFollowPath>("FleetFollowPath");
  factory.registerNodeType<fleet_nav2_escape::FleetEscape>("FleetEscape");
}
