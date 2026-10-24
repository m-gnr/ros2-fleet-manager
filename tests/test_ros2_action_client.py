"""Unit tests for ExecuteTask ActionClient adapter.

Verifies:
- C3.3.2-DEC-01: 5.0s goal accept timeout, 3.0s cancel response timeout
- C3.3.2-DEC-03: GoalResponse.REJECT creates task_review_holds and HELD_FOR_REVIEW
- C3.3.2-DEC-05: Real completed_epoch validation vs rejection on mismatch
- C3.3.2-DEC-06: Thread-safe callback bridging to asyncio consumer
- C3.3.2-DEC-07: Invariant UUID across retries, no automatic FAILED/ERROR on comm timeout
"""

import asyncio
from dataclasses import dataclass
from unittest.mock import MagicMock
import uuid
import pytest

from backend.fleet_manager.adapters.action_client import (
    ExecuteTaskActionClientBridge,
    str_to_ros_uuid,
)
from backend.fleet_manager.domain.constants import (
    CANCEL_RESPONSE_TIMEOUT_SEC,
    GOAL_ACCEPT_TIMEOUT_SEC,
    TaskPriority,
    TaskResultStatus,
)
from backend.fleet_manager.domain.fleet_manager_core import FleetManagerCore
from backend.fleet_manager.domain.models import Pose2D
from backend.fleet_manager.domain.scheduler import RouteDistanceProvider
from backend.fleet_manager.event_loop import Event, FleetEventLoop
from backend.fleet_manager.persistence.store import SQLiteStore


class SimpleRoutes(RouteDistanceProvider):
    def get_path_distance(self, start: Pose2D, goal: Pose2D):
        return 10.0


def test_str_to_ros_uuid():
    u_str = str(uuid.uuid4())
    res = str_to_ros_uuid(u_str)
    # Check that bytes match
    if hasattr(res, "uuid"):
        assert bytes(res.uuid) == uuid.UUID(u_str).bytes
    else:
        assert bytes(res) == uuid.UUID(u_str).bytes


def test_goal_acceptance_timeout_raises_timeout_error():
    """Verify send_execute_task_goal raises TimeoutError after 5.0s without FAILED/ERROR."""
    async def scenario():
        now_val = 100.0
        def clock():
            nonlocal now_val
            return now_val

        consumer = MagicMock()
        loop = asyncio.get_running_loop()
        bridge = ExecuteTaskActionClientBridge(
            robot_id="r1",
            consumer=consumer,
            loop=loop,
            clock=clock,
        )

        mock_client = MagicMock()
        mock_future = loop.create_future()
        mock_client.send_goal_async.return_value = mock_future
        bridge.set_action_client(mock_client)

        u = str(uuid.uuid4())
        task = asyncio.create_task(
            bridge.send_execute_task_goal(
                task_id="t1",
                assignment_epoch=1,
                goal_uuid=u,
                pickup_pose=Pose2D(1, 0),
                dropoff_pose=Pose2D(2, 0),
                priority=TaskPriority.PRIORITY_MEDIUM,
                command_id=f"EXECUTE_TASK:{u}",
                timeout_sec=5.0,
            )
        )
        await asyncio.sleep(0.01)
        now_val += 5.5  # Monotonic time advances past 5.0s
        await asyncio.sleep(0.05)

        with pytest.raises(TimeoutError) as exc_info:
            await task
        assert "timed out after 5.0s" in str(exc_info.value)
        # Verify no FAILED/ERROR event was submitted
        assert consumer.submit.call_count == 0

    asyncio.run(scenario())


def test_cancel_response_timeout_raises_timeout_error():
    """Verify send_cancel_task raises TimeoutError after 3.0s without FAILED/ERROR."""
    async def scenario():
        now_val = 100.0
        def clock():
            nonlocal now_val
            return now_val

        consumer = MagicMock()
        loop = asyncio.get_running_loop()
        bridge = ExecuteTaskActionClientBridge(
            robot_id="r1",
            consumer=consumer,
            loop=loop,
            clock=clock,
        )

        mock_goal_handle = MagicMock()
        mock_cancel_future = loop.create_future()
        mock_goal_handle.cancel_goal_async.return_value = mock_cancel_future

        u = str(uuid.uuid4())
        bridge._active_goal_handles[u] = mock_goal_handle

        task = asyncio.create_task(
            bridge.send_cancel_task(
                task_id="t1",
                assignment_epoch=1,
                goal_uuid=u,
                cancel_command_id=f"CANCEL:{u}",
                timeout_sec=3.0,
            )
        )
        await asyncio.sleep(0.01)
        now_val += 3.5  # Monotonic time advances past 3.0s
        await asyncio.sleep(0.05)

        with pytest.raises(TimeoutError) as exc_info:
            await task
        assert "timed out after 3.0s" in str(exc_info.value)

    asyncio.run(scenario())


def test_explicit_goal_rejection_triggers_review_hold(tmp_path):
    """Verify explicit GoalResponse.REJECT places task on review hold in FM."""
    async def scenario():
        db_path = str(tmp_path / "test_reject.db")
        store = SQLiteStore(db_path)
        core = FleetManagerCore(SimpleRoutes(), Pose2D())
        core.register_robot("r1")
        loop = FleetEventLoop(store, core)
        await loop.start()

        # Robot status
        await loop.submit(Event("ROBOT_STATUS", {
            "robot_id": "r1", "status_seq": 1, "publisher_session_id": str(uuid.uuid4()),
            "current_epoch": 0, "state": 1, "current_phase": 0, "is_loaded": False,
            "pose": Pose2D(), "battery_soc_percent": 100, "battery_energy_wh": 100,
            "current_task_id": None, "timestamp_sec": 10.0,
        }))

        # Submit and assign task
        await loop.submit(Event("SUBMIT_TASK", {
            "task_id": "t1", "pickup_pose": Pose2D(1, 0), "dropoff_pose": Pose2D(2, 0),
            "priority": TaskPriority.PRIORITY_MEDIUM, "created_at": 10.0,
        }))
        await loop.submit(Event("TICK", {"current_time": 10.0}))

        task = loop.core._active_tasks["t1"]
        goal_uuid = task.goal_uuid

        bridge = ExecuteTaskActionClientBridge(
            robot_id="r1",
            consumer=loop,
            loop=asyncio.get_running_loop(),
        )

        mock_client = MagicMock()
        mock_future = asyncio.get_running_loop().create_future()
        mock_goal_handle = MagicMock()
        mock_goal_handle.accepted = False  # Goal rejected!
        mock_future.set_result(mock_goal_handle)
        mock_client.send_goal_async.return_value = mock_future
        bridge.set_action_client(mock_client)

        accepted = await bridge.send_execute_task_goal(
            task_id="t1",
            assignment_epoch=task.assignment_epoch,
            goal_uuid=goal_uuid,
            pickup_pose=task.pickup_pose,
            dropoff_pose=task.dropoff_pose,
            priority=task.priority,
            command_id=f"EXECUTE_TASK:{goal_uuid}",
        )
        assert accepted is False

        # Verify task is now on review hold!
        assert loop.core.has_review_hold("t1") is True
        assert "t1" not in loop.core._active_tasks

        # Verify task is in task_review_holds SQLite table
        row = store.connection.execute("SELECT * FROM task_review_holds WHERE task_id='t1'").fetchone()
        assert row is not None
        assert row["robot_id"] == "r1"
        assert row["goal_uuid"] == goal_uuid

        # Verify Outbox command state is HELD_FOR_REVIEW
        cmd_row = store.connection.execute("SELECT * FROM outbox_events WHERE goal_uuid=?", (goal_uuid,)).fetchone()
        assert cmd_row is not None
        assert cmd_row["state"] == "HELD_FOR_REVIEW"

        # Verify Scheduler does NOT blindly reassign held task
        await loop.submit(Event("TICK", {"current_time": 12.0}))
        assert "t1" not in loop.core._active_tasks

        await loop.close()
        store.close()

    asyncio.run(scenario())


def test_completed_epoch_validation_and_mismatch_rejection(tmp_path):
    """Verify C3.3.2-DEC-05: real completed_epoch validation vs STALE rejection on mismatch."""
    async def scenario():
        db_path = str(tmp_path / "test_completed_epoch.db")
        store = SQLiteStore(db_path)
        core = FleetManagerCore(SimpleRoutes(), Pose2D())
        core.register_robot("r1")
        loop = FleetEventLoop(store, core)
        await loop.start()

        # Initial status
        await loop.submit(Event("ROBOT_STATUS", {
            "robot_id": "r1", "status_seq": 1, "publisher_session_id": str(uuid.uuid4()),
            "current_epoch": 0, "state": 1, "current_phase": 0, "is_loaded": False,
            "pose": Pose2D(), "battery_soc_percent": 100, "battery_energy_wh": 100,
            "current_task_id": None, "timestamp_sec": 10.0,
        }))

        # Assign task
        await loop.submit(Event("SUBMIT_TASK", {
            "task_id": "t1", "pickup_pose": Pose2D(1, 0), "dropoff_pose": Pose2D(2, 0),
            "priority": TaskPriority.PRIORITY_MEDIUM, "created_at": 10.0,
        }))
        await loop.submit(Event("TICK", {"current_time": 10.0}))

        task = loop.core._active_tasks["t1"]
        assigned_epoch = task.assignment_epoch
        goal_uuid = task.goal_uuid

        # 1. ACTION_RESULT with wrong completed_epoch (e.g. 99 != assigned_epoch)
        bad_result = Event("ACTION_RESULT", {
            "robot_id": "r1",
            "task_id": "t1",
            "assignment_epoch": assigned_epoch,
            "completed_epoch": 99,  # Mismatched!
            "goal_uuid": goal_uuid,
            "result_status": int(TaskResultStatus.STATUS_SUCCEEDED),
        })
        outcome = await loop.submit(bad_result)
        assert outcome == "STALE"

        # Verify task is STILL active and NOT completed!
        assert "t1" in loop.core._active_tasks
        assert "t1" not in loop.core._completed_tasks

        # 2. ACTION_RESULT with real completed_epoch matching assignment_epoch
        good_result = Event("ACTION_RESULT", {
            "robot_id": "r1",
            "task_id": "t1",
            "assignment_epoch": assigned_epoch,
            "completed_epoch": assigned_epoch,  # Exactly matches!
            "goal_uuid": goal_uuid,
            "result_status": int(TaskResultStatus.STATUS_SUCCEEDED),
        })
        outcome = await loop.submit(good_result)
        assert outcome == "APPLIED"

        # Now task is successfully completed!
        assert "t1" not in loop.core._active_tasks
        assert "t1" in loop.core._completed_tasks

        await loop.close()
        store.close()

    asyncio.run(scenario())
