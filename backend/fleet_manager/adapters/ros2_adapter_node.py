"""Fleet Manager ROS 2 Node coordinating robot adapters and middleware bridges.

Conforms strictly to:
- DOC-ARCH-2026-10-23-FINAL Section 5 & 11: Three-service layout, namespace isolation per robot.
- C3.3.2-DEC-06: Asynchronous rclpy thread pool bridged thread-safely to single asyncio consumer.
- Config-driven dynamic robot endpoints from fleet specification.
"""

import asyncio
import logging
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FleetROS2Adapter:
    """Coordinates ROS 2 subscriptions, action clients, service clients, and route resolvers."""

    def __init__(
        self,
        node: Any,
        consumer: Any,
        loop: asyncio.AbstractEventLoop,
        robot_ids: List[str],
        route_cache: Optional[Any] = None,
        *,
        robot_namespaces: Optional[Dict[str, str]] = None,
        enable_live_routing: bool = True,
    ) -> None:
        self.node = node
        self.consumer = consumer
        self.loop = loop
        self.robot_ids = robot_ids
        self.robot_namespaces = (
            {robot_id: f"/{robot_id}" for robot_id in robot_ids}
            if robot_namespaces is None else robot_namespaces
        )
        if set(self.robot_namespaces) != set(robot_ids):
            raise ValueError("Robot namespace mapping must cover the configured robot IDs")

        from .action_client import ExecuteTaskActionClientBridge
        from .outbox_sender import ROS2OutboxSender
        from .route_cache import CachedRouteDistanceProvider, RouteCache
        from .route_resolver import AsyncRouteResolver
        from .service_client import ClearRobotErrorServiceClient
        from .status_subscriber import RobotStatusSubscriberBridge

        provider = consumer.core.scheduler.route_provider
        if isinstance(provider, CachedRouteDistanceProvider):
            if route_cache is not None and route_cache is not provider.cache:
                raise ValueError("ROS adapter and Scheduler must share the same route cache")
            route_cache = provider.cache
        self.route_cache = route_cache if route_cache is not None else RouteCache()
        self.route_resolver = AsyncRouteResolver(cache=self.route_cache)

        self.status_bridges: Dict[str, RobotStatusSubscriberBridge] = {}
        self.action_bridges: Dict[str, ExecuteTaskActionClientBridge] = {}
        self.service_clients: Dict[str, ClearRobotErrorServiceClient] = {}
        self.outbox_sender = ROS2OutboxSender(action_clients=self.action_bridges)

        self._battery_clock_ns = None
        if node is not None and any(robot.requires_battery_telemetry for robot in consumer.core.tracker.list_robots()):
            from rclpy.clock import JumpThreshold
            from rclpy.duration import Duration

            if not node.get_parameter("use_sim_time").value:
                raise ValueError("Fleet battery telemetry requires use_sim_time=true")
            clock = node.get_clock()
            clock_changed = threading.Event()
            self._battery_clock_guard = clock.create_jump_callback(
                JumpThreshold(min_forward=None, min_backward=Duration(nanoseconds=-1), on_clock_change=True),
                pre_callback=clock_changed.set,
            )

            def battery_clock_ns():
                now_ns = clock.now().nanoseconds
                return 0 if clock_changed.is_set() else now_ns

            self._battery_clock_ns = battery_clock_ns
            self.consumer.bind_battery_clock(battery_clock_ns)

        self._setup_robot_interfaces()
        if enable_live_routing and node is not None and isinstance(provider, CachedRouteDistanceProvider):
            self.consumer.enable_live_routing(self.route_resolver.compute_route)

    def _setup_robot_interfaces(self) -> None:
        if self.node is None:
            return

        from fleet_interfaces.action import ExecuteTask
        from fleet_interfaces.msg import RobotStatus
        from fleet_interfaces.srv import ClearRobotError
        from nav2_msgs.action import ComputePathToPose
        from rclpy.action import ActionClient

        from .action_client import ExecuteTaskActionClientBridge
        from .service_client import ClearRobotErrorServiceClient
        from .status_subscriber import RobotStatusSubscriberBridge

        for r_id in self.robot_ids:
            namespace = self.robot_namespaces[r_id]
            # 1. Status Subscriber (/{robot_id}/robot_status - C3.3.3-DEC-01)
            status_bridge = RobotStatusSubscriberBridge(
                consumer=self.consumer,
                loop=self.loop,
                ros_clock_ns=lambda: self.node.get_clock().now().nanoseconds,
                robot_id=r_id,
                battery_clock_ns=self._battery_clock_ns,
            )
            self.status_bridges[r_id] = status_bridge
            self.node.create_subscription(
                RobotStatus,
                f"{namespace}/robot_status",
                status_bridge.handle_status_msg,
                10,
            )

            # 2. ExecuteTask ActionClient (/{robot_id}/execute_task - C3.3.3-DEC-01)
            act_client = ActionClient(self.node, ExecuteTask, f"{namespace}/execute_task")
            act_bridge = ExecuteTaskActionClientBridge(
                robot_id=r_id,
                consumer=self.consumer,
                loop=self.loop,
                action_client=act_client,
            )
            self.action_bridges[r_id] = act_bridge

            # 3. ClearRobotError ServiceClient (/{robot_id}/clear_robot_error - C3.3.3-DEC-01)
            srv_client = self.node.create_client(ClearRobotError, f"{namespace}/clear_robot_error")
            clear_bridge = ClearRobotErrorServiceClient(
                robot_id=r_id,
                service_client=srv_client,
            )
            self.service_clients[r_id] = clear_bridge

            # 4. Nav2 ComputePathToPose ActionClient (/{robot_id}/compute_path_to_pose - C3.3.3-DEC-01)
            nav2_client = ActionClient(self.node, ComputePathToPose, f"{namespace}/compute_path_to_pose")
            self.route_resolver.register_robot_client(r_id, nav2_client)

        logger.info("Initialized ROS 2 interfaces for robots: %s", self.robot_ids)
