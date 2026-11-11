"""Launch the generated warehouse and isolated Nav2 stacks in the Fortress image."""
import argparse
from pathlib import Path
import sys

from fleet_config.warehouse_assets import generate

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "docker/simulation-common"))
from check import emit, gazebo_command
from dock_world import dock_bridge_arguments
from live_processes import bridge_executable, run_simulation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("scenario", choices=("delivery", "passing", "routes"))
    parser.add_argument("--ready", type=Path)
    args = parser.parse_args()
    profile = generate(args.profile, args.output, args.scenario)
    if args.ready is not None:
        args.ready.write_text('READY\n')
    bridge = [bridge_executable(), "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock"]
    for robot in profile.robots:
        ns = robot.namespace
        bridge += [f"{ns}/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan",
                   f"{ns}/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry",
                   f"{ns}/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist"]
        bridge += [f"{ns}/contact_{link}@ros_gz_interfaces/msg/Contacts[ignition.msgs.Contacts"
                   for link in ('base_link', 'left_wheel', 'right_wheel', 'caster')]
    bridge += dock_bridge_arguments(profile.stations.charging_stations, profile.robots)
    commands = [
        ("gazebo", gazebo_command(str(args.output / "warehouse.sdf"))),
        ("bridge", bridge),
        ("tf_helper", [sys.executable, str(Path(__file__).with_name("tf.py")), str(args.profile)]),
    ]
    namespaces = []
    for robot in profile.robots:
        ns = robot.namespace.strip("/")
        namespaces.append(ns)
        commands.append((f"nav2_{robot.id}", [
            "ros2", "launch", "nav2_bringup", "bringup_launch.py",
            "use_sim_time:=True", "autostart:=True", "use_namespace:=True", "namespace:=" + ns,
            "map:=" + str(args.output / "map.yaml"), "params_file:=" + str(args.output / f"nav2-{robot.id}.yaml"),
            "slam:=False", "use_composition:=False",
        ]))
    return run_simulation(commands, namespaces, emit)


if __name__ == "__main__":
    sys.exit(main())
