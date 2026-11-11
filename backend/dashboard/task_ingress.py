"""Session-fenced catalog task submission to the Fleet Manager owner loop over a local socket."""
import asyncio
from contextlib import asynccontextmanager, suppress
from dataclasses import asdict
import json
from pathlib import Path
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.fleet_manager.domain import Pose2D, TaskPriority
from backend.fleet_manager.event_loop import Event
from fleet_config.occupancy import profile_digest

MAX_REQUEST_BYTES = 4096


class TaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    request_id: str = Field(pattern=r"^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
    source_session_id: str = Field(min_length=1, max_length=128)
    profile_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    pickup_id: str = Field(min_length=1, max_length=80)
    dropoff_id: str = Field(min_length=1, max_length=80)
    priority: Literal["LOW", "MEDIUM", "HIGH"]


def endpoints(config, request):
    catalog = {point.id: point for point in config.warehouse.transfer_points}
    if request.pickup_id == request.dropoff_id:
        raise ValueError("Alım ve teslim noktaları farklı olmalıdır")
    poses = []
    for role, id_ in (("pickup", request.pickup_id), ("dropoff", request.dropoff_id)):
        point = catalog.get(id_)
        if point is None or not point.accepts(role):
            raise ValueError("Seçilen nokta bu işlem için kullanılamıyor")
        poses.append(Pose2D(**point.pose.model_dump()))
    return poses


async def send_task(path, request):
    reader, writer = await asyncio.open_unix_connection(str(path), limit=MAX_REQUEST_BYTES)
    try:
        writer.write(request.model_dump_json().encode() + b"\n")
        await writer.drain()
        return json.loads(await asyncio.wait_for(reader.readline(), timeout=5))
    finally:
        writer.close()
        await writer.wait_closed()


@asynccontextmanager
async def task_server(consumer, path, config, session):
    """All state changes remain SUBMIT_TASK events owned by FleetEventLoop."""
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"Task socket already exists: {path}")
    lock = asyncio.Lock()
    clients = set()

    async def handle(reader, writer):
        task = asyncio.current_task()
        if len(clients) >= 8:
            writer.close()
            return
        clients.add(task)
        try:
            raw = await asyncio.wait_for(reader.readline(), timeout=3)
            request = TaskRequest.model_validate_json(raw)
            if request.source_session_id != session or request.profile_digest != profile_digest(config):
                raise ValueError("Filo oturumu değişti. Nokta listesini yenileyin")
            pickup, dropoff = endpoints(config, request)
            priority = TaskPriority['PRIORITY_' + request.priority]
            task_id = 'web-' + request.request_id
            async with lock:
                # Read on the owner event loop. SQLite writes remain inside consumer.submit.
                row = consumer.store.connection.execute("SELECT snapshot FROM tasks WHERE task_id=?", (task_id,)).fetchone()
                if row:
                    saved = json.loads(row[0])
                    if (saved['pickup_pose'] != asdict(pickup) or saved['dropoff_pose'] != asdict(dropoff)
                            or saved['priority'] != priority):
                        raise ValueError("İstek kimliği farklı bir görev için kullanılmış")
                    outcome = 'DUPLICATE'
                else:
                    outcome = await consumer.submit(Event('SUBMIT_TASK', dict(
                        task_id=task_id, pickup_pose=pickup, dropoff_pose=dropoff,
                        priority=priority, created_at=time.monotonic(),
                    ), event_id='dashboard-' + request.request_id))
            response = dict(task_id=task_id, outcome=outcome)
        except (ValueError, ValidationError, asyncio.TimeoutError):
            response = dict(error="Görev isteği, nokta seçimi veya filo oturumu geçersiz")
        except Exception:
            response = dict(error="Görev kabulü doğrulanamadı. Aynı istek kimliğiyle tekrar deneyin")
        finally:
            clients.discard(task)
        try:
            writer.write(json.dumps(response).encode() + b"\n")
            await writer.drain()
        except (ConnectionError, OSError):
            pass
        finally:
            writer.close()
            with suppress(ConnectionError, OSError):
                await writer.wait_closed()

    server = await asyncio.start_unix_server(handle, path=str(path), limit=MAX_REQUEST_BYTES)
    inode = path.stat().st_ino
    try:
        path.chmod(0o600)
        yield
    finally:
        server.close()
        await server.wait_closed()
        await asyncio.gather(*clients, return_exceptions=True)
        if path.exists() and path.stat().st_ino == inode:
            path.unlink()
