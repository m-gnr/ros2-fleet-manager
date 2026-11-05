"""Station action delivery with one ROS send per immutable Outbox command."""

import asyncio
import logging
import time

from ..domain.constants import CANCEL_RESPONSE_TIMEOUT_SEC, GOAL_ACCEPT_TIMEOUT_SEC, StationType
from ..event_loop import Event
from .action_client import str_to_ros_uuid, yaw_to_quaternion

logger = logging.getLogger(__name__)


class StationActionClient:
    def __init__(self, client, consumer, loop):
        self.client = client
        self.consumer = consumer
        self.loop = loop
        self.goal_futures = {}
        self.goal_handles = {}
        self.cancel_futures = {}

    async def send(self, command, payload):
        from fleet_interfaces.action import NavigateToStation

        goal_uuid = command["goal_uuid"]
        identity = {
            "task_id": command["task_id"], "robot_id": payload["assigned_robot_id"],
            "station_id": payload["station_id"], "assignment_epoch": command["assignment_epoch"],
            "goal_uuid": goal_uuid,
        }
        if command["kind"] == "CANCEL_STATION_MOVE":
            await self._cancel(command["command_id"], goal_uuid, identity)
            return
        if goal_uuid in self.goal_handles:
            return
        if goal_uuid not in self.goal_futures:
            goal = NavigateToStation.Goal()
            goal.move_id = identity["task_id"]
            goal.robot_id = identity["robot_id"]
            goal.station_id = identity["station_id"]
            goal.expected_session_id = str_to_ros_uuid(payload["session_id"])
            goal.assignment_epoch = identity["assignment_epoch"]
            goal.charging_station = payload["station_type"] == StationType.CHARGING
            goal.tolerance_radius = payload["tolerance_radius"]
            pose = payload["pose"]
            goal.target_pose.header.frame_id = pose["frame_id"]
            goal.target_pose.pose.position.x = float(pose["x"])
            goal.target_pose.pose.position.y = float(pose["y"])
            orientation = goal.target_pose.pose.orientation
            orientation.x, orientation.y, orientation.z, orientation.w = yaw_to_quaternion(pose["yaw"])
            ros_uuid = str_to_ros_uuid(goal_uuid)
            self.goal_futures[goal_uuid] = None
            self.goal_futures[goal_uuid] = self.client.send_goal_async(goal, goal_uuid=ros_uuid)
        handle = await self._wait(self.goal_futures[goal_uuid], GOAL_ACCEPT_TIMEOUT_SEC)
        if handle is None:
            raise RuntimeError("Station goal response is unavailable")
        if not handle.accepted:
            await self.consumer.submit(Event("STATION_GOAL_REJECTED", identity))
            self.goal_futures.pop(goal_uuid, None)
            return
        result_future = handle.get_result_async()
        self.goal_handles[goal_uuid] = handle
        self.goal_futures.pop(goal_uuid)
        result_future.add_done_callback(
            lambda future: self.loop.call_soon_threadsafe(self._result, goal_uuid, identity, future),
        )

    async def _cancel(self, command_id, goal_uuid, identity):
        handle = self.goal_handles.get(goal_uuid)
        if handle is None:
            raise RuntimeError("Station action handle unavailable for cancellation")
        if command_id not in self.cancel_futures:
            self.cancel_futures[command_id] = None
            self.cancel_futures[command_id] = handle.cancel_goal_async()
        response = await self._wait(self.cancel_futures[command_id], CANCEL_RESPONSE_TIMEOUT_SEC)
        accepted = any(bytes(goal.goal_id.uuid) == bytes(handle.goal_id.uuid)
                       for goal in response.goals_canceling)
        await self.consumer.submit(Event("STATION_CANCEL_RESPONSE", {
            **identity, "cancel_command_id": command_id, "accepted": accepted,
        }))
        self.cancel_futures.pop(command_id, None)

    def _result(self, goal_uuid, identity, future):
        from action_msgs.msg import GoalStatus
        from fleet_interfaces.action import NavigateToStation

        try:
            response = future.result()
            result = response.result
            terminal = {
                NavigateToStation.Result.STATUS_SUCCEEDED: GoalStatus.STATUS_SUCCEEDED,
                NavigateToStation.Result.STATUS_PREEMPTED: GoalStatus.STATUS_CANCELED,
                NavigateToStation.Result.STATUS_FAILED: GoalStatus.STATUS_ABORTED,
            }
            if terminal.get(result.status) != response.status:
                raise ValueError("Station action terminal status mismatch")
            stamp = result.stationary_stamp
            event = Event("STATION_RESULT", {
                **identity, "task_id": result.move_id, "station_id": result.station_id,
                "completed_epoch": result.completed_epoch, "result_status": result.status,
                "proof_ns": stamp.sec * 10**9 + stamp.nanosec, "error_reason": result.error_reason,
            })
            task = self.loop.create_task(self.consumer.submit(event))
            task.add_done_callback(lambda done: self._finish_result(goal_uuid, done))
        except Exception:
            logger.exception("Station result evidence unavailable goal=%s", goal_uuid)

    def _finish_result(self, goal_uuid, task):
        self.goal_handles.pop(goal_uuid, None)
        if not task.cancelled() and task.exception() is not None:
            logger.error("Station terminal commit failed goal=%s", goal_uuid, exc_info=task.exception())

    @staticmethod
    async def _wait(future, timeout):
        if future is None:
            raise RuntimeError("Station action delivery is uncertain; ownership retained")
        deadline = time.monotonic() + timeout
        while not future.done():
            if time.monotonic() >= deadline:
                raise TimeoutError("Station action response unavailable; ownership retained")
            await asyncio.sleep(0.02)
        return future.result()
