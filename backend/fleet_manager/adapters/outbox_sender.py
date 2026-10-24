"""Outbox sender bridge connecting OutboxDispatcher to ROS 2 ActionClient.

Conforms strictly to:
- C3.3.2-DEC-07: Invariant command_id, task_id, assignment_epoch, goal_uuid across retries.
- C3.3.2-DEC-03: GoalResponse.REJECT moves outbox command to HELD_FOR_REVIEW without blindly retrying.
- No automatic FAILED/ERROR transitions on communication timeout.
"""

import json
import logging
from typing import Any, Dict

from ..domain.models import Pose2D
from .action_client import ExecuteTaskActionClientBridge

logger = logging.getLogger(__name__)


class ROS2OutboxSender:
    """Dispatches claimed Outbox commands to corresponding robot ROS 2 action clients."""

    def __init__(
        self,
        action_clients: Dict[str, ExecuteTaskActionClientBridge],
    ) -> None:
        self.action_clients = action_clients

    def register_client(self, robot_id: str, client: ExecuteTaskActionClientBridge) -> None:
        self.action_clients[robot_id] = client

    async def __call__(self, command: dict) -> None:
        """Invoked by OutboxDispatcher.send_one() for a single claimed outbox command."""
        payload = json.loads(command["payload"])
        robot_id = payload.get("assigned_robot_id")
        if not robot_id:
            raise ValueError(f"Command payload missing assigned_robot_id: {command['command_id']}")

        action_bridge = self.action_clients.get(robot_id)
        if action_bridge is None:
            raise RuntimeError(f"No action client registered for robot '{robot_id}'")

        kind = command["kind"]
        task_id = command["task_id"]
        assignment_epoch = command["assignment_epoch"]
        goal_uuid = command["goal_uuid"]

        if kind == "EXECUTE_TASK":
            p_dict = payload.get("pickup_pose", {})
            d_dict = payload.get("dropoff_pose", {})
            pickup = Pose2D(
                x=float(p_dict.get("x", 0.0)),
                y=float(p_dict.get("y", 0.0)),
                yaw=float(p_dict.get("yaw", 0.0)),
                frame_id=p_dict.get("frame_id", "map"),
            )
            dropoff = Pose2D(
                x=float(d_dict.get("x", 0.0)),
                y=float(d_dict.get("y", 0.0)),
                yaw=float(d_dict.get("yaw", 0.0)),
                frame_id=d_dict.get("frame_id", "map"),
            )
            priority = int(payload.get("priority", 3))

            accepted = await action_bridge.send_execute_task_goal(
                task_id=task_id,
                assignment_epoch=assignment_epoch,
                goal_uuid=goal_uuid,
                pickup_pose=pickup,
                dropoff_pose=dropoff,
                priority=priority,
                command_id=command["command_id"],
            )
            if not accepted:
                # Goal explicitly rejected. Action client submitted GOAL_REJECTED.
                # Do not raise exception; command should not be retried.
                logger.info("Goal %s was rejected by robot %s and placed on review hold", goal_uuid, robot_id)

        elif kind == "CANCEL_TASK":
            await action_bridge.send_cancel_task(
                task_id=task_id,
                assignment_epoch=assignment_epoch,
                goal_uuid=goal_uuid,
                cancel_command_id=command["command_id"],
            )
        else:
            raise ValueError(f"Unknown outbox command kind: {kind}")
