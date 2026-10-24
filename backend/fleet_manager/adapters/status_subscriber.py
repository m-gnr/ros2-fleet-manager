"""RobotStatus subscriber and asyncio consumer bridge.

Conforms strictly to:
- C3.3-DEC-01 & C3.3.2-DEC-04: status_seq, publisher_session_id, session safety, STALE/SESSION_BLOCKED.
- C3.3.2-DEC-06: Thread-safe bridging from rclpy callback pool to asyncio.Queue via run_coroutine_threadsafe.
- Executor physical state authority: FM ingests status, never writes directly to DB or domain from ROS thread.
"""

import asyncio
import logging
import math
import time
from typing import Any, Callable, Optional
import uuid

from ..domain.models import Pose2D
from ..event_loop import Event

logger = logging.getLogger(__name__)


def parse_uuid_to_str(uuid_field: Any) -> str:
    """Convert unique_identifier_msgs/UUID or bytes/list/str to standard UUID string."""
    if isinstance(uuid_field, str):
        return str(uuid.UUID(uuid_field))
    if hasattr(uuid_field, "uuid"):
        raw = uuid_field.uuid
    else:
        raw = uuid_field
    return str(uuid.UUID(bytes=bytes(raw)))


def quaternion_to_yaw(qx: float, qy: float, qz: float, qw: float) -> float:
    """Extract planar yaw angle in radians from orientation quaternion."""
    siny_cosp = 2.0 * (qw * qz + qx * qy)
    cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
    return math.atan2(siny_cosp, cosy_cosp)


def ros_robot_status_to_dict(msg: Any, receipt_time_sec: Optional[float] = None) -> dict:
    """Extract primitive Python dictionary from fleet_interfaces.msg.RobotStatus."""
    pos = msg.pose.pose.position
    ori = msg.pose.pose.orientation
    yaw = quaternion_to_yaw(ori.x, ori.y, ori.z, ori.w)
    frame_id = msg.pose.header.frame_id or "map"
    if receipt_time_sec is not None:
        timestamp_sec = float(receipt_time_sec)
    else:
        timestamp_sec = float(msg.header.stamp.sec) + float(msg.header.stamp.nanosec) * 1e-9

    session_str = parse_uuid_to_str(msg.publisher_session_id)

    return {
        "robot_id": msg.robot_id,
        "status_seq": int(msg.status_seq),
        "publisher_session_id": session_str,
        "current_epoch": int(msg.current_epoch),
        "state": int(msg.state),
        "current_phase": int(msg.current_phase),
        "is_loaded": bool(msg.is_loaded),
        "pose": Pose2D(x=pos.x, y=pos.y, yaw=yaw, frame_id=frame_id),
        "battery_soc_percent": float(msg.battery_soc_percent),
        "battery_energy_wh": float(msg.battery_energy_wh),
        "current_task_id": msg.current_task_id if msg.current_task_id else None,
        "timestamp_sec": timestamp_sec,
    }


class RobotStatusSubscriberBridge:
    """Bridge for receiving RobotStatus ROS messages and forwarding to FleetEventLoop."""

    def __init__(
        self,
        consumer: Any,
        loop: asyncio.AbstractEventLoop,
        on_outcome: Optional[Callable[[str, dict], None]] = None,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self.consumer = consumer
        self.loop = loop
        self.on_outcome = on_outcome
        self.clock = clock or time.monotonic

    def handle_status_msg(self, msg: Any) -> Any:
        """ROS callback entrypoint. Thread-safely dispatches event to asyncio consumer."""
        receipt_time = self.clock() if self.clock is not None else None
        payload = ros_robot_status_to_dict(msg, receipt_time_sec=receipt_time)
        event = Event(kind="ROBOT_STATUS", payload=payload)
        
        future = asyncio.run_coroutine_threadsafe(
            self.consumer.submit(event),
            self.loop,
        )
        if self.on_outcome is not None:
            def _done_cb(fut):
                try:
                    outcome = fut.result()
                    self.on_outcome(outcome, payload)
                except Exception as exc:
                    logger.error("Error submitting ROBOT_STATUS event: %s", exc)
            future.add_done_callback(_done_cb)
        return future
