"""Unit tests for RobotStatus subscriber, session order, and SESSION_BLOCKED gating.

Verifies C3.3-DEC-01 & C3.3.2-DEC-04:
- status_seq ordering within same session (duplicates / regressions are STALE)
- publisher_session_id recording on clean startup
- Clean startup gating (robot must be verified STATE_IDLE, unloaded, without task)
- Oturum Değişiminde Mülkiyetin Korunması:
  - Session change transitions robot to SESSION_BLOCKED
  - Active task is NOT marked FAILED
  - Occupied station is NOT marked FREE
  - New assignments and releases are blocked
- Thread-safe bridging to single asyncio consumer
"""

import asyncio
from dataclasses import dataclass
from typing import Any
import uuid
import pytest

from backend.fleet_manager.adapters.status_subscriber import (
    RobotStatusSubscriberBridge,
    parse_uuid_to_str,
    quaternion_to_yaw,
    ros_robot_status_to_dict,
)
from backend.fleet_manager.domain.constants import (
    ReservationState,
    RobotState,
    StationType,
    TaskPhase,
    TaskPriority,
)
from backend.fleet_manager.domain.fleet_manager_core import FleetManagerCore
from backend.fleet_manager.domain.models import Pose2D
from backend.fleet_manager.domain.scheduler import RouteDistanceProvider
from backend.fleet_manager.event_loop import Event, FleetEventLoop
from backend.fleet_manager.persistence.store import SQLiteStore


class SimpleRoutes(RouteDistanceProvider):
    def get_path_distance(self, start: Pose2D, goal: Pose2D):
        return 10.0


@dataclass
class MockPosition:
    x: float = 1.0
    y: float = 2.0
    z: float = 0.0


@dataclass
class MockOrientation:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    qw: float = 1.0

    @property
    def w(self):
        return self.qw


@dataclass
class MockPose:
    position: MockPosition = None
    orientation: MockOrientation = None

    def __post_init__(self):
        if self.position is None:
            self.position = MockPosition()
        if self.orientation is None:
            self.orientation = MockOrientation()


@dataclass
class MockHeader:
    stamp_sec: int = 100
    stamp_nanosec: int = 500000000
    frame_id: str = "map"

    @property
    def stamp(self):
        class Stamp:
            sec = self.stamp_sec
            nanosec = self.stamp_nanosec
        return Stamp()


@dataclass
class MockUUID:
    uuid: bytes


@dataclass
class MockRobotStatusMsg:
    robot_id: str = "robot_1"
    status_seq: int = 1
    publisher_session_id: MockUUID = None
    current_epoch: int = 0
    state: int = RobotState.STATE_IDLE
    current_phase: int = TaskPhase.PHASE_NONE
    is_loaded: bool = False
    pose: Any = None
    battery_soc_percent: float = 95.0
    battery_energy_wh: float = 95.0
    current_task_id: str = ""
    header: MockHeader = None

    def __post_init__(self):
        if self.publisher_session_id is None:
            self.publisher_session_id = MockUUID(uuid=list(uuid.uuid4().bytes))
        if self.pose is None:
            class MockPoseStamped:
                header = MockHeader()
                pose = MockPose()
            self.pose = MockPoseStamped()
        if self.header is None:
            self.header = MockHeader()


def test_quaternion_to_yaw_and_uuid_parsing():
    """Verify planar angle conversion and UUID string extraction."""
    # 0 radians yaw
    assert pytest.approx(quaternion_to_yaw(0.0, 0.0, 0.0, 1.0)) == 0.0
    # 90 deg yaw -> sin(pi/4) approx 0.7071
    assert pytest.approx(quaternion_to_yaw(0.0, 0.0, 0.7071068, 0.7071068), 0.001) == 1.57079

    test_u = uuid.uuid4()
    assert parse_uuid_to_str(test_u.hex) == str(test_u)
    assert parse_uuid_to_str(MockUUID(uuid=list(test_u.bytes))) == str(test_u)


def test_ros_robot_status_to_dict_extraction():
    """Verify dictionary parsing from ROS message mock."""
    session_u = uuid.uuid4()
    msg = MockRobotStatusMsg(
        robot_id="robot_1",
        status_seq=42,
        publisher_session_id=MockUUID(uuid=list(session_u.bytes)),
        current_epoch=5,
        state=RobotState.STATE_EXECUTING_TASK,
        current_phase=TaskPhase.PHASE_MOVING_TO_PICKUP,
        is_loaded=False,
        battery_soc_percent=88.5,
        battery_energy_wh=88.5,
        current_task_id="task_123",
    )
    d = ros_robot_status_to_dict(msg)
    assert d["robot_id"] == "robot_1"
    assert d["status_seq"] == 42
    assert d["publisher_session_id"] == str(session_u)
    assert d["current_epoch"] == 5
    assert d["state"] == RobotState.STATE_EXECUTING_TASK
    assert d["current_phase"] == TaskPhase.PHASE_MOVING_TO_PICKUP
    assert d["current_task_id"] == "task_123"
    assert d["timestamp_sec"] == 100.5


def test_status_seq_duplicate_and_regression_is_stale(tmp_path):
    """Verify status_seq strictly checks monotonicity in the same session."""
    async def scenario():
        db_path = str(tmp_path / "test_status.db")
        store = SQLiteStore(db_path)
        core = FleetManagerCore(SimpleRoutes(), Pose2D())
        core.register_robot("robot_1")
        loop = FleetEventLoop(store, core)
        await loop.start()

        sess = str(uuid.uuid4())
        # First message seq=1
        e1 = Event("ROBOT_STATUS", {
            "robot_id": "robot_1", "status_seq": 1, "publisher_session_id": sess,
            "current_epoch": 0, "state": RobotState.STATE_IDLE, "current_phase": 0,
            "is_loaded": False, "pose": Pose2D(), "battery_soc_percent": 100,
            "battery_energy_wh": 100, "current_task_id": None, "timestamp_sec": 10.0,
        })
        assert await loop.submit(e1) == "APPLIED"

        # Advance seq=5
        e2 = Event("ROBOT_STATUS", {
            "robot_id": "robot_1", "status_seq": 5, "publisher_session_id": sess,
            "current_epoch": 0, "state": RobotState.STATE_IDLE, "current_phase": 0,
            "is_loaded": False, "pose": Pose2D(), "battery_soc_percent": 100,
            "battery_energy_wh": 100, "current_task_id": None, "timestamp_sec": 11.0,
        })
        assert await loop.submit(e2) == "APPLIED"

        # Duplicate status_seq=5 (new message with same sequence) -> STALE
        assert await loop.submit(Event("ROBOT_STATUS", dict(e2.payload))) == "STALE"

        # Regression seq=4 -> STALE
        e3 = Event("ROBOT_STATUS", {
            "robot_id": "robot_1", "status_seq": 4, "publisher_session_id": sess,
            "current_epoch": 0, "state": RobotState.STATE_IDLE, "current_phase": 0,
            "is_loaded": False, "pose": Pose2D(), "battery_soc_percent": 100,
            "battery_energy_wh": 100, "current_task_id": None, "timestamp_sec": 12.0,
        })
        assert await loop.submit(e3) == "STALE"

        await loop.close()
        store.close()

    asyncio.run(scenario())


def test_clean_startup_verification_gate(tmp_path):
    """Verify clean startup gates assignment until robot confirmed STATE_IDLE, unloaded, and no task."""
    async def scenario():
        db_path = str(tmp_path / "test_clean_startup.db")
        store = SQLiteStore(db_path)
        core = FleetManagerCore(SimpleRoutes(), Pose2D())
        core.register_robot("robot_1")
        loop = FleetEventLoop(store, core)
        await loop.start()

        sess = str(uuid.uuid4())
        # Robot starts in dirty state (is_loaded=True)
        e_dirty = Event("ROBOT_STATUS", {
            "robot_id": "robot_1", "status_seq": 1, "publisher_session_id": sess,
            "current_epoch": 0, "state": RobotState.STATE_IDLE, "current_phase": 0,
            "is_loaded": True, "pose": Pose2D(), "battery_soc_percent": 100,
            "battery_energy_wh": 100, "current_task_id": None, "timestamp_sec": 10.0,
        })
        assert await loop.submit(e_dirty) == "APPLIED"

        # Queue a task
        await loop.submit(Event("SUBMIT_TASK", {
            "task_id": "t1", "pickup_pose": Pose2D(1, 0), "dropoff_pose": Pose2D(2, 0),
            "priority": TaskPriority.PRIORITY_LOW, "created_at": 10.0,
        }))

        # Schedule tick: robot is NOT eligible because initial status was dirty
        await loop.submit(Event("TICK", {"current_time": 10.0}))
        assert "t1" not in loop.core._active_tasks

        # Now clean confirmation arrives
        e_clean = Event("ROBOT_STATUS", {
            "robot_id": "robot_1", "status_seq": 2, "publisher_session_id": sess,
            "current_epoch": 0, "state": RobotState.STATE_IDLE, "current_phase": 0,
            "is_loaded": False, "pose": Pose2D(), "battery_soc_percent": 100,
            "battery_energy_wh": 100, "current_task_id": None, "timestamp_sec": 11.0,
        })
        assert await loop.submit(e_clean) == "APPLIED"

        # Schedule tick: robot is now verified and eligible!
        await loop.submit(Event("TICK", {"current_time": 11.0}))
        assert "t1" in loop.core._active_tasks
        assert loop.core._active_tasks["t1"].assigned_robot_id == "robot_1"

        await loop.close()
        store.close()

    asyncio.run(scenario())


def test_session_change_preserves_ownership_and_blocks_robot(tmp_path):
    """Verify session change transitions robot to SESSION_BLOCKED without FAILED or FREE."""
    async def scenario():
        db_path = str(tmp_path / "test_session_change.db")
        store = SQLiteStore(db_path)
        core = FleetManagerCore(SimpleRoutes(), Pose2D())
        core.register_robot("robot_1")
        core.register_station("dock_1", StationType.CHARGING, Pose2D(0, 0))
        loop = FleetEventLoop(store, core)
        await loop.start()

        sess_1 = str(uuid.uuid4())
        # Initial status
        await loop.submit(Event("ROBOT_STATUS", {
            "robot_id": "robot_1", "status_seq": 1, "publisher_session_id": sess_1,
            "current_epoch": 0, "state": RobotState.STATE_IDLE, "current_phase": 0,
            "is_loaded": False, "pose": Pose2D(0, 0), "battery_soc_percent": 100,
            "battery_energy_wh": 100, "current_task_id": None, "timestamp_sec": 10.0,
        }))

        # Reserve station and assign task
        await loop.submit(Event("RESERVE", {"station_id": "dock_1", "robot_id": "robot_1"}))
        await loop.submit(Event("SUBMIT_TASK", {
            "task_id": "task_active", "pickup_pose": Pose2D(1, 0), "dropoff_pose": Pose2D(2, 0),
            "priority": TaskPriority.PRIORITY_MEDIUM, "created_at": 10.0,
        }))
        await loop.submit(Event("TICK", {"current_time": 10.0}))

        assert "task_active" in loop.core._active_tasks
        active_task = loop.core._active_tasks["task_active"]
        assert loop.core.reservations.get_station("dock_1").reserved_by_robot_id == "robot_1"

        # Executor restarts! New session UUID arrives
        sess_2 = str(uuid.uuid4())
        e_restarted = Event("ROBOT_STATUS", {
            "robot_id": "robot_1", "status_seq": 1, "publisher_session_id": sess_2,
            "current_epoch": 0, "state": RobotState.STATE_IDLE, "current_phase": 0,
            "is_loaded": False, "pose": Pose2D(0, 0), "battery_soc_percent": 100,
            "battery_energy_wh": 100, "current_task_id": None, "timestamp_sec": 15.0,
        })
        outcome = await loop.submit(e_restarted)
        assert outcome == "SESSION_BLOCKED"

        # Verify C3.3.2-DEC-04 invariant:
        # 1. Active task is NOT marked FAILED!
        assert "task_active" in loop.core._active_tasks
        assert "task_active" not in loop.core._failed_tasks

        # 2. Reserved station is NOT marked FREE!
        st = loop.core.reservations.get_station("dock_1")
        assert st.state != ReservationState.FREE
        assert st.reserved_by_robot_id == "robot_1"

        # 3. Robot is marked session_blocked and cannot accept new assignments
        assert loop.core.tracker.get_robot("robot_1").session_blocked is True
        await loop.submit(Event("SUBMIT_TASK", {
            "task_id": "task_new", "pickup_pose": Pose2D(1, 0), "dropoff_pose": Pose2D(2, 0),
            "priority": TaskPriority.PRIORITY_HIGH, "created_at": 20.0,
        }))
        await loop.submit(Event("TICK", {"current_time": 20.0}))
        assert "task_new" not in loop.core._active_tasks

        await loop.close()
        store.close()

    asyncio.run(scenario())


def test_robot_status_subscriber_bridge_threadsafety(tmp_path):
    """Verify RobotStatusSubscriberBridge thread-safely forwards messages to FleetEventLoop."""
    async def scenario():
        db_path = str(tmp_path / "test_bridge.db")
        store = SQLiteStore(db_path)
        core = FleetManagerCore(SimpleRoutes(), Pose2D())
        core.register_robot("robot_1")
        loop = FleetEventLoop(store, core)
        await loop.start()

        recorded_outcomes = []
        bridge = RobotStatusSubscriberBridge(
            consumer=loop,
            loop=asyncio.get_running_loop(),
            on_outcome=lambda outcome, p: recorded_outcomes.append((outcome, p["status_seq"])),
        )

        sess = str(uuid.uuid4())
        msg = MockRobotStatusMsg(
            robot_id="robot_1",
            status_seq=1,
            publisher_session_id=MockUUID(uuid=list(uuid.UUID(sess).bytes)),
            current_epoch=0,
            state=RobotState.STATE_IDLE,
            current_phase=0,
            is_loaded=False,
            current_task_id="",
        )

        fut = bridge.handle_status_msg(msg)
        outcome = await asyncio.wrap_future(fut)
        assert outcome == "APPLIED"

        await asyncio.sleep(0.05)
        assert len(recorded_outcomes) == 1
        assert recorded_outcomes[0] == ("APPLIED", 1)

        await loop.close()
        store.close()

    asyncio.run(scenario())
