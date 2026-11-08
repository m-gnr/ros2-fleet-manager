"""Relay Gazebo odometry and namespace-local AMCL transforms."""
import signal
import sys

from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
import rclpy
from rclpy.qos import DurabilityPolicy, QoSProfile
from rclpy.signals import SignalHandlerOptions
from tf2_msgs.msg import TFMessage

from fleet_config import load_config


def main():
    profile = load_config(sys.argv[1])
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = rclpy.create_node("warehouse_tf")
    qos = QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    shared = node.create_publisher(TFMessage, "/tf", 30)
    static = node.create_publisher(TFMessage, "/tf_static", qos)
    for robot in profile.robots:
        ns = robot.namespace
        tf = node.create_publisher(TFMessage, ns + "/tf", 10)
        local_static = node.create_publisher(TFMessage, ns + "/tf_static", qos)

        def odom(message, publisher=tf):
            transform = TransformStamped(header=message.header, child_frame_id=message.child_frame_id)
            transform.transform.translation.x = message.pose.pose.position.x
            transform.transform.translation.y = message.pose.pose.position.y
            transform.transform.translation.z = message.pose.pose.position.z
            transform.transform.rotation = message.pose.pose.orientation
            packet = TFMessage(transforms=[transform])
            publisher.publish(packet)
            shared.publish(packet)

        def relay(message):
            transforms = [item for item in message.transforms if item.header.frame_id == "map"]
            if transforms:
                shared.publish(TFMessage(transforms=transforms))

        link = TransformStamped()
        link.header.frame_id = f"{robot.id}/base_link"
        link.child_frame_id = f"{robot.id}/base_link/lidar"
        link.transform.translation.z = .15
        link.transform.rotation.w = 1.
        packet = TFMessage(transforms=[link])

        def publish_static(publisher=local_static, transform=packet):
            publisher.publish(transform)
            static.publish(transform)

        publish_static()
        node.create_timer(1., publish_static)
        node.create_subscription(Odometry, ns + "/odom", odom, 10)
        node.create_subscription(TFMessage, ns + "/tf", relay, 10)
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        while rclpy.ok() and not stopping:
            rclpy.spin_once(node, timeout_sec=.2)
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
