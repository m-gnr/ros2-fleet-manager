#!/usr/bin/env python3
"""Stage C3.3.3 Temporary Test Battery Feeder (pre-C4).

Strict compliance with C3.3.3-DEC-03:
- Exists strictly for simulation test harness to supply battery state to executors.
- NEVER presented as the real Battery Simulator or physical authority.
- DOC-ARCH Section 7 single authority will be implemented in Stage C4.
"""

import sys
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from fleet_interfaces.msg import RobotStatus


class MockBatteryFeeder(Node):
    def __init__(self, robot_ids=("robot_1", "robot_2")):
        super().__init__("c3_3_3_mock_battery_feeder")
        self.set_parameters([Parameter("use_sim_time", Parameter.Type.BOOL, True)])
        self.robot_ids = robot_ids
        self.pubs = {
            r_id: self.create_publisher(RobotStatus, f"/{r_id}/battery_state", 10)
            for r_id in self.robot_ids
        }
        self.timer = self.create_timer(1.0, self._publish_battery)
        self.get_logger().info(f"Initialized mock battery feeder for {self.robot_ids}")

    def _publish_battery(self):
        stamp = self.get_clock().now().to_msg()
        for r_id, pub in self.pubs.items():
            msg = RobotStatus()
            msg.robot_id = r_id
            msg.battery_soc_percent = 100.0
            msg.battery_energy_wh = 100.0
            msg.header.stamp = stamp
            pub.publish(msg)


def main():
    rclpy.init()
    node = MockBatteryFeeder()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
