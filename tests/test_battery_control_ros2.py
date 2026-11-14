"""Isolated real ROS services; synthetic third robot is not a Gazebo acceptance."""
import asyncio
import os
import threading
import time

import pytest

rclpy = pytest.importorskip('rclpy')
from rclpy.executors import SingleThreadedExecutor
from rosgraph_msgs.msg import Clock
from fleet_interfaces.srv import ControlBattery
from fleet_battery_simulator.node import BatterySimulatorNode
from backend.dashboard.battery_ros import BatteryROSGateway
from backend.dashboard.battery_control import BatteryControls
from test_battery_control import config_three, command, TOKEN


def test_default_disabled_and_service_auth_boundary(monkeypatch):
    monkeypatch.delenv('FLEET_SIM_BATTERY_CONTROL', raising=False)
    config = config_three()
    rclpy.init(args=[])
    node = BatterySimulatorNode(config.robots[0], config.fleet.battery_models[config.robots[0].battery_model])
    try:
        assert not any(name.endswith('/sim/control_battery') for name, _ in node.get_service_names_and_types())
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
    monkeypatch.setenv('FLEET_SIM_BATTERY_CONTROL', '1')
    monkeypatch.delenv('FLEET_SIM_BATTERY_TOKEN', raising=False)
    with pytest.raises(ValueError, match='FLEET_SIM_BATTERY_TOKEN'):
        BatterySimulatorNode(config.robots[0], config.fleet.battery_models[config.robots[0].battery_model])


def test_three_real_simulators_services_readback_and_disconnect(monkeypatch):
    monkeypatch.setenv('FLEET_SIM_BATTERY_CONTROL', '1')
    monkeypatch.setenv('ROS_LOCALHOST_ONLY', '1')
    monkeypatch.setenv('FLEET_SIM_BATTERY_TOKEN', TOKEN)
    config = config_three()
    rclpy.init(args=[])
    probe = rclpy.create_node('battery_control_probe')
    nodes = [BatterySimulatorNode(robot, config.fleet.battery_models[robot.battery_model]) for robot in config.robots]
    executor = SingleThreadedExecutor()
    for node in [probe, *nodes]:
        executor.add_node(node)
    publisher = probe.create_publisher(Clock, '/clock', 10)
    counter = [0]
    def tick():
        counter[0] += 100_000_000
        message = Clock()
        message.clock.sec, message.clock.nanosec = divmod(counter[0], 1_000_000_000)
        publisher.publish(message)
    probe.create_timer(.1, tick)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    gateway = BatteryROSGateway(config)
    controls = BatteryControls(config, gateway)

    async def run():
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            inventory = await controls.inventory()
            if all(r['available'] for r in inventory['robots']):
                break
            await asyncio.sleep(.2)
        assert all(r['available'] for r in inventory['robots']), inventory
        sessions = {r['robot_id']: r['state']['session_id'] for r in inventory['robots']}
        from backend.dashboard.battery_control import BatteryCommand
        cmd = BatteryCommand(request_id='real-ros-bulk', all_robots=True, confirm_bulk_soc=True,
            safe_test_environment=True, sessions=sessions, soc_percent=25., mode='FAST')
        result = await controls.apply(cmd)
        assert result['all_verified'], result
        assert len(result['results']) == 3
        assert all(r['readback']['idle_power_w'] == 450. for r in result['results'])
        assert all(r['readback']['charge_power_w'] == 780. for r in result['results'])
        # Retry is an idempotent acknowledgement, not a second SoC reset.
        revision = nodes[0]._battery.revision
        response = await gateway.apply(config.robots[0], cmd, sessions[config.robots[0].id])
        assert response['revision'] == revision and response['message'].startswith('DUPLICATE')
        # Same namespace with a wrong request robot ID is explicitly rejected.
        client = gateway.clients[config.robots[0].id]
        future = client.call_async(ControlBattery.Request(robot_id='wrong_robot', access_token=TOKEN))
        deadline = time.monotonic() + 3
        while not future.done() and time.monotonic() < deadline:
            await asyncio.sleep(.02)
        assert future.done() and not future.result().success
        async def direct(**kwargs):
            f = client.call_async(ControlBattery.Request(robot_id=config.robots[0].id, access_token=kwargs.pop('access_token', TOKEN), **kwargs))
            deadline = time.monotonic() + 3
            while not f.done() and time.monotonic() < deadline:
                await asyncio.sleep(.02)
            assert f.done()
            return f.result()
        rejected = await direct(access_token='wrong-token')
        assert not rejected.success and 'authentication' in rejected.message
        rejected = await direct(set_soc=True, soc_percent=80., request_id='wrong-session', expected_session_id='old')
        assert not rejected.success
        rejected = await direct(set_soc=True, soc_percent=101., request_id='range', expected_session_id=sessions[config.robots[0].id])
        assert not rejected.success
        rejected = await direct(set_soc=True, soc_percent=80., request_id=cmd.request_id, expected_session_id=sessions[config.robots[0].id])
        assert not rejected.success and 'different parameters' in rejected.message
        # Remove the third simulator. The other two must remain controllable.
        executor.remove_node(nodes[2])
        nodes[2].destroy_node()
        nodes.pop()
        await asyncio.sleep(2.2)
        after = await controls.inventory()
        assert [r['available'] for r in after['robots']] == [True, True, False]
        result = await controls.apply(cmd.model_copy(update={'request_id': 'partial-ros', 'soc_percent': 80.}))
        assert [r['outcome'] for r in result['results']] == ['VERIFIED', 'VERIFIED', 'REJECTED']
    try:
        asyncio.run(run())
    finally:
        gateway.close()
        executor.shutdown(timeout_sec=3)
        thread.join(timeout=3)
        for node in [probe, *nodes]:
            node.destroy_node()
        rclpy.try_shutdown()
