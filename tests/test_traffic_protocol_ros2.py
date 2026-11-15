"""Generated ROS types with fake action/service endpoints; no simulator or DDS robot."""
import asyncio
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS
from uuid import UUID, uuid4
import threading
import time

import pytest

rclpy = pytest.importorskip('rclpy')
from rclpy.serialization import serialize_message
from nav_msgs.msg import Path as ROSPath
from geometry_msgs.msg import PoseStamped
from unique_identifier_msgs.msg import UUID as ROSUUID
from fleet_interfaces.srv import RequestTrafficPermit
from fleet_interfaces.msg import TrafficPermitAck, TrafficPermitDecision
from fleet_robot_executor.traffic import ROSTrafficMovementClient, geometry_for
from fleet_robot_executor.node import RobotExecutorNode
from fleet_robot_executor.constants import TaskPhase
from backend.fleet_manager.adapters.traffic_protocol import TrafficProtocolROSBridge, request_payload, write_decision
from backend.fleet_manager.domain.traffic import sweep
from backend.fleet_manager.event_loop import Event
from test_traffic_protocol import setup, request, uid


class Done:
    def __init__(self, value): self.value = value
    def done(self): return True
    def result(self): return self.value


class FakeService:
    def __init__(self): self.requests = []; self.response = RequestTrafficPermit.Response(); self.available = True
    def wait_for_service(self, **kwargs): return self.available
    def call_async(self, request):
        self.requests.append(deepcopy(request))
        return Done(self.response)


class FakeNode:
    def __init__(self):
        self.service = FakeService()
        self._stopping = threading.Event(); self._lock = threading.RLock()
        self.robot_id = 'r1'; self.safety = NS(session_id=uuid4(), blocked=False)
        self.state_machine = NS(active_goal_uuid=uid(), current_epoch=7)
        self.sent = []
    def _qualify(self, name): return '/r1/' + name
    def create_client(self, *args, **kwargs): return self.service
    def create_subscription(self, *args, **kwargs): return args
    def create_service(self, *args, **kwargs): return args
    def create_timer(self, *args, **kwargs): return args
    def create_publisher(self, *args, **kwargs): return NS(publish=lambda v: self.sent.append(deepcopy(v)))


class FakePlanner:
    def __init__(self, path): self.path = path; self.requests = []
    def wait_for_server(self, **kwargs): return True
    def send_goal_async(self, goal):
        self.requests.append(goal)
        return Done(NS(accepted=True, get_result_async=lambda: Done(NS(status=4, result=NS(path=self.path)))))


def path():
    p = ROSPath(); p.header.frame_id = 'map'; p.header.stamp.sec = 5
    for x in (0., 1.):
        v = PoseStamped(); v.header = deepcopy(p.header); v.pose.position.x = x; v.pose.orientation.w = 1.
        p.poses.append(v)
    return p


def wire(p, route):
    r = RequestTrafficPermit.Request()
    r.request_id = ROSUUID(uuid=list(UUID(p['request_id']).bytes)); r.robot_id = p['robot_id']
    r.task_id = p['task_id']; r.assignment_epoch = p['epoch']
    for source, target in (('execute_uuid','parent_goal_uuid'),('child_uuid','child_goal_uuid'),
                           ('executor_session','executor_session_id')):
        setattr(r, target, ROSUUID(uuid=list(UUID(p[source]).bytes)))
    r.movement_kind = p['movement_kind']; r.station_id = p['station_id']; r.path = route
    r.path_digest = hashlib.sha256(serialize_message(route)).hexdigest()
    boxes = geometry_for(route, .2)
    r.geometry = [b[k] for b in boxes for k in ('x0','y0','x1','y1')]
    r.geometry_digest = hashlib.sha256(json.dumps(boxes, sort_keys=True, allow_nan=False).encode()).hexdigest()
    r.map_revision = 'm1'; r.geometry_revision = 'g1'
    return r


def test_real_idl_service_bridge_commit_and_ack(tmp_path):
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever); thread.start()
    consumer = None
    try:
        consumer, p = asyncio.run_coroutine_threadsafe(setup(tmp_path), loop).result(3)
        n = FakeNode()
        bridge = TrafficProtocolROSBridge(n, consumer, loop, {'r1':'/r1'})
        response = bridge.request('r1', wire(p, path()), RequestTrafficPermit.Response())
        assert response.decision.committed and response.decision.status == 'RESERVED'
        assert not response.decision.movement_authorized
        assert bytes(response.decision.identity.execute_uuid.uuid) == UUID(p['execute_uuid']).bytes
        a = TrafficPermitAck(); a.request_id = response.decision.request_id
        a.identity = response.decision.identity; a.geometry_digest = response.decision.geometry_digest
        a.movement_kind = 'PICKUP'; a.kind = a.APPLIED; a.local_binding_id = ROSUUID(uuid=list(uuid4().bytes))
        bridge.ack('r1', a)
        asyncio.run_coroutine_threadsafe(consumer.submit(Event('TRAFFIC_PROTOCOL_UPDATES')), loop).result(3)
        assert consumer.core._active_tasks_by_robot['r1'].task_id == p['task_id']
        forged = wire(p, path()); forged.path.poses[0].pose.orientation.z = .1
        assert bridge.request('r1', forged, RequestTrafficPermit.Response()).decision.committed is False
        assert n.sent[0].status == 'RESERVED'
    finally:
        if consumer:
            asyncio.run_coroutine_threadsafe(consumer.close(), loop).result(3)
            loop.call_soon_threadsafe(consumer.store.close)
        loop.call_soon_threadsafe(loop.stop); thread.join(3); loop.close()


@pytest.mark.parametrize('kind', ['PICKUP','DROPOFF','PARK','CHARGE'])
def test_fake_planner_service_prepares_real_identity_without_motion(monkeypatch, kind):
    import rclpy.action
    planner = FakePlanner(path())
    monkeypatch.setattr(rclpy.action, 'ActionClient', lambda *a, **k: planner)
    n = FakeNode()
    client = ROSTrafficMovementClient(n, dict(map_revision='m1',geometry_revision='g1',frame='map',radius=.2,timeout=1.))
    req = NS(task_id='real-transport', move_id='real-station', station_id='station', assignment_epoch=7)
    handle = NS(request=req, goal_id=ROSUUID(uuid=list(UUID(n.state_machine.active_goal_uuid).bytes)))
    assert client.prepare_and_authorize_movement(handle, PoseStamped(), kind) is False
    sent = n.service.requests[0]
    assert sent.task_id == ('real-transport' if kind in ('PICKUP','DROPOFF') else 'real-station')
    assert bytes(sent.parent_goal_uuid.uuid) == UUID(n.state_machine.active_goal_uuid).bytes
    assert bytes(sent.executor_session_id.uuid) == n.safety.session_id.bytes
    assert UUID(bytes=bytes(sent.child_goal_uuid.uuid)).int != 0
    parsed = request_payload(sent, 'r1')
    assert parsed['geometry'] == [asdict(b) for b in sweep(((0.,0.),(1.,0.)),.2)]
    planner.path.poses[0].pose.position.x = 99.
    assert sent.path.poses[0].pose.position.x == 0.
    assert client.gate.state in ('REJECTED', 'PROTOCOL_UNCERTAIN')
    assert not n.sent


@pytest.mark.parametrize('station,phase,expected', [(False,TaskPhase.PHASE_MOVING_TO_PICKUP,'PICKUP'),
    (False,TaskPhase.PHASE_MOVING_TO_DROPOFF,'DROPOFF'), (True,False,'PARK'), (True,True,'CHARGE')])
def test_node_send_paths_enter_common_gate(station, phase, expected):
    class Held(Exception): pass
    calls = []
    class NeverNav:
        def wait_for_server(self, **kw): raise AssertionError('Reached Nav2 before closed gate')
        def send_goal_async(self, *a, **kw): raise AssertionError('Movement sent')
    n = NS(_nav2_client=NeverNav())
    def gate(handle, target, kind):
        calls.append(kind); raise Held()
    n.prepare_and_authorize_movement = gate
    with pytest.raises(Held):
        if station:
            RobotExecutorNode._navigate_to_station(n, NS(request=NS(target_pose=PoseStamped(), charging_station=phase)))
        else:
            RobotExecutorNode._navigate_with_cancel_support(n, NS(), PoseStamped(), NS(), phase)
    assert calls == [expected]


def test_node_default_and_defense_against_adapter_true():
    assert RobotExecutorNode.prepare_and_authorize_movement(NS(_traffic_movement=None), None, None, 'PICKUP') is True
    revoked = []
    n = NS(_traffic_movement=NS(prepare_and_authorize_movement=lambda *args: True,
                              gate=NS(revoke=lambda reason: revoked.append(reason))),
           _hold_uncertain=lambda reason: ('HELD', reason))
    assert RobotExecutorNode.prepare_and_authorize_movement(n,None,None,'PICKUP')[0] == 'HELD'
    assert revoked == ['MOTION_DISABLED']


def test_service_timeout_can_commit_later_without_movement_or_release(tmp_path):
    aio = asyncio.new_event_loop()
    thread = threading.Thread(target=aio.run_forever); thread.start()
    consumer = None
    try:
        consumer, p = asyncio.run_coroutine_threadsafe(setup(tmp_path), aio).result(3)
        original = consumer.submit
        async def delayed(event):
            if event.kind == 'TRAFFIC_PROTOCOL_REQUEST':
                await asyncio.sleep(.05)
            return await original(event)
        consumer.submit = delayed
        bridge = TrafficProtocolROSBridge(FakeNode(), consumer, aio, {'r1':'/r1'}, timeout=.001)
        result = bridge.request('r1', wire(p,path()), RequestTrafficPermit.Response())
        assert not result.decision.committed and not result.decision.movement_authorized
        # The caller's timeout does not retract a queued request or its claims.
        asyncio.run_coroutine_threadsafe(asyncio.sleep(.1), aio).result(3)
        updates = asyncio.run_coroutine_threadsafe(original(Event('TRAFFIC_PROTOCOL_UPDATES')), aio).result(3)
        assert updates[0]['status'] == 'RESERVED'
        assert consumer.core._active_tasks_by_robot['r1'].goal_uuid == p['execute_uuid']
    finally:
        if consumer:
            asyncio.run_coroutine_threadsafe(consumer.close(), aio).result(3)
            aio.call_soon_threadsafe(consumer.store.close)
        aio.call_soon_threadsafe(aio.stop); thread.join(3); aio.close()


def test_connection_loss_and_closed_test_profile(monkeypatch):
    import rclpy.action
    monkeypatch.setattr(rclpy.action, 'ActionClient', lambda *a, **k: FakePlanner(path()))
    n = FakeNode(); n.service.available = False
    profile = dict(map_revision='m1',geometry_revision='g1',frame='map',radius=.2,timeout=.1)
    client = ROSTrafficMovementClient(n,profile)
    handle = NS(request=NS(task_id='real',assignment_epoch=7),
                goal_id=ROSUUID(uuid=list(UUID(n.state_machine.active_goal_uuid).bytes)))
    assert not client.prepare_and_authorize_movement(handle,PoseStamped(),'PICKUP')
    assert not n.service.requests and client.gate.state == 'PROTOCOL_UNCERTAIN'
    with pytest.raises(ValueError):
        ROSTrafficMovementClient(n,{**profile,'movement_authorized':True})
    assert 'motion_envelope: null' in (Path(__file__).resolve().parents[1]/'config/fleet.warehouse-30x18.yaml').read_text()
