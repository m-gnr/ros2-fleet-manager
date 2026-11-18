"""Trusted fixture process sending authenticated zero commands; no motion enable."""
import argparse
import hashlib
import hmac
import json
from pathlib import Path
import time

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from std_msgs.msg import String


def wire(body, key):
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return json.dumps(dict(body=raw, mac=hmac.new(key, raw.encode(), hashlib.sha256).hexdigest()))


def body(provision, state, sequence):
    return dict(source_session=provision["source_session"], actuator_session=state["actuator_session"],
        command_sequence=sequence, permit_id=provision["permit_id"], permit_generation=provision["generation"],
        command_context=provision["context"], ticket=state["ticket"],
        issued_at=dict(clock="source_monotonic", value=time.monotonic()), velocity=[0.]*6)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--provision", type=Path, required=True)
    args = parser.parse_args()
    provision = json.loads(args.provision.read_text())
    key = bytes.fromhex(provision.pop("key_hex"))
    rclpy.init()
    node = rclpy.create_node("authenticated_zero_producer")
    qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.VOLATILE)
    publisher = node.create_publisher(String, args.namespace + "/authorized_zero", qos)
    latest, sent_ticket, sequence = None, None, 0

    def state(message):
        nonlocal latest
        latest = (json.loads(message.data), time.monotonic())

    def send():
        nonlocal sequence, sent_ticket
        if latest is None or time.monotonic()-latest[1] >= .15:
            return
        report = latest[0]
        if report["state"] not in ("NO_COMMAND", "ACTIVE") or report["ticket"] == sent_ticket:
            return
        sequence += 1
        message = String(data=wire(body(provision, report, sequence), key))
        publisher.publish(message)
        sent_ticket = report["ticket"]
        print(json.dumps(dict(event="ZERO_SENT", sequence=sequence)), flush=True)

    node.create_subscription(String, args.namespace + "/native_actuator", state, qos)
    node.create_timer(.03, send, clock=Clock(clock_type=ClockType.STEADY_TIME))
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
