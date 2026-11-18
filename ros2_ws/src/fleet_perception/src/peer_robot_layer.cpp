#include <algorithm>
#include <chrono>
#include <cmath>
#include <map>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <vector>

#include "nav2_costmap_2d/layer.hpp"
#include "nav2_costmap_2d/layered_costmap.hpp"
#include "nav2_costmap_2d/cost_values.hpp"
#include "pluginlib/class_list_macros.hpp"
#include "std_msgs/msg/string.hpp"
#include "tf2_msgs/msg/tf_message.hpp"
#include "tf2_ros/buffer.h"

namespace fleet_perception
{
// An additional geometric observation, never a traffic permit or actuator gate.
// The experiment is opt-in when generating the warehouse Nav2 parameters.
class PeerRobotLayer : public nav2_costmap_2d::Layer
{
  using Steady = std::chrono::steady_clock;
  struct Edge {
    std::string parent;
    int64_t stamp{0};
    Steady::time_point received{};
    bool invalid{false};
  };
  struct Disc {double x, y, radius;};
public:
  void onInitialize() override
  {
    auto node = node_.lock();
    if (!node) throw std::runtime_error("Costmap lifecycle node unavailable");
    // Required parameters have no independent robot/geometry/timing defaults.
    declareParameter("robot_ids", rclcpp::ParameterType::PARAMETER_STRING_ARRAY);
    declareParameter("tf_topics", rclcpp::ParameterType::PARAMETER_STRING_ARRAY);
    declareParameter("radii", rclcpp::ParameterType::PARAMETER_DOUBLE_ARRAY);
    for (auto key : {"self_id", "map_frame"}) declareParameter(key, rclcpp::ParameterType::PARAMETER_STRING);
    for (auto key : {"pose_age_sec", "transport_sec", "localization_age_sec", "future_tolerance_sec"}) {
      declareParameter(key, rclcpp::ParameterType::PARAMETER_DOUBLE);
    }
    ids_ = node->get_parameter(name_ + ".robot_ids").as_string_array();
    const auto topics = node->get_parameter(name_ + ".tf_topics").as_string_array();
    radii_ = node->get_parameter(name_ + ".radii").as_double_array();
    self_ = node->get_parameter(name_ + ".self_id").as_string();
    frame_ = node->get_parameter(name_ + ".map_frame").as_string();
    pose_age_ = node->get_parameter(name_ + ".pose_age_sec").as_double();
    transport_ = node->get_parameter(name_ + ".transport_sec").as_double();
    localization_age_ = node->get_parameter(name_ + ".localization_age_sec").as_double();
    future_ = node->get_parameter(name_ + ".future_tolerance_sec").as_double();
    if (ids_.size() != radii_.size() || ids_.size() != topics.size() || ids_.empty() || frame_.empty() ||
      std::count(ids_.begin(), ids_.end(), self_) != 1 ||
      !positive(pose_age_) || !positive(transport_) ||
      !positive(localization_age_) || !positive(future_)) {
      throw std::runtime_error("Explicit fleet geometry and freshness budgets required");
    }
    for (size_t i = 0; i < ids_.size(); ++i) {
      if (!positive(radii_[i]) || ids_[i].empty() || topics[i].empty() || topics[i][0] != '/' ||
        !edges_.emplace(ids_[i] + "/odom", Edge{frame_}).second ||
        !edges_.emplace(ids_[i] + "/base_link", Edge{ids_[i] + "/odom"}).second) {
        throw std::runtime_error("Invalid/duplicate peer geometry");
      }
    }
    buffer_ = std::make_unique<tf2_ros::Buffer>(node->get_clock());
    // Nav2 remaps /tf to a relative topic, including inside costmap namespaces.
    // Explicit configured namespace topics reuse the existing TF publications
    // and avoid silently subscribing to /robot/global_costmap/tf.
    rclcpp::SubscriptionOptions options;
    options.callback_group = callback_group_;
    for (size_t i = 0; i < ids_.size(); ++i) {
      subscriptions_.push_back(node->create_subscription<tf2_msgs::msg::TFMessage>(
        topics[i], rclcpp::QoS(100),
        [this, id = ids_[i]](tf2_msgs::msg::TFMessage::ConstSharedPtr packet) {
          receive(*packet, id);
        }, options));
    }
    publisher_ = node->create_publisher<std_msgs::msg::String>("peer_observations", 1);
    publisher_->on_activate();
    enabled_ = true;
    current_ = false;
  }

  void updateBounds(double, double, double, double * min_x, double * min_y,
    double * max_x, double * max_y) override
  {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto steady = Steady::now();
    const int64_t now = clock_->now().nanoseconds();
    rewind(now);
    // Old and new bounds both participate so moving peers leave no ghost costs.
    auto expand = [&](const Disc & d) {
        const auto cell = layered_costmap_->getCostmap()->getResolution();
        *min_x = std::min(*min_x, d.x - d.radius - cell);
        *min_y = std::min(*min_y, d.y - d.radius - cell);
        *max_x = std::max(*max_x, d.x + d.radius + cell);
        *max_y = std::max(*max_y, d.y + d.radius + cell);
      };
    for (const auto & item : discs_) expand(item.second);
    current_ = now > 0;
    std::ostringstream report;
    report << "{\"current\":";
    std::ostringstream peers;
    bool first = true;
    for (size_t i = 0; i < ids_.size(); ++i) {
      const auto & id = ids_[i];
      bool live = fresh(edges_.at(id + "/base_link"), now, steady, pose_age_, 0.) &&
        fresh(edges_.at(id + "/odom"), now, steady, localization_age_, future_);
      if (live) {
        try {
          const auto stamp = tf2::TimePoint(std::chrono::nanoseconds(edges_.at(id + "/base_link").stamp));
          // Exact measurement time; latest TF fallback would hide missing history.
          // BufferCore performs a nonblocking lookup. The ROS Buffer wrapper
          // would invoke a wait requiring a dedicated TF thread, which this
          // callback-group-owned buffer deliberately does not have.
          const auto transform = static_cast<tf2::BufferCore &>(*buffer_).lookupTransform(
            layered_costmap_->getGlobalFrameID(), id + "/base_link", stamp);
          const auto & p = transform.transform.translation;
          if (!std::isfinite(p.x) || !std::isfinite(p.y)) live = false;
          else if (id != self_) discs_[id] = Disc{p.x, p.y, radii_[i]};
        } catch (const tf2::TransformException &) {live = false;}
      }
      current_ = current_ && live;
      if (!first) peers << ',';
      first = false;
      peers << "{\"robot_id\":\"" << id << "\",\"live\":" << (live ? "true" : "false")
            << ",\"pose_stamp_ns\":" << edges_.at(id + "/base_link").stamp;
      auto disc = discs_.find(id);
      if (disc != discs_.end()) {
        peers << ",\"x\":" << disc->second.x << ",\"y\":" << disc->second.y
              << ",\"radius\":" << disc->second.radius;
      }
      peers << '}';
    }
    for (const auto & item : discs_) expand(item.second);
    report << (current_ ? "true" : "false") << ",\"frame\":\""
           << layered_costmap_->getGlobalFrameID() << "\",\"stamp_ns\":" << now
           << ",\"robots\":[" << peers.str() << "]}";
    std_msgs::msg::String message;
    message.data = report.str();
    publisher_->publish(message);
  }

  void updateCosts(nav2_costmap_2d::Costmap2D & master, int min_i, int min_j,
    int max_i, int max_j) override
  {
    std::lock_guard<std::mutex> lock(mutex_);
    const double half = master.getResolution() / 2.;
    // Mark every grid square touching the conservative circle, including when
    // its centre is outside a rolling window. Never clear another layer's cost.
    for (const auto & item : discs_) {
      const auto & d = item.second;
      int left, bottom, right, top;
      master.worldToMapEnforceBounds(d.x - d.radius - half, d.y - d.radius - half, left, bottom);
      master.worldToMapEnforceBounds(d.x + d.radius + half, d.y + d.radius + half, right, top);
      for (int y = std::max(min_j, bottom); y < std::min(max_j, top + 1); ++y) {
        for (int x = std::max(min_i, left); x < std::min(max_i, right + 1); ++x) {
          double wx, wy;
          master.mapToWorld(x, y, wx, wy);
          const double dx = std::max(0., std::abs(wx - d.x) - half);
          const double dy = std::max(0., std::abs(wy - d.y) - half);
          if (dx * dx + dy * dy <= d.radius * d.radius) {
            master.setCost(x, y, nav2_costmap_2d::LETHAL_OBSTACLE);
          }
        }
      }
    }
  }
  // Costmap clear/recovery cannot erase an observed robot or certify freshness.
  void reset() override {std::lock_guard<std::mutex> lock(mutex_); current_ = false;}
  bool isClearable() override {return false;}

private:
  static bool positive(double v) {return std::isfinite(v) && v > 0.;}
  bool fresh(const Edge & e, int64_t now, Steady::time_point steady, double age, double lead) const
  {
    return !e.invalid && e.stamp > 0 && now > 0 &&
           static_cast<double>(now - e.stamp) / 1e9 <= age &&
           static_cast<double>(e.stamp - now) / 1e9 <= lead &&
           std::chrono::duration<double>(steady - e.received).count() < transport_;
  }
  void rewind(int64_t now)
  {
    if (last_clock_ > now) {
      buffer_->clear();
      for (auto & item : edges_) {
        item.second.stamp = 0;
        item.second.invalid = true;
      }
      // Last occupied cells remain held until a complete fresh chain exists.
    }
    last_clock_ = now;
  }
  void receive(const tf2_msgs::msg::TFMessage & packet, const std::string & id)
  {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto now = clock_->now().nanoseconds();
    rewind(now);
    for (const auto & transform : packet.transforms) {
      if (transform.child_frame_id != id + "/odom" && transform.child_frame_id != id + "/base_link") continue;
      auto found = edges_.find(transform.child_frame_id);
      if (found == edges_.end()) continue;
      auto & e = found->second;
      const auto & p = transform.transform.translation;
      const auto & q = transform.transform.rotation;
      const auto norm = q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w;
      if (transform.header.frame_id != e.parent || !std::isfinite(p.x) ||
        !std::isfinite(p.y) || !std::isfinite(p.z) || !std::isfinite(norm) ||
        std::abs(norm - 1.) > 1e-3) {
        e.invalid = true;
        continue;
      }
      const int64_t stamp = rclcpp::Time(transform.header.stamp).nanoseconds();
      // Both source time and advancing measurements matter. Duplicates never
      // refresh a receipt deadline, even while the Gazebo clock is paused.
      const bool odom_edge = e.parent == frame_;
      const double lead = odom_edge ? future_ : 0.;
      const double age = odom_edge ? localization_age_ : pose_age_;
      if (stamp <= e.stamp || stamp <= 0 || now <= 0 ||
        double(stamp - now)/1e9 > lead || double(now - stamp)/1e9 > age) continue;
      if (!buffer_->setTransform(transform, "fleet_shared_tf")) {e.invalid = true; continue;}
      e.stamp = stamp;
      e.received = Steady::now();
      e.invalid = false;
    }
  }
  std::mutex mutex_;
  std::vector<std::string> ids_;
  std::vector<double> radii_;
  std::string self_, frame_;
  double pose_age_, transport_, localization_age_, future_;
  int64_t last_clock_{0};
  std::map<std::string, Edge> edges_;
  std::map<std::string, Disc> discs_;
  std::unique_ptr<tf2_ros::Buffer> buffer_;
  std::vector<rclcpp::Subscription<tf2_msgs::msg::TFMessage>::SharedPtr> subscriptions_;
  rclcpp_lifecycle::LifecyclePublisher<std_msgs::msg::String>::SharedPtr publisher_;
};
}  // namespace fleet_perception
PLUGINLIB_EXPORT_CLASS(fleet_perception::PeerRobotLayer, nav2_costmap_2d::Layer)
