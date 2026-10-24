"""Unit tests for SQLite Outbox sender and idempotent retry contracts.

Verifies C3.3.2-DEC-07 & C3.3-DEC-02:
- Same command_id, task_id, assignment_epoch, and goal_uuid on retry (invariant payload)
- Uncertain delivery / timeout does NOT transition task to FAILED or robot to ERROR
- GoalResponse.REJECT moves command to HELD_FOR_REVIEW (C3.3.2-DEC-03)
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest

from backend.fleet_manager.adapters.outbox_sender import ROS2OutboxSender
from backend.fleet_manager.domain.constants import TaskPriority
from backend.fleet_manager.domain.fleet_manager_core import FleetManagerCore
from backend.fleet_manager.domain.models import Pose2D
from backend.fleet_manager.domain.scheduler import RouteDistanceProvider
from backend.fleet_manager.event_loop import Event, FleetEventLoop, OutboxDispatcher
from backend.fleet_manager.persistence.store import SQLiteStore


class SimpleRoutes(RouteDistanceProvider):
    def get_path_distance(self, start: Pose2D, goal: Pose2D):
        return 10.0


def test_outbox_sender_retry_preserves_invariant_identity(tmp_path):
    """Verify retries preserve exact command_id, task_id, assignment_epoch, and goal_uuid."""
    async def scenario():
        db_path = str(tmp_path / "test_outbox_retry.db")
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

        # Assign task
        await loop.submit(Event("SUBMIT_TASK", {
            "task_id": "t1", "pickup_pose": Pose2D(1, 0), "dropoff_pose": Pose2D(2, 0),
            "priority": TaskPriority.PRIORITY_MEDIUM, "created_at": 10.0,
        }))
        await loop.submit(Event("TICK", {"current_time": 10.0}))

        task = loop.core._active_tasks["t1"]
        orig_goal_uuid = task.goal_uuid
        orig_epoch = task.assignment_epoch

        # Track calls to send_execute_task_goal
        call_records = []
        mock_action_bridge = MagicMock()

        async def _mock_send_goal(**kwargs):
            call_records.append(dict(kwargs))
            if len(call_records) == 1:
                # First attempt times out (ambiguous delivery)
                raise TimeoutError("Goal acceptance timeout 5.0s")
            # Second attempt succeeds
            return True

        mock_action_bridge.send_execute_task_goal = AsyncMock(side_effect=_mock_send_goal)

        sender = ROS2OutboxSender(action_clients={"r1": mock_action_bridge})
        clock_val = 100.0
        dispatcher = OutboxDispatcher(
            consumer=loop,
            sender=sender,
            clock=lambda: clock_val,
            retry_delay=2.0,
        )

        # 1. First send attempt -> times out
        sent = await dispatcher.send_one()
        assert sent is True
        assert len(call_records) == 1
        assert call_records[0]["goal_uuid"] == orig_goal_uuid
        assert call_records[0]["assignment_epoch"] == orig_epoch

        # Verify Outbox command state is RETRY
        cmd = store.connection.execute("SELECT * FROM outbox_events WHERE task_id='t1'").fetchone()
        assert cmd["state"] == "RETRY"
        assert cmd["attempts"] == 1
        assert "Goal acceptance timeout" in cmd["last_error"]

        # Invariant check: Task is STILL active, NOT marked FAILED!
        assert "t1" in loop.core._active_tasks
        assert "t1" not in loop.core._failed_tasks
        assert loop.core.tracker.get_robot("r1").state != 6  # Not ERROR!

        # 2. Advance monotonic clock past retry delay and claim again
        clock_val += 3.0
        sent2 = await dispatcher.send_one()
        assert sent2 is True
        assert len(call_records) == 2

        # Verify second attempt used EXACT same goal_uuid, epoch, and command_id
        assert call_records[1]["goal_uuid"] == orig_goal_uuid
        assert call_records[1]["assignment_epoch"] == orig_epoch
        assert call_records[1]["command_id"] == call_records[0]["command_id"]

        # Verify command is now SENT
        cmd2 = store.connection.execute("SELECT * FROM outbox_events WHERE task_id='t1'").fetchone()
        assert cmd2["state"] == "SENT"
        assert cmd2["attempts"] == 2

        await loop.close()
        store.close()

    asyncio.run(scenario())


def test_outbox_sender_goal_rejection_moves_to_held_for_review(tmp_path):
    """Verify explicit goal rejection transitions command to HELD_FOR_REVIEW."""
    async def scenario():
        db_path = str(tmp_path / "test_outbox_reject.db")
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

        # Assign task
        await loop.submit(Event("SUBMIT_TASK", {
            "task_id": "t_rej", "pickup_pose": Pose2D(1, 0), "dropoff_pose": Pose2D(2, 0),
            "priority": TaskPriority.PRIORITY_MEDIUM, "created_at": 10.0,
        }))
        await loop.submit(Event("TICK", {"current_time": 10.0}))

        task = loop.core._active_tasks["t_rej"]
        goal_uuid = task.goal_uuid

        mock_action_bridge = MagicMock()
        # Mock goal rejection: submits GOAL_REJECTED and returns False
        async def _mock_reject_send(**kwargs):
            await loop.submit(Event("GOAL_REJECTED", {
                "task_id": "t_rej", "robot_id": "r1", "assignment_epoch": task.assignment_epoch,
                "goal_uuid": goal_uuid, "reason": "State machine rejected admission", "held_at": 50.0,
            }))
            return False

        mock_action_bridge.send_execute_task_goal = AsyncMock(side_effect=_mock_reject_send)
        sender = ROS2OutboxSender(action_clients={"r1": mock_action_bridge})
        dispatcher = OutboxDispatcher(
            consumer=loop,
            sender=sender,
            clock=lambda: 50.0,
            retry_delay=2.0,
        )

        sent = await dispatcher.send_one()
        assert sent is True

        # Verify Outbox command is HELD_FOR_REVIEW
        cmd = store.connection.execute("SELECT * FROM outbox_events WHERE task_id='t_rej'").fetchone()
        assert cmd["state"] == "HELD_FOR_REVIEW"

        # Verify not claimed again
        assert await dispatcher.send_one() is False

        await loop.close()
        store.close()

    asyncio.run(scenario())
