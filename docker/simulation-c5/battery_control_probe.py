"""Isolated ROS/Chrome probe, not a Gazebo or Fleet Manager acceptance runner.

Publishes a controlled /clock and forwards real BatteryState to a clearly
identified test snapshot. No RobotStatus, assignments, station leases or
physical dock evidence is fabricated.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import signal
import time
from uuid import uuid4

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rosgraph_msgs.msg import Clock
from fleet_interfaces.msg import BatteryState
from fleet_config import load_config
from fleet_battery_simulator.node import BatterySimulatorNode
from backend.dashboard.models import FleetSnapshot, Robot, SourceSnapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fleet', required=True)
    parser.add_argument('--snapshot', type=Path, required=True)
    args = parser.parse_args()
    config = load_config(args.fleet)
    rclpy.init(args=[])
    probe = rclpy.create_node('battery_control_clock_probe')
    nodes = [BatterySimulatorNode(robot, config.fleet.battery_models[robot.battery_model],
                                 docks=config.stations.charging_stations) for robot in config.robots]
    executor = SingleThreadedExecutor()
    for node in [probe, *nodes]:
        executor.add_node(node)
    samples = {}
    for robot in config.robots:
        probe.create_subscription(BatteryState, robot.namespace + '/battery_state',
                                  lambda msg, rid=robot.id: samples.update({rid: (time.monotonic(), msg)}), 10)
    clock = probe.create_publisher(Clock, '/clock', 10)
    sim_ns = 0
    sequence = 0
    source_session = str(uuid4())
    stop = False
    def stopping(*_):
        nonlocal stop
        stop = True
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, stopping)
    next_tick = time.monotonic()
    try:
        while not stop:
            executor.spin_once(timeout_sec=.01)
            if time.monotonic() < next_tick:
                continue
            next_tick += .1
            sim_ns += 100_000_000
            msg = Clock()
            msg.clock.sec, msg.clock.nanosec = divmod(sim_ns, 1_000_000_000)
            clock.publish(msg)
            sequence += 1
            robots = []
            for robot in config.robots:
                sample = samples.get(robot.id)
                fresh = sample and time.monotonic() - sample[0] <= 2
                battery = sample[1] if fresh else None
                robots.append(Robot(robot_id=robot.id, state=None, telemetry='NO_DATA', initial_status_verified=False,
                    status_sim_ns=None, status_age_sec=None, pose=None, pose_sim_ns=None, pose_reliability='NO_DATA',
                    battery_reliability='LIVE' if battery else 'NO_DATA', battery_soc_percent=battery.battery_soc_percent if battery else None,
                    battery_energy_wh=battery.battery_energy_wh if battery else None,
                    battery_sim_ns=str(battery.battery_stamp.sec * 1_000_000_000 + battery.battery_stamp.nanosec) if battery else None,
                    charging='NOT_CHARGING' if battery else 'UNAVAILABLE', charging_station_id=None, active_task_id=None))
            snapshot = SourceSnapshot(captured_monotonic_ns=time.monotonic_ns(), fleet=FleetSnapshot(
                source_session_id=source_session, sequence=sequence,
                generated_at_utc=datetime.now(timezone.utc), robots=tuple(robots), tasks=(), stations=(),
                task_counts=dict(total=0, active=0, queued=0)))
            temporary = args.snapshot.with_suffix('.tmp')
            temporary.write_text(snapshot.model_dump_json())
            temporary.replace(args.snapshot)
    finally:
        executor.shutdown()
        for node in [probe, *nodes]:
            node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
