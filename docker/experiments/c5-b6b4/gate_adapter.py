"""ROS adapter for zero-only experiments, not a product safety interlock."""
import argparse
import json
import time

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from fleet_robot_executor.motion_gate import TrafficMotionGate
from topology import topology

QOS = QoSProfile(depth=1, durability=DurabilityPolicy.VOLATILE,
                 reliability=ReliabilityPolicy.RELIABLE)


def axes(msg):
    return tuple(getattr(v, a) for v in (msg.linear, msg.angular) for a in ('x', 'y', 'z'))


class TrafficGateNode(Node):
    def __init__(self, namespace):
        super().__init__('traffic_motion_gate', namespace=namespace)
        self.topics = topology(namespace)
        self.model = TrafficMotionGate(clock=time.monotonic, producer='b6b4_ros')
        self.sequences = {}
        self.last_reasons = ('STARTUP_DENY_ALL', 'NONZERO_DISABLED')
        self.output = self.create_publisher(Twist, self.topics['actuator'], QOS)
        self.diagnostics = self.create_publisher(String, self.topics['diagnostics'], QOS)
        self.inputs = [self.create_subscription(Twist, self.topics[source],
                       lambda msg, source=source: self.raw(msg, source), QOS)
                       for source in ('smoother', 'behavior', 'executor', 'alternative')]
        self.envelopes = self.create_subscription(String, self.topics['envelope'], self.envelope, QOS)
        self.timer = self.create_timer(.05, self.heartbeat, clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.heartbeat()

    def emit(self, reasons):
        self.last_reasons = tuple(reasons)
        # Deliberate second zero-only boundary; never serialize incoming/model velocity.
        self.output.publish(Twist())
        self.diagnostics.publish(String(data=json.dumps(dict(
            session=self.model.local_session, reasons=self.last_reasons,
            physical_stop='UNKNOWN', ownership_release=False, nonzero_enabled=False))))

    def raw(self, msg, source):
        try:
            result = self.model.filter_velocity(axes(msg), producer='b6b4_ros')
            # Twist has neither a source stamp nor session/context/sequence proof.
            self.emit(('UNBOUND_TWIST', source, *result.reasons))
        except Exception:
            self.model.revoke('ADAPTER_ERROR')
            self.emit(('ADAPTER_ERROR', 'NONZERO_DISABLED'))

    def envelope(self, msg):
        """Diagnostic test envelope only. Identity fields are NOT authentication."""
        try:
            value = json.loads(msg.data)
            if not isinstance(value, dict):
                raise ValueError('object required')
            if value.get('gate_session') != self.model.local_session:
                self.emit(('OLD_GATE_SESSION', 'NONZERO_DISABLED'))
                return
            source, seq = value.get('source'), value.get('sequence')
            if source not in ('smoother', 'behavior', 'executor') or type(seq) is not int or seq < 1:
                raise ValueError('source/sequence required')
            if seq <= self.sequences.get(source, 0):
                self.emit(('OLD_OR_DUPLICATE_COMMAND', 'NONZERO_DISABLED'))
                return
            self.sequences[source] = seq
            result = self.model.filter_velocity(value.get('velocity'), producer='b6b4_ros',
                                                context=value.get('context'))
            # No ROS endpoint accepts caller-asserted health, permit or applied evidence.
            self.emit(result.reasons)
        except (ValueError, TypeError, KeyError):
            self.model.revoke('MALFORMED_ENVELOPE')
            self.emit(('MALFORMED_ENVELOPE', 'NONZERO_DISABLED'))

    def heartbeat(self):
        try:
            context = self.model.binding['context'] if self.model.binding else None
            result = self.model.filter_velocity((0.,) * 6, producer='b6b4_ros', context=context)
            self.emit((*self.last_reasons, *[r for r in result.reasons if r not in self.last_reasons]))
        except Exception:
            self.model.revoke('ADAPTER_ERROR')
            self.emit(('ADAPTER_ERROR', 'NONZERO_DISABLED'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--namespace', required=True)
    args = parser.parse_args()
    topology(args.namespace)
    rclpy.init(args=[])
    node = TrafficGateNode(args.namespace)
    try:
        rclpy.spin(node)
    finally:
        node.emit(('SHUTDOWN', 'NONZERO_DISABLED'))
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
