#!/usr/bin/env python3
"""TF helper for Stage B3: dual-robot odometry, namespaced TF, and global relay.
Publishes transforms to:
- /robot_1/tf, /robot_1/tf_static
- /robot_2/tf, /robot_2/tf_static
- /tf, /tf_static (unified global tree)
"""
import sys
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_msgs.msg import TFMessage


class DualRobotTfHelper(Node):
    def __init__(self):
        super().__init__('b3_tf_helper')
        self.set_parameters([Parameter('use_sim_time', Parameter.Type.BOOL, True)])

        # QoS for static transforms (TRANSIENT_LOCAL)
        static_qos = QoSProfile(
            depth=10,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE
        )

        # Static TF publishers
        self.pub_static_r1 = self.create_publisher(TFMessage, '/robot_1/tf_static', static_qos)
        self.pub_static_r2 = self.create_publisher(TFMessage, '/robot_2/tf_static', static_qos)
        self.pub_static_root = self.create_publisher(TFMessage, '/tf_static', static_qos)

        # Dynamic TF publishers
        self.pub_tf_r1 = self.create_publisher(TFMessage, '/robot_1/tf', 10)
        self.pub_tf_r2 = self.create_publisher(TFMessage, '/robot_2/tf', 10)
        self.pub_tf_root = self.create_publisher(TFMessage, '/tf', 10)

        # Build static transforms for both robots
        self.static_msgs = self._build_static_transforms()
        self._publish_static()

        # Timer to periodically resend static transforms (prevents race conditions with late-starting costmaps)
        self.create_timer(1.0, self._publish_static)

        # Subscriptions to robot odometry
        self.sub_odom1 = self.create_subscription(Odometry, '/robot_1/odom', self.odom1_cb, 10)
        self.sub_odom2 = self.create_subscription(Odometry, '/robot_2/odom', self.odom2_cb, 10)

        # Subscriptions to namespaced /tf to relay AMCL map->odom to root /tf
        self.sub_tf_r1 = self.create_subscription(TFMessage, '/robot_1/tf', self.tf_r1_cb, 10)
        self.sub_tf_r2 = self.create_subscription(TFMessage, '/robot_2/tf', self.tf_r2_cb, 10)

    def _build_static_transforms(self):
        t1 = TransformStamped()
        t1.header.frame_id = 'robot_1/base_link'
        t1.child_frame_id = 'robot_1/base_link/lidar'
        t1.transform.translation.x = 0.0
        t1.transform.translation.y = 0.0
        t1.transform.translation.z = 0.15
        t1.transform.rotation.w = 1.0

        t2 = TransformStamped()
        t2.header.frame_id = 'robot_2/base_link'
        t2.child_frame_id = 'robot_2/base_link/lidar'
        t2.transform.translation.x = 0.0
        t2.transform.translation.y = 0.0
        t2.transform.translation.z = 0.15
        t2.transform.rotation.w = 1.0

        return {'r1': [t1], 'r2': [t2], 'all': [t1, t2]}

    def _publish_static(self):
        now = self.get_clock().now().to_msg()
        for t in self.static_msgs['all']:
            t.header.stamp = now

        self.pub_static_r1.publish(TFMessage(transforms=self.static_msgs['r1']))
        self.pub_static_r2.publish(TFMessage(transforms=self.static_msgs['r2']))
        self.pub_static_root.publish(TFMessage(transforms=self.static_msgs['all']))

    def odom1_cb(self, msg: Odometry):
        t = TransformStamped()
        t.header.stamp = msg.header.stamp
        t.header.frame_id = 'robot_1/odom'
        t.child_frame_id = 'robot_1/base_link'
        t.transform.translation.x = msg.pose.pose.position.x
        t.transform.translation.y = msg.pose.pose.position.y
        t.transform.translation.z = msg.pose.pose.position.z
        t.transform.rotation = msg.pose.pose.orientation

        tf_msg = TFMessage(transforms=[t])
        self.pub_tf_r1.publish(tf_msg)
        self.pub_tf_root.publish(tf_msg)

    def odom2_cb(self, msg: Odometry):
        t = TransformStamped()
        t.header.stamp = msg.header.stamp
        t.header.frame_id = 'robot_2/odom'
        t.child_frame_id = 'robot_2/base_link'
        t.transform.translation.x = msg.pose.pose.position.x
        t.transform.translation.y = msg.pose.pose.position.y
        t.transform.translation.z = msg.pose.pose.position.z
        t.transform.rotation = msg.pose.pose.orientation

        tf_msg = TFMessage(transforms=[t])
        self.pub_tf_r2.publish(tf_msg)
        self.pub_tf_root.publish(tf_msg)

    def tf_r1_cb(self, msg: TFMessage):
        # Relay map->robot_1/odom transforms from AMCL to root /tf
        amcl_transforms = [t for t in msg.transforms if t.header.frame_id == 'map']
        if amcl_transforms:
            self.pub_tf_root.publish(TFMessage(transforms=amcl_transforms))

    def tf_r2_cb(self, msg: TFMessage):
        # Relay map->robot_2/odom transforms from AMCL to root /tf
        amcl_transforms = [t for t in msg.transforms if t.header.frame_id == 'map']
        if amcl_transforms:
            self.pub_tf_root.publish(TFMessage(transforms=amcl_transforms))


def main():
    rclpy.init()
    node = DualRobotTfHelper()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
