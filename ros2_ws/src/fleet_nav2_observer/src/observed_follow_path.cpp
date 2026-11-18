// Metadata observer only. Loading this plugin does not enforce traffic or qualify stop.
#include <string>
#include <random>
#include "nav2_behavior_tree/plugins/action/follow_path_action.hpp"
#include "behaviortree_cpp_v3/bt_factory.h"
#include "fleet_interfaces/msg/traffic_child_observation.hpp"

namespace fleet_nav2_observer
{
using Message = fleet_interfaces::msg::TrafficChildObservation;

unique_identifier_msgs::msg::UUID uuid(const std::string & value)
{
  unique_identifier_msgs::msg::UUID out;
  std::string digits;
  for (auto c : value) {if (c != '-') {digits += c;}}
  if (digits.size() != 32 || digits.find_first_not_of("0123456789abcdef") != std::string::npos) {
    throw std::runtime_error("Explicit canonical UUID required");
  }
  for (size_t i = 0; i < 16; ++i) {out.uuid[i] = std::stoul(digits.substr(i * 2, 2), nullptr, 16);}
  if (out.uuid == unique_identifier_msgs::msg::UUID().uuid) {throw std::runtime_error("Zero UUID");}
  return out;
}

class ObservedFollowPath : public nav2_behavior_tree::FollowPathAction
{
public:
  ObservedFollowPath(const std::string & name, const BT::NodeConfiguration & conf)
  : FollowPathAction(name, "follow_path", conf)
  {
    std::string context, nav, session;
    if (!getInput("context_id", context) || !getInput("nav_goal_uuid", nav) ||
      !getInput("executor_session", session)) {throw std::runtime_error("Missing parent context");}
    base_.context_id = uuid(context);
    base_.nav_goal_uuid = uuid(nav);
    base_.executor_session_id = uuid(session);
    std::random_device random;
    for (auto & byte : base_.observer_session_id.uuid) {byte = static_cast<uint8_t>(random());}
    base_.observer_session_id.uuid[6] = (base_.observer_session_id.uuid[6] & 0x0f) | 0x40;
    base_.observer_session_id.uuid[8] = (base_.observer_session_id.uuid[8] & 0x3f) | 0x80;
    publisher_ = node_->create_publisher<Message>("traffic_child_observation", 32);
  }

  static BT::PortsList providedPorts()
  {
    auto ports = FollowPathAction::providedPorts();
    ports.insert(BT::InputPort<std::string>("context_id"));
    ports.insert(BT::InputPort<std::string>("nav_goal_uuid"));
    ports.insert(BT::InputPort<std::string>("executor_session"));
    return ports;
  }

  void on_tick() override
  {
    FollowPathAction::on_tick();
    pending_path_ = goal_.path;  // Exact immutable copy before async_send_goal.
  }

  void accepted()
  {
    if (!goal_handle_ || (observed_ && child_ == goal_handle_->get_goal_id())) {return;}
    child_ = goal_handle_->get_goal_id();
    observed_ = true;
    accepted_path_ = pending_path_;
    emit(Message::ACCEPTED, 0, "CLIENT_GOAL_HANDLE_ACCEPTED");
  }

  void on_wait_for_result(std::shared_ptr<const nav2_msgs::action::FollowPath::Feedback> feedback) override
  {
    accepted();
    FollowPathAction::on_wait_for_result(feedback);
    if (goal_updated_) {
      emit(Message::INVALIDATED, 0, "PATH_OR_CONTROLLER_REPLACED");
      pending_path_ = goal_.path;
    }
  }

  BT::NodeStatus on_success() override {return terminal(4);}
  BT::NodeStatus on_aborted() override {return terminal(6);}
  BT::NodeStatus on_cancelled() override
  {
    // Base halt invokes on_cancelled even when cancel/result waits fail.
    // Only tick's actual matching result is allowed to report a terminal.
    if (halting_) {return BT::NodeStatus::SUCCESS;}
    return terminal(5);
  }
  void halt() override
  {
    if (observed_) {emit(Message::INVALIDATED, 0, "BT_HALTED");}
    halting_ = true;
    FollowPathAction::halt();
    halting_ = false;
  }

private:
  BT::NodeStatus terminal(int status)
  {
    accepted();  // Includes a goal that completed before the next waiting tick.
    if (observed_) {emit(Message::TERMINAL, status, "MATCHING_ACTION_RESULT");}
    return status == 6 ? BT::NodeStatus::FAILURE : BT::NodeStatus::SUCCESS;
  }
  void emit(uint8_t kind, int8_t terminal_status, const std::string & reason)
  {
    auto message = base_;
    message.child_goal_uuid.uuid = child_;
    message.observation_seq = ++sequence_;
    message.stamp = node_->now();
    message.kind = kind;
    message.terminal_status = terminal_status;
    message.reason = reason;
    message.path = accepted_path_;
    publisher_->publish(message);
  }
  Message base_;
  nav_msgs::msg::Path pending_path_, accepted_path_;
  rclcpp_action::GoalUUID child_{};
  uint64_t sequence_{0};
  bool observed_{false}, halting_{false};
  rclcpp::Publisher<Message>::SharedPtr publisher_;
};
}  // namespace fleet_nav2_observer

BT_REGISTER_NODES(factory)
{
  factory.registerNodeType<fleet_nav2_observer::ObservedFollowPath>("FleetObservedFollowPath");
}
