"""ExecuteTask ActionClient adapter for Fleet Manager.

Conforms strictly to:
- C3.3.2-DEC-01: Goal accept timeout 5.0s monotonic, cancel response timeout 3.0s monotonic.
- C3.3.2-DEC-03: Explicit GoalResponse.REJECT handling via GOAL_REJECTED event and task_review_holds.
- C3.3.2-DEC-05: Real completed_epoch propagation in ACTION_RESULT.
- C3.3.2-DEC-06: Thread-safe callback bridging to asyncio consumer.
- C3.3.2-DEC-07: Invariant (task_id, assignment_epoch, goal_uuid) retry contracts.
"""

import asyncio
import logging
import math
import time
from typing import Any, Callable, Dict, Optional, Tuple
import uuid

from ..domain.constants import (
    CANCEL_RESPONSE_TIMEOUT_SEC,
    GOAL_ACCEPT_TIMEOUT_SEC,
    TaskPriority,
)
from ..domain.models import Pose2D
from ..event_loop import Event

logger = logging.getLogger(__name__)


def str_to_ros_uuid(uuid_str: str) -> Any:
    """Construct unique_identifier_msgs/msg/UUID from UUID string if rosidl is available."""
    try:
        from unique_identifier_msgs.msg import UUID as RosUUID
        u = uuid.UUID(uuid_str)
        return RosUUID(uuid=list(u.bytes))
    except ImportError:
        return uuid.UUID(uuid_str).bytes


def yaw_to_quaternion(yaw: float) -> Tuple[float, float, float, float]:
    """Convert planar yaw angle in radians to quaternion (x, y, z, w)."""
    half = yaw * 0.5
    return (0.0, 0.0, math.sin(half), math.cos(half))


class ExecuteTaskActionClientBridge:
    """Bridges ROS 2 ActionClient operations with FleetEventLoop and Outbox."""

    def __init__(
        self,
        robot_id: str,
        consumer: Any,
        loop: asyncio.AbstractEventLoop,
        action_client: Any = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.robot_id = robot_id
        self.consumer = consumer
        self.loop = loop
        self.action_client = action_client
        self.clock = clock
        self._active_goal_handles: Dict[str, Any] = {}
        self._feedback_seq: Dict[str, int] = {}

    def set_action_client(self, action_client: Any) -> None:
        self.action_client = action_client

    async def send_execute_task_goal(
        self,
        task_id: str,
        assignment_epoch: int,
        goal_uuid: str,
        pickup_pose: Pose2D,
        dropoff_pose: Pose2D,
        priority: int,
        command_id: str,
        timeout_sec: float = GOAL_ACCEPT_TIMEOUT_SEC,
    ) -> bool:
        """Send ExecuteTask goal asynchronously with exact goal_uuid.
        
        Awaits acceptance up to timeout_sec monotonic seconds.
        If timeout occurs -> raises TimeoutError (triggers outbox retry).
        If REJECT -> submits GOAL_REJECTED to consumer and returns False.
        If ACCEPT -> registers feedback/result listeners and returns True.
        """
        if self.action_client is None:
            raise RuntimeError(f"Action client for {self.robot_id} is not initialized")

        try:
            from fleet_interfaces.action import ExecuteTask
            from geometry_msgs.msg import PoseStamped

            goal_msg = ExecuteTask.Goal()
            goal_msg.task_id = task_id
            goal_msg.assignment_epoch = assignment_epoch
            goal_msg.priority = priority

            # Pickup Pose
            p_pose = PoseStamped()
            p_pose.header.frame_id = pickup_pose.frame_id or "map"
            p_pose.pose.position.x = float(pickup_pose.x)
            p_pose.pose.position.y = float(pickup_pose.y)
            qx, qy, qz, qw = yaw_to_quaternion(pickup_pose.yaw)
            p_pose.pose.orientation.x = qx
            p_pose.pose.orientation.y = qy
            p_pose.pose.orientation.z = qz
            p_pose.pose.orientation.w = qw
            goal_msg.pickup_pose = p_pose

            # Dropoff Pose
            d_pose = PoseStamped()
            d_pose.header.frame_id = dropoff_pose.frame_id or "map"
            d_pose.pose.position.x = float(dropoff_pose.x)
            d_pose.pose.position.y = float(dropoff_pose.y)
            qx, qy, qz, qw = yaw_to_quaternion(dropoff_pose.yaw)
            d_pose.pose.orientation.x = qx
            d_pose.pose.orientation.y = qy
            d_pose.pose.orientation.z = qz
            d_pose.pose.orientation.w = qw
            goal_msg.dropoff_pose = d_pose
        except ImportError:
            class MockGoal:
                pass
            goal_msg = MockGoal()
            goal_msg.task_id = task_id
            goal_msg.assignment_epoch = assignment_epoch
            goal_msg.priority = priority
            goal_msg.pickup_pose = pickup_pose
            goal_msg.dropoff_pose = dropoff_pose

        # Construct goal UUID message
        ros_uuid = str_to_ros_uuid(goal_uuid)

        def _feedback_callback(feedback_msg):
            self._handle_feedback(task_id, goal_uuid, assignment_epoch, feedback_msg)

        send_future = self.action_client.send_goal_async(
            goal_msg,
            feedback_callback=_feedback_callback,
            goal_uuid=ros_uuid,
        )

        # Await acceptance with local monotonic clock timeout
        start_t = self.clock()
        while not send_future.done():
            if (self.clock() - start_t) > timeout_sec:
                raise TimeoutError(
                    f"ExecuteTask goal acceptance timed out after {timeout_sec:.1f}s for {task_id}:{goal_uuid}"
                )
            await asyncio.sleep(0.02)

        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            # Explicit goal rejection
            logger.warning("ExecuteTask goal rejected by robot %s for task %s", self.robot_id, task_id)
            reject_event = Event(
                kind="GOAL_REJECTED",
                payload={
                    "task_id": task_id,
                    "robot_id": self.robot_id,
                    "assignment_epoch": assignment_epoch,
                    "goal_uuid": goal_uuid,
                    "reason": "GoalResponse.REJECT",
                    "held_at": self.clock(),
                },
            )
            await self.consumer.submit(reject_event)
            return False

        # Accepted
        self._active_goal_handles[goal_uuid] = goal_handle
        self._feedback_seq[goal_uuid] = 0

        # Register result callback
        res_future = goal_handle.get_result_async()
        res_future.add_done_callback(
            lambda fut: self._handle_result(task_id, goal_uuid, assignment_epoch, fut)
        )
        return True

    async def send_cancel_task(
        self,
        task_id: str,
        assignment_epoch: int,
        goal_uuid: str,
        cancel_command_id: str,
        timeout_sec: float = CANCEL_RESPONSE_TIMEOUT_SEC,
    ) -> bool:
        """Request preemption cancellation of an active ExecuteTask goal.
        
        Awaits cancel response up to timeout_sec monotonic seconds.
        If timeout occurs -> raises TimeoutError (triggers outbox retry).
        """
        goal_handle = self._active_goal_handles.get(goal_uuid)
        if goal_handle is None:
            raise RuntimeError(f"No active goal handle for cancel: {goal_uuid}")

        cancel_future = goal_handle.cancel_goal_async()
        start_t = self.clock()
        while not cancel_future.done():
            if (self.clock() - start_t) > timeout_sec:
                raise TimeoutError(
                    f"Cancel response timed out after {timeout_sec:.1f}s for {task_id}:{goal_uuid}"
                )
            await asyncio.sleep(0.02)

        cancel_response = cancel_future.result()
        # In rclpy: cancel_response.goals_canceling contains accepted cancel goals
        accepted = bool(cancel_response and len(cancel_response.goals_canceling) > 0)

        cancel_event = Event(
            kind="CANCEL_RESPONSE",
            payload={
                "robot_id": self.robot_id,
                "task_id": task_id,
                "assignment_epoch": assignment_epoch,
                "goal_uuid": goal_uuid,
                "cancel_command_id": cancel_command_id,
                "accepted": accepted,
            },
        )
        await self.consumer.submit(cancel_event)
        return accepted

    def _handle_feedback(self, task_id: str, goal_uuid: str, assignment_epoch: int, feedback_wrapper: Any) -> None:
        """ROS callback for action feedback."""
        fb = feedback_wrapper.feedback
        seq = self._feedback_seq.get(goal_uuid, 0) + 1
        self._feedback_seq[goal_uuid] = seq

        payload = {
            "robot_id": self.robot_id,
            "task_id": task_id,
            "assignment_epoch": assignment_epoch,
            "goal_uuid": goal_uuid,
            "status_seq": seq,
            "current_phase": int(fb.current_phase),
            "distance_to_goal": float(fb.distance_to_goal),
            "battery_soc": float(fb.battery_soc),
        }
        asyncio.run_coroutine_threadsafe(
            self.consumer.submit(Event(kind="ACTION_FEEDBACK", payload=payload)),
            self.loop,
        )

    def _handle_result(self, task_id: str, goal_uuid: str, assignment_epoch: int, future: Any) -> None:
        """ROS callback for action result completion."""
        try:
            res_wrapped = future.result()
            res = res_wrapped.result
            completed_epoch = int(res.completed_epoch)
            status = int(res.status)
            error_reason = str(res.error_reason)

            payload = {
                "robot_id": self.robot_id,
                "task_id": task_id,
                "assignment_epoch": assignment_epoch,
                "completed_epoch": completed_epoch,
                "goal_uuid": goal_uuid,
                "result_status": status,
                "error_reason": error_reason,
            }
            asyncio.run_coroutine_threadsafe(
                self.consumer.submit(Event(kind="ACTION_RESULT", payload=payload)),
                self.loop,
            )
        except Exception as exc:
            logger.error("Failed to process action result for %s:%s: %s", task_id, goal_uuid, exc)
        finally:
            self._active_goal_handles.pop(goal_uuid, None)
            self._feedback_seq.pop(goal_uuid, None)
