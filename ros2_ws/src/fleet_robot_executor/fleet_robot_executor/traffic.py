"""Reservation handshake for isolated tests. There is deliberately no motion enable."""
from copy import deepcopy
import hashlib
import json
import math
import threading
import time
from uuid import UUID, uuid4


class MovementGate:
    """One prepared child, immutable content, irreversible local revoke fencing.

    A response stages a reservation. APPLIED ACK is unqualified in this version.
    Every send attempt and revoke linearizes under the same lock. SENDING/SENT
    would require a real interlock; they are unreachable here, including send-wins.
    Timeout/disconnect/retire never infer terminal action status or release ownership.
    """
    def __init__(self, *, clock=time.monotonic):
        self.clock, self.lock = clock, threading.RLock()
        self.request = self.decision = self.applied = None
        self.deadline = 0.0
        self.state = 'CLOSED'
        self.closed_requests = set()
        self.child_observation = None

    def prepare(self, request, timeout):
        with self.lock:
            if not math.isfinite(timeout) or timeout <= 0:
                raise ValueError('Explicit positive test timeout required')
            if self.request:
                self.closed_requests.add(self.request['request_id'])
            if request['request_id'] in self.closed_requests:
                raise ValueError('Retired request cannot be reopened')
            self.request, self.decision, self.applied = deepcopy(request), None, None
            self.child_observation = None
            self.deadline = self.clock() + timeout
            self.state = 'WAITING'

    def revoke(self, reason='REVOKED'):
        with self.lock:
            if self.request:
                self.closed_requests.add(self.request['request_id'])
            self.state, self.applied = reason, None
            self.child_observation = None

    def _live(self):
        if self.request is None or self.request['request_id'] in self.closed_requests:
            return False
        if self.clock() >= self.deadline:
            self.revoke('TIMEOUT')
            return False
        return True

    def receive(self, decision):
        with self.lock:
            if not self._live():
                return False
            # Old response is ignored, never allowed to replace a prepared child.
            if decision.get('request_id') != self.request['request_id']:
                return False
            i, r = decision.get('identity', {}), self.request
            matches = all(i.get(k) == r[k] for k in (
                'robot_id', 'task_id', 'epoch', 'execute_uuid', 'child_uuid', 'executor_session',
                'path_hash', 'map_revision', 'geometry_revision', 'frame'))
            matches = matches and all(decision.get(k) == r[k] for k in (
                'movement_kind', 'station_id', 'geometry_digest'))
            try:
                matches = (matches and UUID(i['permit_id']).int != 0 and UUID(i['fm_session']).int != 0
                           and type(i['generation']) is int and i['generation'] > 0)
            except (KeyError, ValueError, TypeError):
                matches = False
            if (not matches or not decision.get('committed') or decision.get('movement_authorized') is not False
                    or decision.get('status') != 'RESERVED'):
                self.revoke('REJECTED')
                return False
            if self.decision is not None:
                if self.decision != decision:
                    self.revoke('DECISION_CHANGED')
                    return False
                return True
            self.decision, self.state = deepcopy(decision), 'RESERVED'
            return True

    def applied_ack(self, ack):
        with self.lock:
            if (not self._live() or not self.decision or ack.get('kind') != 'APPLIED'
                    or any(ack.get(k) != self.decision.get(k) for k in (
                        'identity', 'request_id', 'geometry_digest', 'movement_kind', 'station_id'))):
                return False
            try:
                if UUID(ack['local_binding_id']).int == 0:
                    return False
            except (KeyError, ValueError, TypeError):
                return False
            self.applied, self.state = deepcopy(ack), 'APPLIED_UNQUALIFIED'
            return True

    def send(self, send_callback):
        with self.lock:
            if not self._live() or not self.decision or not self.applied:
                return False
            # No local boundary interlock/actuator qualification. Never call sender.
            self.state = 'MOTION_DISABLED'
            return False

    def observe_child_accepted(self, actual_uuid, serialized_path):
        """Record an accepted child against the reserved immutable path.

        Observation is not a local APPLIED acknowledgement or authorization.
        The caller must obtain UUID/path from its real action client transaction.
        Nonzero send remains inhibited, even after this record is complete.
        """
        with self.lock:
            if not self._live() or not self.decision:
                return None
            if (actual_uuid != self.request['child_uuid'] or type(serialized_path) is not bytes
                    or hashlib.sha256(serialized_path).hexdigest() != self.request['path_hash']):
                self.revoke('CHILD_PATH_IDENTITY_MISMATCH')
                return None
            observation = {k: deepcopy(self.decision[k]) for k in
                           ('identity', 'request_id', 'geometry_digest', 'movement_kind', 'station_id')}
            observation.update(actual_child_uuid=actual_uuid,
                               actual_path_hash=hashlib.sha256(serialized_path).hexdigest(),
                               terminal_status=None, movement_authorized=False,
                               physical_stop='UNKNOWN', ownership_release=False)
            if self.child_observation is not None:
                comparable = {**self.child_observation, 'terminal_status': None}
                if comparable != observation:
                    self.revoke('CHILD_OBSERVATION_CHANGED')
                    return None
                return deepcopy(self.child_observation)
            self.child_observation = observation
            return deepcopy(observation)

    def observe_child_terminal(self, actual_uuid, status):
        """A real terminal does not establish stop, retirement, or physical exit."""
        with self.lock:
            if (self.child_observation is None or actual_uuid != self.child_observation['actual_child_uuid']
                    or type(status) is not int or status not in (4, 5, 6)):
                return False
            previous = self.child_observation['terminal_status']
            if previous is not None and previous != status:
                self.revoke('CHILD_TERMINAL_CHANGED')
                return False
            self.child_observation['terminal_status'] = status
            return True


def observe_follow_path_acceptance(gate, goal_handle, sent_goal, *, expected_action_name):
    """Capture real ROS client response and exact Path bytes, metadata only.

    This does not send a goal or open MovementGate.send. Endpoint matching is
    transaction provenance, not DDS sender authentication or physical evidence.
    """
    from nav2_msgs.action import FollowPath
    from rclpy.action.client import ClientGoalHandle
    from rclpy.serialization import serialize_message
    if (not isinstance(goal_handle, ClientGoalHandle) or not isinstance(sent_goal, FollowPath.Goal)
            or not goal_handle.accepted or not isinstance(expected_action_name, str)
            or not expected_action_name.startswith('/')
            or goal_handle._action_client._action_type is not FollowPath
            or goal_handle._action_client._action_name != expected_action_name):
        gate.revoke('UNQUALIFIED_CHILD_RESPONSE')
        return None
    return gate.observe_child_accepted(str(UUID(bytes=bytes(goal_handle.goal_id.uuid))),
                                      bytes(serialize_message(sent_goal.path)))


def geometry_for(path, radius):
    if not math.isfinite(radius) or radius <= 0 or not path.poses:
        raise ValueError('Explicit test geometry and nonempty path required')
    points = [(p.pose.position.x, p.pose.position.y) for p in path.poses]
    if any(not math.isfinite(v) for p in points for v in p):
        raise ValueError('Nonfinite path')
    pairs = list(zip(points, points[1:])) or [(points[0], points[0])]
    return [dict(x0=min(a[0], b[0])-radius, y0=min(a[1], b[1])-radius,
                 x1=max(a[0], b[0])+radius, y1=max(a[1], b[1])+radius) for a, b in pairs]


class ROSTrafficMovementClient:
    """Planner-only preparation. No NavigateToPose or FollowPath send capability."""
    def __init__(self, node, profile):
        from fleet_interfaces.srv import RequestTrafficPermit
        from fleet_interfaces.msg import TrafficPermitDecision
        from nav2_msgs.action import ComputePathToPose
        from rclpy.action import ActionClient
        from rclpy.callback_groups import ReentrantCallbackGroup
        if set(profile) != {'map_revision', 'geometry_revision', 'frame', 'radius', 'timeout'}:
            raise ValueError('Only explicit closed traffic test profile is supported')
        if (not all(isinstance(profile[k], str) and profile[k] for k in ('map_revision', 'geometry_revision', 'frame'))
                or not all(math.isfinite(profile[k]) and profile[k] > 0 for k in ('radius', 'timeout'))):
            raise ValueError('Invalid traffic test profile')
        self.node, self.profile, self.gate = node, dict(profile), MovementGate()
        group = ReentrantCallbackGroup()
        self.planner = ActionClient(node, ComputePathToPose, node._qualify('compute_path_to_pose'), callback_group=group)
        self.service = node.create_client(RequestTrafficPermit, node._qualify('request_traffic_permit'), callback_group=group)
        self.subscription = node.create_subscription(TrafficPermitDecision, node._qualify('traffic_decision'),
                                                      self.receive, 10, callback_group=group)

    def receive(self, message):
        identity = {}
        for name in message.identity.get_fields_and_field_types():
            value = getattr(message.identity, name)
            identity[name] = str(UUID(bytes=bytes(value.uuid))) if hasattr(value, 'uuid') else value
        data = {name: getattr(message, name) for name in (
            'movement_kind', 'station_id', 'geometry_digest', 'status', 'reason', 'committed', 'movement_authorized')}
        data.update(identity=identity, request_id=str(UUID(bytes=bytes(message.request_id.uuid))))
        return self.gate.receive(data)

    def _await(self, future, deadline):
        while not future.done():
            if self.node._stopping.wait(.01) or time.monotonic() >= deadline:
                self.gate.revoke('TIMEOUT')
                raise TimeoutError('Traffic preparation timeout; ownership retained')
        if time.monotonic() >= deadline:
            self.gate.revoke('TIMEOUT')
            raise TimeoutError('Late traffic preparation result')
        return future.result()

    def prepare_and_authorize_movement(self, handle, target, movement_kind):
        from fleet_interfaces.srv import RequestTrafficPermit
        from nav2_msgs.action import ComputePathToPose
        from rclpy.serialization import serialize_message
        from unique_identifier_msgs.msg import UUID as ROSUUID
        from action_msgs.msg import GoalStatus
        n, p = self.node, self.profile
        deadline = time.monotonic() + p['timeout']
        try:
            if not self.planner.wait_for_server(timeout_sec=p['timeout']):
                raise TimeoutError('Planner unavailable')
            goal = ComputePathToPose.Goal()
            goal.goal = deepcopy(target)
            goal.use_start = False
            planner = self._await(self.planner.send_goal_async(goal), deadline)
            if not planner or not planner.accepted:
                raise RuntimeError('Planner rejected')
            result = self._await(planner.get_result_async(), deadline)
            if result.status != GoalStatus.STATUS_SUCCEEDED:
                raise RuntimeError('Planner did not succeed')
            path = deepcopy(result.result.path)
            if path.header.frame_id != p['frame'] or any(v.header.frame_id != p['frame'] for v in path.poses):
                raise ValueError('Path frame fence')
            boxes = geometry_for(path, p['radius'])
            request = RequestTrafficPermit.Request()
            request.request_id = ROSUUID(uuid=list(uuid4().bytes))
            request.child_goal_uuid = ROSUUID(uuid=list(uuid4().bytes))
            request.parent_goal_uuid = deepcopy(handle.goal_id)
            request.executor_session_id = ROSUUID(uuid=list(n.safety.session_id.bytes))
            request.robot_id = n.robot_id
            request.task_id = handle.request.task_id if movement_kind in ('PICKUP', 'DROPOFF') else handle.request.move_id
            request.assignment_epoch = handle.request.assignment_epoch
            request.station_id = '' if movement_kind in ('PICKUP', 'DROPOFF') else handle.request.station_id
            request.movement_kind, request.path = movement_kind, path
            request.path_digest = hashlib.sha256(bytes(serialize_message(path))).hexdigest()
            request.geometry = [v[k] for v in boxes for k in ('x0', 'y0', 'x1', 'y1')]
            request.geometry_digest = hashlib.sha256(json.dumps(boxes, sort_keys=True, allow_nan=False).encode()).hexdigest()
            request.map_revision, request.geometry_revision = p['map_revision'], p['geometry_revision']
            frozen = dict(request_id=str(UUID(bytes=bytes(request.request_id.uuid))), robot_id=n.robot_id,
                          task_id=request.task_id, epoch=request.assignment_epoch,
                          execute_uuid=str(UUID(bytes=bytes(request.parent_goal_uuid.uuid))),
                          child_uuid=str(UUID(bytes=bytes(request.child_goal_uuid.uuid))),
                          executor_session=str(n.safety.session_id), path_hash=request.path_digest,
                          map_revision=p['map_revision'], geometry_revision=p['geometry_revision'], frame=p['frame'],
                          geometry_digest=request.geometry_digest, movement_kind=movement_kind, station_id=request.station_id)
            with n._lock:
                if (n.state_machine.active_goal_uuid != frozen['execute_uuid']
                        or n.state_machine.current_epoch != frozen['epoch'] or n.safety.blocked):
                    raise ValueError('Local assignment fence')
            self.gate.prepare(frozen, max(.001, deadline - time.monotonic()))
            if not self.service.wait_for_service(timeout_sec=max(0., deadline-time.monotonic())):
                raise TimeoutError('Traffic service unavailable')
            response = self._await(self.service.call_async(request), deadline)
            if not self.receive(response.decision):
                raise ValueError('RPC decision does not match the prepared request')
            return self.gate.send(None)  # No sender exists in this mode.
        except Exception:
            self.gate.revoke('PROTOCOL_UNCERTAIN')
            return False
