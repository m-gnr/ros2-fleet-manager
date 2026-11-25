// Dependency lifetime regression only; no robot topic or movement permission.
#include <rclcpp/rclcpp.hpp>
#include <ros_gz_bridge/ros_gz_bridge.hpp>
#include <iostream>

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);bool passed=true;
  for(auto direction:{ros_gz_bridge::BridgeDirection::ROS_TO_GZ,ros_gz_bridge::BridgeDirection::GZ_TO_ROS}) {
    auto node=std::make_shared<ros_gz_bridge::RosGzBridge>();
    std::weak_ptr<ros_gz_bridge::RosGzBridge> owner=node;
    ros_gz_bridge::BridgeConfig config;
    config.ros_topic_name=config.gz_topic_name="/c5_1b_dependency_lifetime";
    config.ros_type_name="std_msgs/msg/String";config.gz_type_name="ignition.msgs.StringMsg";config.direction=direction;
    node->add_bridge(config);
    auto references=node.use_count();node.reset();
    std::cout<<"direction="<<int(direction)<<" references_before_reset="<<references<<" expired="<<owner.expired()<<std::endl;
    passed=passed&&owner.expired();
  }
  rclcpp::shutdown();return passed?0:1;
}
