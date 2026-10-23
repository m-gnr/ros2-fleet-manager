"""A bounded DDS message receipt check, not a fleet component."""

import json
import math
import os
import sys
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String


def main():
    role = os.environ["DDS_ROLE"]
    topic = os.environ["DDS_TEST_TOPIC"]
    payload = os.environ["DDS_TEST_PAYLOAD"]
    timeout = float(os.environ["DDS_TEST_TIMEOUT_SECONDS"])
    period = float(os.environ["DDS_PUBLISH_PERIOD_SECONDS"])
    domain = int(os.environ["ROS_DOMAIN_ID"])
    if role not in ("publisher", "subscriber"):
        raise ValueError("DDS_ROLE must be publisher or subscriber")
    if not topic.startswith("/") or not payload:
        raise ValueError("An absolute topic and a nonempty payload are required")
    if not all(math.isfinite(v) and v > 0 for v in (timeout, period)):
        raise ValueError("Timeout and publish period must be positive finite seconds")
    if not 0 <= domain <= 232:
        raise ValueError("ROS_DOMAIN_ID must be in 0..232")

    rclpy.init()
    node = rclpy.create_node("dds_check_" + role)
    qos = QoSProfile(
        depth=1,
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.VOLATILE,
    )
    matched = False
    print(json.dumps({"event": "START", "role": role, "topic": topic,
                      "rmw": os.environ["RMW_IMPLEMENTATION"], "domain": domain}), flush=True)

    def receive(message):
        nonlocal matched
        if message.data == payload:
            matched = True
            print(json.dumps({"event": "RECEIVED", "topic": topic,
                              "data": message.data}), flush=True)

    if role == "publisher":
        publisher = node.create_publisher(String, topic, qos)

        def publish():
            publisher.publish(String(data=payload))
            print(json.dumps({"event": "PUBLISHED", "topic": topic,
                              "data": payload}), flush=True)

        node.create_timer(period, publish)
    else:
        node.create_subscription(String, topic, receive, qos)

    deadline = time.monotonic() + timeout
    try:
        while rclpy.ok() and not matched:
            if role == "subscriber" and time.monotonic() >= deadline:
                print("FAIL: no matching DDS message received", flush=True)
                return 1
            rclpy.spin_once(node, timeout_sec=0.2)
        return 0 if matched else 1
    except (KeyboardInterrupt, ExternalShutdownException):
        return 0 if role == "publisher" else 1
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
