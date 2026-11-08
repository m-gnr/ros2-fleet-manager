"""C5 uses committed product state and a bounded, read-only WebSocket feed."""
import asyncio
from contextlib import closing
from datetime import datetime, timezone
import json
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError
from starlette.websockets import WebSocketDisconnect

from backend.dashboard import api, publisher
from backend.dashboard.models import MAX_BYTES, SOURCE_TTL_NS, FleetSnapshot, SourceSnapshot, WireSnapshot
from backend.fleet_manager.builder import build_fleet_manager_from_config
from backend.fleet_manager.domain import Pose2D, RobotState
from backend.fleet_manager.event_loop import Event, FleetEventLoop
from backend.fleet_manager.persistence.store import SQLiteStore

ORIGIN = "http://127.0.0.1:32101"
URL = "http://127.0.0.1"


def test_committed_physical_status_battery_and_ownership(tmp_path):
    async def scenario(store):
        core, robot_ids = build_fleet_manager_from_config()
        robot_id = robot_ids[0]
        now = [15.0]
        sim_ns = [10_000_000_000]
        consumer = FleetEventLoop(store, core, clock=lambda: now[0])
        consumer.bind_battery_clock(lambda: sim_ns[0])
        consumer.enable_dashboard_sampling()
        await consumer.start()
        session = str(uuid4())

        def snapshot():
            return publisher.project(consumer.dashboard_sample(), "scenario", 1, datetime.now(timezone.utc))

        async def status(seq, **changes):
            payload = dict(robot_id=robot_id, status_seq=seq, publisher_session_id=session,
                           current_epoch=0, current_task_id=None, state=RobotState.STATE_IDLE, current_phase=0,
                           is_loaded=False, timestamp_sec=now[0], source_status_ns=sim_ns[0],
                           pose=Pose2D(3, 4, 1.5), pose_sample_ns=sim_ns[0], pose_valid_until=now[0] + 2,
                           battery_soc_percent=80.0, battery_energy_wh=80.0,
                           battery_sample_ns=sim_ns[0], battery_valid_until=now[0] + 2)
            payload.update(changes)
            return await consumer.submit(Event("ROBOT_STATUS", payload))

        try:
            initial = snapshot().robots[0]
            assert (initial.telemetry, initial.state, initial.pose, initial.battery_soc_percent) == (
                "NO_DATA", None, None, None,
            )
            assert await status(1) == "APPLIED"
            fleet = snapshot()
            robot = fleet.robots[0]
            assert (robot.telemetry, robot.state, robot.pose.x, robot.battery_soc_percent,
                    robot.battery_energy_wh, robot.battery_sim_ns) == ("LIVE", "IDLE", 3, 80, 80, "10000000000")
            assert len(fleet.stations) == 2 and all(station.state == "FREE" for station in fleet.stations)
            assert await consumer.submit(Event("SUBMIT_TASK", dict(
                task_id="operator-test", pickup_pose=Pose2D(1, 1), dropoff_pose=Pose2D(2, 2),
                created_at=now[0],
            ))) == "APPLIED"
            fleet = snapshot()
            assert fleet.tasks[0].status == "QUEUED" and fleet.task_counts.queued == 1
            assert fleet.tasks[0].pickup.frame_id == "map"
            assert await status(1, pose=Pose2D(7, 8)) == "STALE"
            assert snapshot().robots[0].pose.x == 3

            # The observer sees neither rolled-back status nor invalid-frame coordinates.
            trigger = """CREATE TRIGGER reject_status BEFORE UPDATE ON robots
                         BEGIN SELECT RAISE(ABORT, 'test rollback'); END;"""
            store.connection.executescript(trigger)
            with pytest.raises(Exception, match="test rollback"):
                await status(2, state=RobotState.STATE_ERROR)
            store.connection.execute("DROP TRIGGER reject_status")
            assert snapshot().robots[0].state == "IDLE"
            now[0] += 0.5
            sim_ns[0] += 500_000_000
            assert await status(2, pose=Pose2D(8, 9, 0, "odom"), battery_valid_until=0) == "APPLIED"
            invalid = snapshot().robots[0]
            assert invalid.telemetry == "LIVE" and invalid.pose_reliability == "STALE" and invalid.pose.x == 3
            assert invalid.battery_reliability == "UNAVAILABLE" and invalid.battery_soc_percent is None
            assert invalid.charging == "UNAVAILABLE"
            assert await status(3, current_epoch=1, pose=Pose2D(2, 3)) == "APPLIED"
            assert await status(4, current_epoch=0, state=RobotState.STATE_ERROR) == "STALE"
            assert snapshot().robots[0].state == "IDLE"
            now[0] += 2.1
            assert snapshot().robots[0].telemetry == "STALE"
            assert snapshot().robots[0].battery_soc_percent is None
            assert await status(1, publisher_session_id=str(uuid4())) == "SESSION_BLOCKED"
            blocked = snapshot().robots[0]
            assert blocked.telemetry == blocked.pose_reliability == blocked.battery_reliability == "BLOCKED"
            assert blocked.pose.x == 2 and blocked.battery_energy_wh is None
            assert store.connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        finally:
            await consumer.close()

    with closing(SQLiteStore(tmp_path / "fleet.sqlite3")) as store:
        asyncio.run(scenario(store))


def make_source(seq, *, source="producer", ns=None):
    return SourceSnapshot(
        captured_monotonic_ns=time.monotonic_ns() if ns is None else ns,
        fleet=FleetSnapshot(source_session_id=source, sequence=seq, generated_at_utc=datetime.now(timezone.utc),
                            robots=(), tasks=(), stations=(), task_counts=dict(total=0, queued=0, active=0)),
    )


def write_source(path, sequence, **kwargs):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(make_source(sequence, **kwargs).model_dump_json())
    temporary.replace(path)


def wait_for_api(client, seq):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        response = client.get("/api/fleet")
        if response.status_code == 200 and response.json()["sequence"] == seq:
            return response
        time.sleep(0.025)
    pytest.fail(f"sequence {seq} unavailable")


def test_http_readonly_origin_and_restart(tmp_path):
    path = tmp_path / "snapshot.json"
    app = api.create_app(path, origins={ORIGIN})
    with TestClient(app, base_url=URL) as client:
        assert client.get("/api/fleet").status_code == 503
        write_source(path, 1)
        response = wait_for_api(client, 1)
        old = WireSnapshot.model_validate(response.json())
        assert response.headers["cache-control"] == "no-store"
        assert {(route.path, tuple(route.methods or ())) for route in app.routes if hasattr(route, "methods")} == {
            (path, ("GET",)) for path in (
                "/api/health", "/api/fleet", "/api/robots", "/api/robots/{robot_id}", "/api/tasks", "/api/stations",
                "/api/warehouse-layout",
            )
        }
        assert client.post("/api/tasks", json={}).status_code == 405
        assert client.get("/api/robots/missing").status_code == 404
        assert "access-control-allow-origin" not in client.get("/api/health", headers={"origin": "https://foreign.test"}).headers
        assert client.get("/api/health", headers={"origin": ORIGIN}).headers["access-control-allow-origin"] == ORIGIN
        assert client.get("/api/health", headers={"host": "foreign.test"}).status_code == 400
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("ws://127.0.0.1/ws/fleet", headers={"origin": "https://foreign.test"}):
                pass
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("ws://127.0.0.1/ws/fleet"):
                pass

    with TestClient(api.create_app(path, origins={ORIGIN}), base_url=URL) as client:
        newer = WireSnapshot.model_validate(wait_for_api(client, 1).json())
        assert newer.backend_session_id != old.backend_session_id
        assert newer.source_session_id == old.source_session_id
    write_source(path, 1, ns=time.monotonic_ns() - SOURCE_TTL_NS - 1)
    with TestClient(api.create_app(path, origins={ORIGIN}), base_url=URL) as client:
        assert client.get("/api/fleet").status_code == 503
        with client.websocket_connect("ws://127.0.0.1/ws/fleet", headers={"origin": ORIGIN}) as socket:
            with pytest.raises(WebSocketDisconnect) as closed:
                socket.receive_text()
            assert closed.value.code == 1013


def test_socket_initial_latest_coalescing_reconnect_and_limits(tmp_path):
    path = tmp_path / "snapshot.json"
    write_source(path, 1)
    app = api.create_app(path, origins={ORIGIN}, max_clients=1)
    with TestClient(app, base_url=URL) as client:
        wait_for_api(client, 1)
        headers = {"origin": ORIGIN}
        with client.websocket_connect("ws://127.0.0.1/ws/fleet", headers=headers) as socket:
            assert socket.receive_json()["sequence"] == 1
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect("ws://127.0.0.1/ws/fleet", headers=headers):
                    pass
            write_source(path, 4)
            assert socket.receive_json()["sequence"] == 4
            write_source(path, 3)
            assert client.get("/api/fleet").json()["sequence"] == 4
            socket.send_text("command")
            with pytest.raises(WebSocketDisconnect) as closed:
                socket.receive_text()
            assert closed.value.code == 1008
        write_source(path, 5)
        wait_for_api(client, 5)
        with client.websocket_connect("ws://127.0.0.1/ws/fleet", headers=headers) as socket:
            assert socket.receive_json()["sequence"] == 5
            write_source(path, 1, source="restarted")
            with pytest.raises(WebSocketDisconnect) as closed:
                socket.receive_text()
            assert closed.value.code == 1013
        with client.websocket_connect("ws://127.0.0.1/ws/fleet", headers=headers) as socket:
            assert socket.receive_json()["source_session_id"] == "restarted"


def test_slow_client_bounded_send_and_schema(monkeypatch, tmp_path):
    class SlowSocket:
        sent = 0
        closed = None

        async def receive(self):
            await asyncio.Future()

        async def send_text(self, _value):
            self.sent += 1
            await asyncio.Future()

        async def close(self, code):
            self.closed = code

    async def run():
        socket = SlowSocket()
        feed = api.Feed(tmp_path / "snapshot.json")
        feed.update(make_source(1))
        monkeypatch.setattr(api, "SEND_TIMEOUT_SEC", 0.02)
        await asyncio.wait_for(api.send_latest(socket, feed), 1)
        assert socket.sent == 1 and socket.closed == 1013

    asyncio.run(run())
    path = tmp_path / "invalid.json"
    path.write_bytes(b"x" * (MAX_BYTES + 1))
    assert api.read_source(path) is None
    payload = make_source(1).model_dump(mode="json")
    payload["fleet"]["schema_version"] = 2
    path.write_text(json.dumps(payload))
    assert api.read_source(path) is None
    with pytest.raises(ValidationError):
        SourceSnapshot.model_validate(payload)


def test_scene_bridge_identity_is_limited_to_config():
    from backend.dashboard.scene_stream import BridgeIdentity

    gate = BridgeIdentity({"fleet_id": "/separate_namespace/plan"})
    identity = dict(version=1, robot_id="fleet_id", frame_id="map", source="tf")
    assert not gate.accepts(dict(identity, type="robot_pose"))
    assert not gate.accepts(dict(version=1, type="fleet_hello", robot_ids=["separate_namespace"]))
    assert not gate.accepts(dict(version=1, type="fleet_hello", robot_ids=["fleet_id", "fleet_id"]))
    assert gate.accepts(dict(version=1, type="fleet_hello", robot_ids=["fleet_id"]))
    assert gate.accepts(dict(identity, type="hello", path_topic="/separate_namespace/plan"))
    assert not gate.accepts(dict(identity, type="hello", path_topic="/fleet_id/plan"))
    assert not gate.accepts(dict(identity, type="robot_pose", frame_id="odom"))
    assert not gate.accepts(dict(identity, type="robot_pose", source="diagnostic_odom"))
    path = dict(identity, type="robot_path", source_topic="/separate_namespace/plan")
    assert not gate.accepts(dict(path, plan_source="active_goal"))
    assert gate.accepts(dict(path, plan_source="nav2_observed_plan"))


def test_multiplexed_sources_expire_and_reconnect_independently(tmp_path):
    from threading import Event, Thread

    from websockets.exceptions import ConnectionClosed
    from websockets.sync.server import serve

    from backend.dashboard.scene_stream import BRIDGE_ORIGIN, PROTOCOL

    outage = Event()
    connected = []
    identity = dict(version=1, robot_id="alpha", frame_id="map", source="tf", stream_id=str(uuid4()), epoch=0)

    def bridge(peer):
        connected.append(True)
        peer.send(json.dumps(dict(type="fleet_hello", version=1, robot_ids=["alpha"])))
        peer.send(json.dumps(dict(identity, type="hello", after_stamp_ns="0", stale_after_ms=1000)))
        try:
            while not outage.wait(0.04):
                peer.send(json.dumps(dict(identity, type="data_status", status="LIVE")))
        except ConnectionClosed:
            pass

    path = tmp_path / "snapshot.json"
    write_source(path, 1)
    with serve(bridge, "127.0.0.1", 0, origins=[BRIDGE_ORIGIN]) as upstream:
        thread = Thread(target=upstream.serve_forever)
        thread.start()
        try:
            port = upstream.socket.getsockname()[1]
            app = api.create_app(path, origins={ORIGIN}, bridge_url=f"ws://127.0.0.1:{port}/telemetry/fleet",
                                 scene_topics={"alpha": "/ns/plan"})
            with TestClient(app, base_url=URL) as client:
                wait_for_api(client, 1)
                with client.websocket_connect("ws://127.0.0.1/ws/fleet", headers={"origin": ORIGIN},
                                              subprotocols=[PROTOCOL]) as socket:
                    assert socket.accepted_subprotocol == PROTOCOL
                    assert socket.receive_json()["sequence"] == 1

                    def receive_until(predicate):
                        for _ in range(120):
                            message = socket.receive_json()
                            if predicate(message):
                                return message
                        pytest.fail("Expected multiplexed packet was missing")

                    receive_until(lambda message: message.get("type") == "scene_connected")
                    receive_until(lambda message: message.get("type") == "product_unavailable")
                    status = receive_until(lambda message: message.get("packet", {}).get("type") == "data_status")
                    assert status["packet"]["robot_id"] == "alpha"
                    outage.set()
                    receive_until(lambda message: message.get("type") == "scene_disconnected")
                    outage.clear()
                    write_source(path, 2)
                    receive_until(lambda message: message.get("sequence") == 2)
                    receive_until(lambda message: message.get("type") == "scene_connected")
                    assert len(connected) >= 2
                    assert client.post("/api/config/apply").status_code == 404
                    socket.send_text("command")
                    with pytest.raises(WebSocketDisconnect) as closed:
                        for _ in range(8):
                            socket.receive_json()
                    assert closed.value.code == 1008
        finally:
            outage.set()
            upstream.shutdown()
            thread.join(timeout=3)


def test_slow_scene_socket_keeps_at_most_one_upstream_event(monkeypatch, tmp_path):
    from backend.dashboard import scene_stream

    async def run():
        advanced = []
        finished = []

        async def upstream(*_):
            try:
                for index in range(100):
                    advanced.append(index)
                    yield {"type": "scene_connected"}, time.monotonic()
            finally:
                finished.append(True)

        class SlowSocket:
            closed = None

            async def receive(self):
                await asyncio.Future()

            async def send_text(self, _):
                await asyncio.Future()

            async def close(self, code):
                self.closed = code

        monkeypatch.setattr(scene_stream, "bridge_events", upstream)
        socket = SlowSocket()
        feed = api.Feed(tmp_path / "snapshot.json")
        feed.update(make_source(1))
        await asyncio.wait_for(scene_stream.send_operations(
            socket, feed, bridge_url="ws://scene", topics={}, poll_sec=0.01, send_timeout=0.03,
        ), 1)
        assert advanced == [0] and finished == [True]
        assert socket.closed == 1013

    asyncio.run(run())
