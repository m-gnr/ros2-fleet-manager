"""Unit tests for task_review_holds table and scheduler ineligibility.

Verifies C3.3.2-DEC-03:
- Task review hold record creation on explicit goal rejection
- Scheduler skips held tasks as ineligible (no blind re-queue / reassignment)
- Operator release of hold restores eligibility
- Scenario reset gating preserves database evidence
"""

import asyncio
import uuid
import pytest

from backend.fleet_manager.domain.constants import TaskPriority
from backend.fleet_manager.domain.fleet_manager_core import FleetManagerCore
from backend.fleet_manager.domain.models import Pose2D
from backend.fleet_manager.domain.scheduler import RouteDistanceProvider
from backend.fleet_manager.event_loop import Event, FleetEventLoop
from backend.fleet_manager.persistence.store import ScenarioResetRequired, SQLiteStore


class SimpleRoutes(RouteDistanceProvider):
    def get_path_distance(self, start: Pose2D, goal: Pose2D):
        return 10.0


def test_task_review_holds_lifecycle(tmp_path):
    """Verify task_review_holds lifecycle, scheduler ineligibility, and operator clear."""
    async def scenario():
        db_path = str(tmp_path / "test_holds.db")
        store = SQLiteStore(db_path)
        core = FleetManagerCore(SimpleRoutes(), Pose2D())
        core.register_robot("r1")
        loop = FleetEventLoop(store, core)
        await loop.start()

        sess = str(uuid.uuid4())
        # Initial robot status
        await loop.submit(Event("ROBOT_STATUS", {
            "robot_id": "r1", "status_seq": 1, "publisher_session_id": sess,
            "current_epoch": 0, "state": 1, "current_phase": 0, "is_loaded": False,
            "pose": Pose2D(), "battery_soc_percent": 100, "battery_energy_wh": 100,
            "current_task_id": None, "timestamp_sec": 10.0,
        }))

        # Submit task
        await loop.submit(Event("SUBMIT_TASK", {
            "task_id": "t_hold", "pickup_pose": Pose2D(1, 0), "dropoff_pose": Pose2D(2, 0),
            "priority": TaskPriority.PRIORITY_HIGH, "created_at": 10.0,
        }))

        # First tick assigns task
        await loop.submit(Event("TICK", {"current_time": 10.0}))
        assert "t_hold" in loop.core._active_tasks
        assigned_task = loop.core._active_tasks["t_hold"]
        goal_uuid = assigned_task.goal_uuid

        # Executor explicitly rejects goal
        reject_event = Event("GOAL_REJECTED", {
            "task_id": "t_hold",
            "robot_id": "r1",
            "assignment_epoch": assigned_task.assignment_epoch,
            "goal_uuid": goal_uuid,
            "reason": "Capacity limit exceeded in Executor",
            "held_at": 15.0,
        })
        outcome = await loop.submit(reject_event)
        assert outcome == "APPLIED"

        # Verify hold is registered in core and store
        assert loop.core.has_review_hold("t_hold") is True
        row = store.connection.execute("SELECT * FROM task_review_holds WHERE task_id='t_hold'").fetchone()
        assert row is not None
        assert row["reason"] == "Capacity limit exceeded in Executor"
        assert row["held_at"] == 15.0

        # Scheduler ticks must NOT assign t_hold to r1 or any robot
        await loop.submit(Event("TICK", {"current_time": 20.0}))
        assert "t_hold" not in loop.core._active_tasks

        # Operator inspects and clears the review hold
        clear_event = Event("CLEAR_REVIEW_HOLD", {"task_id": "t_hold"})
        assert await loop.submit(clear_event) == "APPLIED"

        assert loop.core.has_review_hold("t_hold") is False
        assert store.connection.execute("SELECT 1 FROM task_review_holds WHERE task_id='t_hold'").fetchone() is None

        # Next scheduler tick: r1 confirms IDLE via RobotStatus, then evaluates and assigns t_hold again!
        await loop.submit(Event("ROBOT_STATUS", {
            "robot_id": "r1", "status_seq": 2, "publisher_session_id": sess,
            "current_epoch": 1, "state": 1, "current_phase": 0, "is_loaded": False,
            "pose": Pose2D(), "battery_soc_percent": 100, "battery_energy_wh": 100,
            "current_task_id": None, "timestamp_sec": 24.0,
        }))
        await loop.submit(Event("TICK", {"current_time": 25.0}))
        assert "t_hold" in loop.core._active_tasks

        await loop.close()
        store.close()

        # Database with holds or data cannot be restarted without reset
        new_store = SQLiteStore(db_path)
        new_core = FleetManagerCore(SimpleRoutes(), Pose2D())
        new_core.register_robot("r1")
        with pytest.raises(ScenarioResetRequired):
            FleetEventLoop(new_store, new_core)
        new_store.close()

    asyncio.run(scenario())
