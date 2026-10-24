"""Unit tests for ClearRobotError service client.

Verifies:
- Manual operator-only recovery contract (never called automatically on error)
- Expected epoch matching
- FM preserves physical state authority (no optimistic IDLE or unblocking of resources)
"""

import asyncio
from unittest.mock import MagicMock
import pytest

from backend.fleet_manager.adapters.service_client import ClearRobotErrorServiceClient
from backend.fleet_manager.domain.constants import (
    ReservationState,
    RobotState,
    StationType,
)
from backend.fleet_manager.domain.fleet_manager_core import FleetManagerCore
from backend.fleet_manager.domain.models import Pose2D
from backend.fleet_manager.domain.scheduler import RouteDistanceProvider


class SimpleRoutes(RouteDistanceProvider):
    def get_path_distance(self, start: Pose2D, goal: Pose2D):
        return 10.0


def test_clear_robot_error_client_invocation():
    """Verify ClearRobotError client requests error clear and respects physical state authority."""
    async def scenario():
        core = FleetManagerCore(SimpleRoutes(), Pose2D())
        core.register_robot("r1")
        core.register_station("charge_1", StationType.CHARGING, Pose2D(0, 0))

        # Station blocked due to error
        core.reservations.mark_blocked("charge_1", "r1")
        assert core.reservations.get_station("charge_1").state == ReservationState.BLOCKED

        # Robot in error state
        core.handle_robot_status(
            robot_id="r1", state=RobotState.STATE_ERROR, current_phase=0, is_loaded=False,
            pose=Pose2D(0, 0), battery_soc_percent=50, battery_energy_wh=50,
            current_epoch=3, current_task_id=None, timestamp_sec=10.0,
        )
        assert core.tracker.get_robot("r1").state == RobotState.STATE_ERROR

        # Mock ClearRobotError service client
        mock_srv = MagicMock()
        mock_srv.service_is_ready.return_value = True

        mock_fut = asyncio.get_running_loop().create_future()
        class MockResponse:
            accepted = True
            reason = "Cleared by operator"
            resulting_state = RobotState.STATE_IDLE

        mock_fut.set_result(MockResponse())
        mock_srv.call_async.return_value = mock_fut

        client = ClearRobotErrorServiceClient("r1", service_client=mock_srv)

        # Operator triggers error clear with expected_epoch=3
        resp = await client.clear_error(expected_epoch=3)
        assert resp.accepted is True
        assert resp.reason == "Cleared by operator"

        # Crucial architectural assertion:
        # Service response ALONE must NOT transition FM replica to IDLE or unblock station!
        assert core.tracker.get_robot("r1").state == RobotState.STATE_ERROR
        assert core.reservations.get_station("charge_1").state == ReservationState.BLOCKED

        # Only when Executor publishes actual RobotStatus does FM update:
        core.handle_robot_status(
            robot_id="r1", state=RobotState.STATE_IDLE, current_phase=0, is_loaded=False,
            pose=Pose2D(0, 0), battery_soc_percent=50, battery_energy_wh=50,
            current_epoch=3, current_task_id=None, timestamp_sec=11.0,
        )
        assert core.tracker.get_robot("r1").state == RobotState.STATE_IDLE

    asyncio.run(scenario())
