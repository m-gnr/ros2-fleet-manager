"""ClearRobotError ROS 2 service client adapter.

Conforms strictly to:
- Physical state authority: Fleet Manager never marks robot IDLE or clears BLOCKED resources upon service return.
- Manual operator recovery only: Service is strictly called upon explicit operator request, never automatically on error.
- Monotonic expected_epoch matching: Preserves epoch safety contracts.
"""

import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ClearRobotErrorServiceClient:
    """Service client wrapper for ClearRobotError.srv."""

    def __init__(self, robot_id: str, service_client: Any = None) -> None:
        self.robot_id = robot_id
        self.service_client = service_client

    def set_service_client(self, client: Any) -> None:
        self.service_client = client

    async def clear_error(
        self,
        expected_epoch: int,
        timeout_sec: float = 5.0,
    ) -> Any:
        """Call ClearRobotError service on explicit operator command.
        
        Does NOT transition Fleet Manager domain state or clear BLOCKED resources.
        Robot Executor remains the sole physical state authority and will publish
        updated RobotStatus telemetry following state transition.
        """
        if self.service_client is None:
            raise RuntimeError(f"ClearRobotError service client for {self.robot_id} not initialized")

        try:
            from fleet_interfaces.srv import ClearRobotError
            request = ClearRobotError.Request()
            request.robot_id = self.robot_id
            request.expected_epoch = expected_epoch
        except ImportError:
            class MockRequest:
                pass
            request = MockRequest()
            request.robot_id = self.robot_id
            request.expected_epoch = expected_epoch

        future = self.service_client.call_async(request)
        start_t = asyncio.get_event_loop().time()
        while not future.done():
            if (asyncio.get_event_loop().time() - start_t) > timeout_sec:
                raise TimeoutError(f"ClearRobotError call timed out after {timeout_sec:.1f}s")
            await asyncio.sleep(0.05)

        response = future.result()
        logger.info(
            "ClearRobotError response for %s: accepted=%s, reason='%s', resulting_state=%s",
            self.robot_id, response.accepted, response.reason, response.resulting_state
        )
        return response
