"""Test-only initial energy for the real C4 battery node."""

import argparse
import signal

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.signals import SignalHandlerOptions

from fleet_battery_simulator.node import BatterySimulatorNode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fleet-config", required=True)
    parser.add_argument("--robot-id", required=True)
    parser.add_argument("--initial-soc", type=float, required=True)
    args = parser.parse_args()
    if not 0 <= args.initial_soc <= 100:
        parser.error("initial SoC must be between 0 and 100")

    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    rclpy.init(args=[], signal_handler_options=SignalHandlerOptions.NO)
    node = BatterySimulatorNode.from_config(args.fleet_config, args.robot_id)
    node._battery.remaining_wh = node._battery.capacity_wh * args.initial_soc / 100
    try:
        # Let the current DDS callback finish before destroying the context.
        while not stopping and rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.2)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
