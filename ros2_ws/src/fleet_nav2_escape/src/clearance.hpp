#pragma once

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <limits>
#include <mutex>
#include <optional>
#include <sstream>
#include <vector>

#include "geometry_msgs/msg/point.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "nav2_msgs/msg/costmap.hpp"
#include "rclcpp/rclcpp.hpp"
#include "tf2/utils.h"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"

namespace fleet_nav2_escape
{
using Pose = geometry_msgs::msg::PoseStamped;
using Point = geometry_msgs::msg::Point;
using Grid = nav2_msgs::msg::Costmap;
using Steady = std::chrono::steady_clock;
constexpr double clearance_goal_tolerance = 0.05;
constexpr double clearance_step = 0.0125;

inline double distance(const Point & a, const Point & b)
{
  return std::hypot(a.x - b.x, a.y - b.y);
}

inline Point offset(const Point & p, double dx, double dy)
{
  Point result = p;
  result.x += dx;
  result.y += dy;
  return result;
}

inline bool recent(const builtin_interfaces::msg::Time & stamp, const rclcpp::Time & now, double age)
{
  const auto time = rclcpp::Time(stamp, now.get_clock_type());
  const auto elapsed = (now - time).seconds();
  return time.nanoseconds() > 0 && elapsed >= -0.02 && elapsed <= age;
}

inline std::vector<Point> collision_hull(const std::string & encoded)
{
  std::vector<double> xy;
  std::istringstream input(encoded);
  for (std::string value; std::getline(input, value, ';');) {
    xy.push_back(std::stod(value));
  }
  if (xy.size() < 6 || xy.size() % 2 ||
    std::any_of(xy.begin(), xy.end(), [](double v) {return !std::isfinite(v);}))
  {
    throw std::invalid_argument("Invalid Gazebo collision hull");
  }
  std::vector<Point> hull;
  for (size_t i = 0; i < xy.size(); i += 2) {
    hull.push_back(offset(Point{}, xy[i], xy[i + 1]));
  }
  return hull;
}

inline std::vector<Point> placed_hull(const std::vector<Point> & hull, const Point & p, double yaw)
{
  std::vector<Point> placed;
  placed.reserve(hull.size());
  const double c = std::cos(yaw), s = std::sin(yaw);
  for (const auto & v : hull) {
    placed.push_back(offset(p, c * v.x - s * v.y, s * v.x + c * v.y));
  }
  return placed;
}

inline bool separated_by(const std::vector<Point> & first, const std::vector<Point> & second)
{
  for (size_t i = 0; i < first.size(); ++i) {
    const auto & a = first[i], & b = first[(i + 1) % first.size()];
    const double nx = b.y - a.y, ny = a.x - b.x;
    const double plane = nx * a.x + ny * a.y;
    const double clearance = clearance_step * std::hypot(nx, ny);
    if (std::all_of(second.begin(), second.end(), [&](const Point & point) {
      return nx * point.x + ny * point.y > plane + clearance;
    })) {
      return true;
    }
  }
  return false;
}

struct PhysicalRobot
{
  Pose::ConstSharedPtr pose;
  double radius;
  Steady::time_point received;
  std::vector<Point> hull;
};

class PhysicalFleet
{
public:
  template<typename NodeT>
  void subscribe(NodeT & node, const std::vector<std::string> & topics,
    const std::vector<double> & radii, const std::vector<std::string> & hulls,
    const rclcpp::SubscriptionOptions & options = {})
  {
    if (topics.empty() || topics.size() != radii.size() || topics.size() != hulls.size() ||
      std::any_of(radii.begin(), radii.end(), [](double r) {return !std::isfinite(r) || r <= 0;}))
    {
      throw std::invalid_argument("Invalid recovery fleet geometry");
    }
    robots_.resize(topics.size());
    for (size_t i = 0; i < topics.size(); ++i) {
      robots_[i].radius = radii[i];
      robots_[i].hull = collision_hull(hulls[i]);
      subscriptions_.push_back(node.template create_subscription<Pose>(
        topics[i], rclcpp::SensorDataQoS().keep_last(1),
        [this, i](Pose::ConstSharedPtr msg) {
          std::lock_guard<std::mutex> lock(mutex_);
          auto & robot = robots_[i];
          if (!robot.pose || rclcpp::Time(msg->header.stamp) > rclcpp::Time(robot.pose->header.stamp)) {
            robot.pose = std::move(msg);
            robot.received = Steady::now();
          }
        }, options));
    }
  }

  std::vector<PhysicalRobot> snapshot() const
  {
    std::lock_guard<std::mutex> lock(mutex_);
    return robots_;
  }

private:
  mutable std::mutex mutex_;
  std::vector<PhysicalRobot> robots_;
  std::vector<rclcpp::Subscription<Pose>::SharedPtr> subscriptions_;
};

class ClearanceMap
{
public:
  explicit ClearanceMap(const Grid & grid) : grid_(grid) {}

  struct Sample
  {
    int cost;
    double clearance;
  };

  Sample sample(const Point & p, double radius) const
  {
    const auto & m = grid_.metadata;
    const double step = m.resolution;
    const auto & o = m.origin.position;
    const double margin = radius + clearance_step;
    if (!(step > 0) || !std::isfinite(p.x) || !std::isfinite(p.y) ||
      !std::isfinite(o.x) || !std::isfinite(o.y) ||
      grid_.data.size() != static_cast<size_t>(m.size_x) * m.size_y ||
      p.x - margin < o.x || p.y - margin < o.y ||
      p.x + margin >= o.x + m.size_x * step || p.y + margin >= o.y + m.size_y * step)
    {
      return {255, 0.0};
    }
    const int cx = (p.x - o.x) / step;
    const int cy = (p.y - o.y) / step;
    // Measure distance to the occupied square itself, including its edges.
    // The half-sample margin covers the swept circle between checked points.
    double gap = 0.55;
    const int reach = static_cast<int>(std::ceil(gap / step)) + 1;
    for (int y = std::max(0, cy - reach); y <= std::min(int(m.size_y) - 1, cy + reach); ++y) {
      for (int x = std::max(0, cx - reach); x <= std::min(int(m.size_x) - 1, cx + reach); ++x) {
        if (grid_.data[y * m.size_x + x] < 254) {
          continue;
        }
        const double dx = std::max(0.0, std::abs(o.x + (x + 0.5) * step - p.x) - step / 2);
        const double dy = std::max(0.0, std::abs(o.y + (y + 0.5) * step - p.y) - step / 2);
        gap = std::min(gap, dx * dx + dy * dy);
      }
    }
    return {grid_.data[cy * m.size_x + cx], std::sqrt(gap)};
  }

  bool footprint_clear(const Point & p, double yaw, const std::vector<Point> & hull) const
  {
    const auto & m = grid_.metadata;
    const auto & o = m.origin.position;
    const double step = m.resolution;
    constexpr double margin = clearance_step / 2;
    const auto polygon = placed_hull(hull, p, yaw);
    double min_x = p.x, max_x = p.x, min_y = p.y, max_y = p.y;
    for (const auto & q : polygon) {
      min_x = std::min(min_x, q.x);
      max_x = std::max(max_x, q.x);
      min_y = std::min(min_y, q.y);
      max_y = std::max(max_y, q.y);
    }
    if (min_x - margin < o.x || min_y - margin < o.y ||
      max_x + margin >= o.x + m.size_x * step || max_y + margin >= o.y + m.size_y * step)
    {
      return false;
    }
    // Candidate squares already overlap the polygon's x and y projections.
    // Its remaining separating axes are the normals of its convex edges.
    for (int y = (min_y - margin - o.y) / step; y <= (max_y + margin - o.y) / step; ++y) {
      for (int x = (min_x - margin - o.x) / step; x <= (max_x + margin - o.x) / step; ++x) {
        if (grid_.data[y * m.size_x + x] < 254) {
          continue;
        }
        const double wx = o.x + (x + 0.5) * step, wy = o.y + (y + 0.5) * step;
        const double half = step / 2 + margin;
        bool separated = false;
        for (size_t i = 0; i < polygon.size(); ++i) {
          const auto & a = polygon[i], & b = polygon[(i + 1) % polygon.size()];
          const double nx = b.y - a.y, ny = a.x - b.x;
          const double plane = nx * a.x + ny * a.y;
          if (nx * wx + ny * wy - half * (std::abs(nx) + std::abs(ny)) > plane) {
            separated = true;
            break;
          }
        }
        if (!separated) {
          return false;
        }
      }
    }
    return true;
  }

private:
  const Grid & grid_;
};

inline Point transform_point(const Point & point, const geometry_msgs::msg::TransformStamped & tf)
{
  geometry_msgs::msg::PointStamped source, target;
  source.point = point;
  tf2::doTransform(source, target, tf);
  return target.point;
}

struct ClearanceResult
{
  const char * failure{nullptr};
  std::array<bool, 2> exited{};
  double physical_gap{0.0};
};

struct ClearanceGrids
{
  const Grid & global, & local, & global_obstacles, & local_obstacles;
};

inline bool obstacles_current(const Grid::ConstSharedPtr & obstacles, const Grid & full,
  const rclcpp::Time & now, double max_age)
{
  return obstacles && obstacles->metadata.layer == "before_peer" &&
         obstacles->header.frame_id == full.header.frame_id &&
         recent(obstacles->header.stamp, now, max_age);
}

inline ClearanceResult check_clearance(
  const ClearanceGrids & grids, const geometry_msgs::msg::TransformStamped & local_from_map,
  const geometry_msgs::msg::TransformStamped & map_from_world, const Pose & pose, const Point & target, double target_yaw, double radius,
  const std::vector<PhysicalRobot> & robots, size_t self,
  const rclcpp::Time & now, std::array<bool, 2> exited = {})
{
  if (self >= robots.size()) {
    return {"physical poses unavailable"};
  }
  const auto & own = robots[self].pose;
  const auto & hull = robots[self].hull;
  const auto received_at = Steady::now();
  for (const auto & robot : robots) {
    if (!own || !robot.pose || robot.pose->header.frame_id.empty() ||
      robot.pose->header.frame_id != own->header.frame_id ||
      robot.pose->header.frame_id != map_from_world.child_frame_id ||
      grids.global.header.frame_id != map_from_world.header.frame_id ||
      !recent(robot.pose->header.stamp, now, 0.30) ||
      received_at - robot.received > std::chrono::milliseconds(500) ||
      !std::isfinite(robot.pose->pose.position.x) || !std::isfinite(robot.pose->pose.position.y) ||
      !std::isfinite(tf2::getYaw(robot.pose->pose.orientation)) || robot.hull.size() < 3)
    {
      return {"physical poses unavailable"};
    }
  }
  const double angle = tf2::getYaw(own->pose.orientation) - tf2::getYaw(pose.pose.orientation);
  if (!std::isfinite(angle)) {
    return {"physical heading unavailable"};
  }
  constexpr double pi = 3.141592653589793;
  const double c = std::cos(angle), s = std::sin(angle);
  const double yaw = tf2::getYaw(pose.pose.orientation);
  const double turn = std::remainder(target_yaw - yaw, 2 * pi);
  const double global_yaw = tf2::getYaw(own->pose.orientation) +
    tf2::getYaw(map_from_world.transform.rotation);
  const double local_yaw = yaw + tf2::getYaw(local_from_map.transform.rotation);
  const auto & start = pose.pose.position;
  const double length = distance(start, target);
  if (!std::isfinite(length) || !std::isfinite(turn) ||
    !std::isfinite(global_yaw) || !std::isfinite(local_yaw) || length > 1.05) {
    return {"invalid clearance segment length"};
  }

  const ClearanceMap maps[]{ClearanceMap(grids.global), ClearanceMap(grids.local)};
  const ClearanceMap obstacles[]{ClearanceMap(grids.global_obstacles),
    ClearanceMap(grids.local_obstacles)};
  std::array<double, 2> previous_grid_gap{};
  std::vector<double> start_peer_gap(robots.size(), 0.0);
  std::vector<std::vector<Point>> peer_shapes;
  std::vector<double> hull_radii;
  for (const auto & robot : robots) {
    double bound = robot.radius;
    for (const auto & vertex : robot.hull) {
      bound = std::max(bound, std::hypot(vertex.x, vertex.y));
    }
    hull_radii.push_back(bound);
    peer_shapes.push_back(placed_hull(robot.hull, robot.pose->pose.position,
      tf2::getYaw(robot.pose->pose.orientation)));
  }
  const int rotations = std::max(1, int(std::ceil(std::abs(turn) / 0.025)));
  const int steps = std::max(1, int(std::ceil(length / clearance_step)));
  double physical_gap = std::numeric_limits<double>::infinity();
  std::array<bool, 2> start_exited{};
  for (int i = 0; i <= steps; ++i) {
    const double fraction = double(i) / steps;
    const double dx = (target.x - start.x) * fraction, dy = (target.y - start.y) * fraction;
    const auto point = offset(start, dx, dy);
    const auto physical = offset(own->pose.position, c * dx - s * dy, s * dx + c * dy);
    // Static warehouse geometry is registered to Gazebo's world frame. Check
    // the real swept circle there, and retain the localized center cost as
    // an independent veto. The rolling grid is anchored to live odometry.
    const Point in_grid[]{transform_point(physical, map_from_world),
      transform_point(point, local_from_map)};
    const int nav_cost = maps[0].sample(point, radius).cost;
    const bool was_in_band = !exited[0] || !exited[1];
    const ClearanceMap::Sample raw[]{maps[0].sample(in_grid[0], radius),
      maps[1].sample(in_grid[1], radius)};
    const int costs[]{std::max(nav_cost, raw[0].cost), raw[1].cost};
    // In the band the moving robots are checked as current physical envelopes.
    // Static, scan and unknown cells still use their full occupied squares.
    // As soon as both raw centers are clear, also require the complete raster
    // footprint, including its conservatively rasterized peer observations.
    const bool in_band = costs[0] == 253 || costs[1] == 253;
    for (size_t j = 0; j < 2; ++j) {
      const auto & footprint_map = in_band ? obstacles[j] : maps[j];
      const auto sample = footprint_map.sample(in_grid[j], radius);
      const int cost = costs[j];
      if (cost >= 254 || sample.cost >= 254) {
        return {j == 0 ? "global lethal/unknown center" : "local lethal/unknown center"};
      }
      const double initial_yaw = j == 0 ? global_yaw : local_yaw;
      const auto collision = j == 0 ? "global lethal/unknown footprint" :
        "local lethal/unknown footprint";
      if (i == 0 && sample.clearance <= radius + clearance_step) {
        for (int k = 0; k <= rotations; ++k) {
          if (!footprint_map.footprint_clear(in_grid[j], initial_yaw + turn * k / rotations, hull)) {
            return {collision};
          }
        }
      } else if (sample.clearance <= radius + clearance_step &&
        !footprint_map.footprint_clear(in_grid[j], initial_yaw + turn, hull))
      {
        return {collision};
      }
      if (cost < 253) {
        exited[j] = true;
      } else if (exited[j]) {
        return {"inscribed band re-entry"};
      }
      if (i > 0 && was_in_band && raw[j].clearance + 1e-5 < previous_grid_gap[j]) {
        return {"costmap clearance decreased"};
      }
      previous_grid_gap[j] = raw[j].clearance;
    }
    if (i == 0) {
      start_exited = exited;
    }
    for (size_t j = 0; j < robots.size(); ++j) {
      if (j == self) {
        continue;
      }
      const double gap = distance(physical, robots[j].pose->pose.position) -
        hull_radii[self] - hull_radii[j];
      if (gap <= clearance_step) {
        const int first = i == 0 ? 0 : rotations;
        for (int k = first; k <= rotations; ++k) {
          const auto subject = placed_hull(hull, physical,
            tf2::getYaw(own->pose.orientation) + turn * k / rotations);
          if (!separated_by(subject, peer_shapes[j]) && !separated_by(peer_shapes[j], subject)) {
            return {"physical peer footprint overlap"};
          }
        }
      }
      if (i == 0) {
        start_peer_gap[j] = gap;
        physical_gap = std::min(physical_gap, gap);
      } else if (was_in_band && start_peer_gap[j] < 0.45 && gap + 1e-5 < start_peer_gap[j]) {
        return {"physical peer clearance decreased"};
      }
    }
  }
  if (!exited[0] || !exited[1]) {
    return {"segment did not leave the inscribed band"};
  }
  return {nullptr, start_exited, physical_gap};
}
}  // namespace fleet_nav2_escape
