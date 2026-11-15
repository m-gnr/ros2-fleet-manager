"""ROS reservation service and ACK bridge, installed only by the explicit test seam."""
import asyncio
from dataclasses import fields
import hashlib
import math
from uuid import UUID, uuid4

from ..event_loop import Event
from ..domain.traffic import PermitIdentity


def uuid_text(message):
    return str(UUID(bytes=bytes(message.uuid)))


def write_decision(data, message):
    from unique_identifier_msgs.msg import UUID as ROSUUID
    if 'identity' in data:
        for f in fields(PermitIdentity):
            value = data['identity'][f.name]
            if f.name in ('execute_uuid', 'child_uuid', 'executor_session', 'fm_session', 'permit_id'):
                value = ROSUUID(uuid=list(UUID(value).bytes))
            setattr(message.identity, f.name, value)
    if 'request_id' in data:
        message.request_id = ROSUUID(uuid=list(UUID(data['request_id']).bytes))
    for name in ('status', 'reason', 'movement_kind', 'station_id', 'geometry_digest'):
        setattr(message, name, data.get(name, ''))
    message.committed = True
    message.movement_authorized = False
    return message


def request_payload(request, robot_id):
    from rclpy.serialization import serialize_message
    if request.robot_id != robot_id or request.movement_kind not in ('PICKUP', 'DROPOFF', 'PARK', 'CHARGE'):
        raise ValueError('Endpoint identity/movement fence')
    path = request.path
    if (not path.header.frame_id or not path.poses
            or any(p.header.frame_id != path.header.frame_id for p in path.poses)):
        raise ValueError('Explicit consistent path frame required')
    for pose in path.poses:
        v, q = pose.pose.position, pose.pose.orientation
        if not all(math.isfinite(x) for x in (v.x, v.y, v.z, q.x, q.y, q.z, q.w)):
            raise ValueError('Finite complete path poses required')
    values = list(request.geometry)
    if len(values) % 4 or not values:
        raise ValueError('Segment AABB geometry required')
    raw = bytes(serialize_message(path))
    # Hash the complete ROS path, including orientation and stamps, not its length.
    if hashlib.sha256(raw).hexdigest() != request.path_digest:
        raise ValueError('Path digest mismatch')
    return dict(request_id=uuid_text(request.request_id), robot_id=robot_id, task_id=request.task_id,
                epoch=request.assignment_epoch, execute_uuid=uuid_text(request.parent_goal_uuid),
                child_uuid=uuid_text(request.child_goal_uuid), executor_session=uuid_text(request.executor_session_id),
                movement_kind=request.movement_kind, station_id=request.station_id,
                path_bytes=raw.hex(), path_hash=request.path_digest,
                points=[(p.pose.position.x, p.pose.position.y) for p in path.poses],
                geometry=[dict(zip(('x0', 'y0', 'x1', 'y1'), values[n:n+4])) for n in range(0, len(values), 4)],
                geometry_digest=request.geometry_digest, map_revision=request.map_revision,
                geometry_revision=request.geometry_revision, frame=path.header.frame_id)


class TrafficProtocolROSBridge:
    def __init__(self, node, consumer, loop, namespaces, *, timeout=2.0):
        from fleet_interfaces.srv import RequestTrafficPermit
        from fleet_interfaces.msg import TrafficPermitAck, TrafficPermitDecision
        if consumer._traffic_protocol_session is None:
            raise ValueError('Consumer traffic test seam must be enabled first')
        self.node, self.consumer, self.loop, self.timeout = node, consumer, loop, timeout
        self.publishers = {}
        self.handles = []
        for robot, namespace in namespaces.items():
            self.publishers[robot] = node.create_publisher(TrafficPermitDecision, f'{namespace}/traffic_decision', 10)
            self.handles.append(node.create_service(RequestTrafficPermit, f'{namespace}/request_traffic_permit',
                lambda req, res, robot=robot: self.request(robot, req, res)))
            self.handles.append(node.create_subscription(TrafficPermitAck, f'{namespace}/traffic_ack',
                lambda msg, robot=robot: self.ack(robot, msg), 10))

        self.poll_pending = False
        self.handles.append(node.create_timer(.1, self.poll))

    def poll(self):
        if self.poll_pending:
            return
        self.poll_pending = True
        future = asyncio.run_coroutine_threadsafe(
            self.consumer.submit(Event('TRAFFIC_PROTOCOL_UPDATES')), self.loop)
        def completed(done):
            from fleet_interfaces.msg import TrafficPermitDecision
            try:
                for data in done.result():
                    self.publishers[data['identity']['robot_id']].publish(write_decision(data, TrafficPermitDecision()))
            except Exception:
                # No fresh response will extend the Executor's monotonic deadline.
                pass
            finally:
                self.poll_pending = False
        future.add_done_callback(completed)

    def request(self, robot, request, response):
        try:
            p = request_payload(request, robot)
            future = asyncio.run_coroutine_threadsafe(self.consumer.submit(
                Event('TRAFFIC_PROTOCOL_REQUEST', p, 'permit:' + p['request_id'])), self.loop)
            data = future.result(self.timeout)
            write_decision(data, response.decision)
            self.publishers[robot].publish(response.decision)
        except Exception as exc:
            # The queued event may still commit after timeout. Never retract/free it.
            response.decision.status = 'DENIED'
            response.decision.reason = f'PROTOCOL_UNCERTAIN:{type(exc).__name__}'
            response.decision.committed = False
            response.decision.movement_authorized = False
        return response

    def ack(self, robot, message):
        i = {}
        for f in fields(PermitIdentity):
            value = getattr(message.identity, f.name)
            i[f.name] = uuid_text(value) if hasattr(value, 'uuid') else value
        if i['robot_id'] != robot:
            return
        p = dict(identity=i, request_id=uuid_text(message.request_id),
                 geometry_digest=message.geometry_digest, movement_kind=message.movement_kind,
                 station_id=message.station_id, local_binding_id=uuid_text(message.local_binding_id),
                 kind={1: 'APPLIED', 2: 'RETIRED'}.get(message.kind, 'INVALID'))
        # Callback never writes SQLite and ACK receipt is not applied authority.
        asyncio.run_coroutine_threadsafe(self.consumer.submit(
            Event('TRAFFIC_PROTOCOL_ACK', p, 'traffic-ack:' + str(uuid4()))), self.loop)
