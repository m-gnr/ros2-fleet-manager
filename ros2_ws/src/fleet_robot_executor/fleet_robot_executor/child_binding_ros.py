"""Explicit in-process observation seam; never installed by a launcher or ROS parameter.

Run only in an isolated zero-only/actuator-free Nav2 identity fixture. This
observer does not turn an existing stock motion path into a safe traffic path.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import threading
import time
import os
from uuid import UUID, uuid4
import xml.etree.ElementTree as ET

from .child_binding import ChildBinding
from .traffic import MovementGate, geometry_for


class ROSChildBindingObserver:
    def __init__(self, node, profile):
        from fleet_interfaces.msg import TrafficChildObservation
        from fleet_interfaces.srv import RequestTrafficPermit
        from rclpy.callback_groups import ReentrantCallbackGroup
        required = {'template', 'output_dir', 'map_revision', 'geometry_revision', 'frame', 'radius', 'timeout'}
        if set(profile) != required or any(not math.isfinite(profile[k]) or profile[k] <= 0
                                           for k in ('radius', 'timeout')):
            raise ValueError('Explicit closed identity-test profile required')
        self.node, self.profile = node, dict(profile)
        self.lock, self.binding, self.pending = threading.RLock(), None, []
        self.routes, self.events, self.decisions = {}, [], []
        self.gate = MovementGate()
        self.directory = Path(profile['output_dir'])
        self.directory.mkdir(parents=True, exist_ok=False)
        self.template = ET.parse(profile['template'])
        if len(list(self.template.iter('FollowPath'))) != 1:
            raise ValueError('Exactly one explicit FollowPath BT transaction required')
        group = ReentrantCallbackGroup()
        self.service = node.create_client(RequestTrafficPermit, node._qualify('request_traffic_permit'), callback_group=group)
        self.subscription = node.create_subscription(TrafficChildObservation, node._qualify('traffic_child_observation'),
                                                     self.receive, 32, callback_group=group)
        self.timer = node.create_timer(.1, self.check, callback_group=group)

    def _parent(self, handle, kind):
        n = self.node
        with n._lock:
            if (n.safety.blocked or n.state_machine.is_cancelling or n._stopping.is_set()
                    or n.state_machine.active_goal_uuid != n._uuid_to_str(handle.goal_id.uuid)
                    or n.state_machine.current_epoch != handle.request.assignment_epoch):
                return None
            return dict(robot_id=n.robot_id, task_id=handle.request.task_id,
                        epoch=handle.request.assignment_epoch, execute_uuid=n._uuid_to_str(handle.goal_id.uuid),
                        executor_session=str(n.safety.session_id), movement_kind=kind, station_id='')

    def begin(self, handle, goal, kind):
        from unique_identifier_msgs.msg import UUID as ROSUUID
        with self.lock:
            self.close('NAVIGATE_TRANSACTION_REPLACED')
            parent = self._parent(handle, kind)
            if parent is None:
                raise ValueError('Actual local ExecuteTask assignment required')
            nav_uuid = str(uuid4())
            self.binding = ChildBinding(parent, nav_uuid, deadline=time.monotonic()+self.profile['timeout'],
                                        timeout_ns=round(self.node.executor_config.odometry_freshness_sec*1e9))
            self.parent_handle, self.kind, self.pending = handle, kind, []
            tree = deepcopy(self.template)
            follow = next(tree.iter('FollowPath'))
            follow.tag = 'FleetObservedFollowPath'
            follow.attrib.update(context_id=self.binding.context_id, nav_goal_uuid=nav_uuid,
                                 executor_session=parent['executor_session'])
            path = self.directory / (self.binding.context_id + '.xml')
            # Exclusive creation; never overwrite a tree used by an earlier goal.
            with path.open('xb') as stream:
                tree.write(stream, encoding='utf-8', xml_declaration=True)
            goal.behavior_tree = str(path)
            return ROSUUID(uuid=list(UUID(nav_uuid).bytes)), self.binding.context_id

    def confirm(self, context_id, future):
        from rclpy.action.client import ClientGoalHandle
        from nav2_msgs.action import NavigateToPose
        with self.lock:
            b = self.binding
            if b is None or b.context_id != context_id or b.closed:
                return
            try:
                handle = future.result()
                if (not isinstance(handle, ClientGoalHandle) or not handle.accepted
                        or handle._action_client._action_type is not NavigateToPose
                        or handle._action_client._action_name != self.node.nav2_action_name
                        or not b.confirm_nav(str(UUID(bytes=bytes(handle.goal_id.uuid))))):
                    self.close('NAVIGATE_ACCEPTANCE_UNQUALIFIED')
                    return
                queued, self.pending = self.pending, []
                for message in queued:
                    self.receive(message)
            except Exception:
                self.close('NAVIGATE_ACCEPTANCE_UNKNOWN')

    def receive(self, message):
        from rclpy.serialization import serialize_message
        from .traffic import geometry_for
        with self.lock:
            b = self.binding
            if os.environ.get('C5_1B_DIAGNOSTICS')=='1':
                self.node.get_logger().info('CHILD_RECEIVE kind=%s seq=%s binding=%s closed=%s' % (
                    message.kind,message.observation_seq,b.context_id if b else None,b.closed if b else None))
            if b is None or b.closed:
                return
            if str(UUID(bytes=bytes(message.context_id.uuid))) != b.context_id:
                return
            if not b.accepted:
                if len(self.pending) >= 16:
                    self.close('PENDING_OBSERVATIONS_OVERFLOW')
                else:
                    self.pending.append(deepcopy(message))
                return
            raw = bytes(serialize_message(message.path))
            o = {name: str(UUID(bytes=bytes(getattr(message, field).uuid))) for name, field in (
                ('context_id', 'context_id'), ('nav_uuid', 'nav_goal_uuid'),
                ('executor_session', 'executor_session_id'), ('observer_session', 'observer_session_id'),
                ('child_uuid', 'child_goal_uuid'))}
            o.update(sequence=message.observation_seq, kind=message.kind, reason=message.reason,
                     stamp_ns=message.stamp.sec*10**9+message.stamp.nanosec,
                     path_bytes=raw, terminal_status=message.terminal_status)
            observed_ros_ns=self.node.get_clock().now().nanoseconds
            p = b.observe(o, now_ns=observed_ros_ns, receipt_now=time.monotonic(),
                          assignment=self._parent(self.parent_handle, self.kind))
            if os.environ.get('C5_1B_DIAGNOSTICS')=='1':
                self.node.get_logger().info('CHILD_OBSERVE source_age_ns=%s forwarded=%s closed=%s' % (
                    observed_ros_ns-o['stamp_ns'],p is not None,b.closed))
            if p is None:
                return
            if p['child_provenance']['kind'] == 1:
                path = deepcopy(message.path)
                if (path.header.frame_id != self.profile['frame'] or not path.poses
                        or any(v.header.frame_id != path.header.frame_id for v in path.poses)):
                    self.close('PATH_FRAME_FENCE')
                    return
                boxes = geometry_for(path, self.profile['radius'])
                self.routes[p['request_id']] = path
                p.update(geometry=boxes, geometry_digest=hashlib.sha256(
                    json.dumps(boxes, sort_keys=True, allow_nan=False).encode()).hexdigest(),
                    map_revision=self.profile['map_revision'], geometry_revision=self.profile['geometry_revision'],
                    frame=self.profile['frame'])
                b.request.update({k: deepcopy(p[k]) for k in ('geometry', 'geometry_digest', 'map_revision',
                                                             'geometry_revision', 'frame')})
                self.gate.prepare(p, max(.001, b.deadline-time.monotonic()))
            else:
                self.gate.revoke('CHILD_CLOSED')
            self._send(p)

    def _send(self, p):
        from fleet_interfaces.srv import RequestTrafficPermit
        from unique_identifier_msgs.msg import UUID as ROSUUID
        request = RequestTrafficPermit.Request()
        evidence = p['child_provenance']
        for source, field in (('request_id', 'request_id'), ('execute_uuid', 'parent_goal_uuid'),
                              ('child_uuid', 'child_goal_uuid'), ('executor_session', 'executor_session_id')):
            setattr(request, field, ROSUUID(uuid=list(UUID(p[source]).bytes)))
        for source, field in (('context_id', 'context_id'), ('nav_uuid', 'nav_goal_uuid'),
                              ('observer_session', 'observer_session_id')):
            setattr(request, field, ROSUUID(uuid=list(UUID(evidence[source]).bytes)))
        request.observation_seq, request.observation_kind = evidence['sequence'], evidence['kind']
        request.child_terminal_status, request.observation_reason = evidence['terminal_status'], evidence['reason']
        request.robot_id, request.task_id, request.assignment_epoch = p['robot_id'], p['task_id'], p['epoch']
        request.movement_kind, request.station_id = p['movement_kind'], p['station_id']
        request.path, request.path_digest = deepcopy(self.routes[p['request_id']]), p['path_hash']
        request.geometry = [v[k] for v in p['geometry'] for k in ('x0', 'y0', 'x1', 'y1')]
        request.geometry_digest = p['geometry_digest']
        request.map_revision, request.geometry_revision = p['map_revision'], p['geometry_revision']
        self.events.append(deepcopy(p))
        future = self.service.call_async(request)
        def completed(done):
            with self.lock:
                try:
                    decision = done.result().decision
                    self.decisions.append(deepcopy(decision))
                    if (evidence['kind'] == 1 and self.binding is not None and not self.binding.closed
                            and self.binding.context_id == evidence['context_id']):
                        from .traffic import ROSTrafficMovementClient
                        if ROSTrafficMovementClient.receive(self, decision):
                            self.gate.observe_child_accepted(p['child_uuid'], bytes.fromhex(p['path_bytes']))
                except Exception:
                    self.gate.revoke('CHILD_RPC_UNCERTAIN')
        future.add_done_callback(completed)

    def close(self, reason):
        with self.lock:
            if self.binding:
                p = self.binding.close(reason)
                self.gate.revoke(reason)
                if p and p['request_id'] in self.routes and 'geometry' in p:
                    self._send(p)

    def check(self):
        with self.lock:
            if self.binding and (time.monotonic() >= self.binding.deadline
                                 or self._parent(self.parent_handle, self.kind) != self.binding.parent):
                self.close('PARENT_OR_RECEIPT_FENCE')
