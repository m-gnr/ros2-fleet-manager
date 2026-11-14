#include <algorithm>
#include <iomanip>
#include <random>
#include <sstream>
#include "nav2_costmap_2d/obstacle_layer.hpp"
#include "pluginlib/class_list_macros.hpp"
#include "fleet_interfaces/msg/observation_health.hpp"

namespace fleet_perception
{
class ObservedObstacleLayer : public nav2_costmap_2d::ObstacleLayer
{
public:
  void onInitialize() override
  {
    nav2_costmap_2d::ObstacleLayer::onInitialize();
    auto node = node_.lock();
    if (!node) throw std::runtime_error("Costmap lifecycle node unavailable");
    std::random_device random;
    std::ostringstream session;
    for (int i = 0; i < 4; ++i) session << std::hex << std::setw(8) << std::setfill('0') << random();
    session_ = session.str();
    std::string sources;
    node->get_parameter(name_ + ".observation_sources", sources);
    std::istringstream names(sources);
    std::string source;
    while (names >> source) {
      std::string topic;
      node->get_parameter(name_ + "." + source + ".topic", topic);
      topics_.push_back(topic);
    }
    if (topics_.size() != observation_buffers_.size())
      throw std::runtime_error("Observation source/buffer mapping mismatch");
    publisher_ = node->create_publisher<fleet_interfaces::msg::ObservationHealth>(
      "perception_observations", rclcpp::SensorDataQoS());
    publisher_->on_activate();
  }

  void updateBounds(double x, double y, double yaw, double * min_x, double * min_y,
                    double * max_x, double * max_y) override
  {
    // Recursive buffer locks are the same locks used by the Nav2 callbacks.
    // Keep every buffer stable across the real layer computation and snapshot.
    struct LockedBuffers {
      std::vector<std::shared_ptr<nav2_costmap_2d::ObservationBuffer>> buffers;
      explicit LockedBuffers(decltype(buffers) value) : buffers(std::move(value)) {
        for (auto & buffer : buffers) buffer->lock();
      }
      ~LockedBuffers() { for (auto it = buffers.rbegin(); it != buffers.rend(); ++it) (*it)->unlock(); }
    } locked(observation_buffers_);
    nav2_costmap_2d::ObstacleLayer::updateBounds(x, y, yaw, min_x, min_y, max_x, max_y);
    fleet_interfaces::msg::ObservationHealth report;
    report.layer_session = session_;
    report.sequence = ++sequence_;
    report.processed_at = clock_->now();
    report.topics = topics_;
    for (auto & buffer : observation_buffers_) {
      std::vector<nav2_costmap_2d::Observation> observations;
      buffer->getObservations(observations);
      builtin_interfaces::msg::Time stamp;
      const bool participates =
        std::find(marking_buffers_.begin(), marking_buffers_.end(), buffer) != marking_buffers_.end() ||
        std::find(clearing_buffers_.begin(), clearing_buffers_.end(), buffer) != clearing_buffers_.end();
      bool used = enabled_ && current_ && participates && !observations.empty();
      for (auto & observation : observations) {
        if (observation.cloud_->header.frame_id != global_frame_) used = false;
        // Persistence > 0 gives multiple measurements, so do not claim a
        // single measurement identity in that unsupported configuration.
        stamp = observation.cloud_->header.stamp;
      }
      used = used && observations.size() == 1;
      report.measurement_stamps.push_back(stamp);
      report.used.push_back(used);
    }
    publisher_->publish(report);
  }
private:
  std::string session_;
  uint64_t sequence_{0};
  std::vector<std::string> topics_;
  rclcpp_lifecycle::LifecyclePublisher<fleet_interfaces::msg::ObservationHealth>::SharedPtr publisher_;
};
}
PLUGINLIB_EXPORT_CLASS(fleet_perception::ObservedObstacleLayer, nav2_costmap_2d::Layer)
