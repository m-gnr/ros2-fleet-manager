"""Bounded ROS service gateway; imports ROS only when explicitly enabled."""
import asyncio
import math
import os
import threading
import time
from uuid import UUID


class BatteryROSGateway:
    def __init__(self, config):
        self._token = os.environ.get("FLEET_SIM_BATTERY_TOKEN", "")
        if len(self._token) < 32:
            raise ValueError("Battery control gateway requires FLEET_SIM_BATTERY_TOKEN (32+ characters)")
        import rclpy
        from rclpy.context import Context
        from rclpy.executors import SingleThreadedExecutor
        from fleet_interfaces.msg import BatteryState
        from fleet_interfaces.srv import ControlBattery
        self.service_type = ControlBattery
        self.context = Context()
        rclpy.init(args=[], context=self.context)
        self.node = rclpy.create_node("battery_dashboard_gateway", context=self.context)
        self.executor = SingleThreadedExecutor(context=self.context)
        self.executor.add_node(self.node)
        self.clients, self.samples = {}, {}
        self.sample_lock = threading.Lock()
        for robot in config.robots:
            self.clients[robot.id] = self.node.create_client(ControlBattery, robot.namespace + "/sim/control_battery")
            self.node.create_subscription(BatteryState, robot.namespace + "/battery_state",
                                          lambda msg, rid=robot.id: self.observe(rid, msg), 10)
        self.thread = threading.Thread(target=self.executor.spin, daemon=True)
        self.thread.start()

    def observe(self, robot_id, msg):
        with self.sample_lock:
            self.samples[robot_id] = (time.monotonic(), msg)

    def check(self, robot):
        with self.sample_lock:
            sample = self.samples.get(robot.id)
        if sample is None or time.monotonic() - sample[0] > 2:
            raise ValueError("BatteryState telemetry stale or unavailable")
        msg = sample[1]
        if msg.robot_id != robot.id or self.node.count_publishers(robot.namespace + "/battery_state") != 1:
            raise ValueError("Battery publisher ownership ambiguous")
        if not all(math.isfinite(x) for x in (msg.battery_energy_wh, msg.battery_soc_percent, msg.battery_capacity_wh)):
            raise ValueError("Invalid battery telemetry")
        if (msg.battery_capacity_wh <= 0 or not 0 <= msg.battery_soc_percent <= 100 or
                not math.isclose(msg.battery_energy_wh, msg.battery_capacity_wh * msg.battery_soc_percent / 100,
                                 rel_tol=1e-6, abs_tol=1e-6)):
            raise ValueError("Inconsistent battery telemetry")
        service = robot.namespace + "/sim/control_battery"
        servers = sum(service in dict(self.node.get_service_names_and_types_by_node(name, namespace))
                      for name, namespace in self.node.get_node_names_and_namespaces())
        if servers != 1 or not self.clients[robot.id].service_is_ready():
            raise ValueError("Battery control service unavailable or ambiguous")
        return str(UUID(bytes=bytes(msg.publisher_session_id.uuid)))

    async def call(self, robot, **fields):
        session = self.check(robot)
        request = self.service_type.Request(robot_id=robot.id, access_token=self._token, **fields)
        future = self.clients[robot.id].call_async(request)
        try:
            deadline = time.monotonic() + 2
            while not future.done():
                if time.monotonic() >= deadline:
                    raise TimeoutError("Battery service timeout; outcome unknown")
                await asyncio.sleep(.02)
            response = future.result()
            if not response.success:
                raise ValueError(response.message)
            if fields.get("request_id") and response.request_id != fields["request_id"]:
                raise ValueError("Battery request identity mismatch")
            if response.robot_id != robot.id or response.session_id != session or self.check(robot) != session:
                raise ValueError("Battery service identity or session mismatch")
            return {key: getattr(response, key) for key in response.get_fields_and_field_types()}
        finally:
            if not future.done():
                future.cancel()

    async def read(self, robot):
        return await self.call(robot)

    async def apply(self, robot, command, session):
        return await self.call(robot, expected_session_id=session, request_id=command.request_id,
                               set_soc=command.soc_percent is not None, soc_percent=command.soc_percent or 0.,
                               set_profile=command.mode is not None, mode=command.mode or "",
                               discharge_minutes=command.discharge_minutes, charge_minutes=command.charge_minutes)

    def close(self):
        self.executor.shutdown(timeout_sec=3)
        self.thread.join(timeout=3)
        self.node.destroy_node()
        self.context.try_shutdown()
