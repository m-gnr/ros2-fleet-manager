"""Opt-in fake-only wiring. Never imported by the C5-A launcher."""
import re


def topology(namespace):
    if not re.fullmatch(r'/b6b4_test/[a-z][a-z0-9_]*', namespace):
        raise ValueError('Only isolated /b6b4_test/<run> namespaces are allowed')
    return {name: namespace + '/' + suffix for name, suffix in dict(
        controller='upstream/controller', smoother='upstream/smoother',
        behavior='upstream/behavior', executor='upstream/executor',
        alternative='upstream/alternative', envelope='upstream/envelope',
        actuator='actuator_cmd_vel', legacy='cmd_vel',
        ignition='ign_velocity', observed='fake_actuator', diagnostics='gate_diagnostics').items()}


def remappings(namespace):
    """Per-node maps, including the smoother's distinct input/output endpoints."""
    t = topology(namespace)
    return dict(controller=[('cmd_vel', t['controller'])],
                smoother=[('cmd_vel', t['controller']), ('cmd_vel_smoothed', t['smoother'])],
                behavior=[('cmd_vel', t['behavior'])],
                executor=[('cmd_vel', t['executor'])])


def bridge_arguments(namespace):
    t = topology(namespace)
    # Only velocity mapping; fake transport target, no world or DiffDrive is started.
    return ['ros2', 'run', 'ros_gz_bridge', 'parameter_bridge',
            t['ignition'] + '@geometry_msgs/msg/Twist]ignition.msgs.Twist',
            '--ros-args', '-r', t['ignition'] + ':=' + t['actuator'],
            '-r', '__node:=b6b4_velocity_bridge']
