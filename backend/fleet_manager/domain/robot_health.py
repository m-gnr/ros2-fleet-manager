"""Read-only health evidence window. Not a robot state machine or motion gate.

ROS source GIDs and receipt associations are not authenticated epoch/session
claims. Only native HMAC evidence is authenticated in the test trust domain.
Every result remains ineligible for movement and physical resource release.
"""
from copy import deepcopy
import math
from uuid import UUID

from fleet_config.native_zero import verify, STATUS_DOMAIN, compact, sha
from .constants import ROBOT_STATUS_STALE_TIMEOUT_SEC

HEALTH_DOMAIN = b'C5_NATIVE_ZERO_HEALTH_V1\n'


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def covariance_summary(values):
    """Planar PSD covariance and statistical sigmas, never hard error bounds."""
    if not isinstance(values,(list,tuple)) or len(values) != 36 or not all(number(v) for v in values):
        raise ValueError('Finite 6x6 covariance required')
    c = [[values[6*i+j] for j in (0, 1, 5)] for i in (0, 1, 5)]
    minors = [c[i][i]*c[j][j]-c[i][j]*c[i][j] for i in range(3) for j in range(i)]
    determinant = c[0][0]*(c[1][1]*c[2][2]-c[1][2]*c[1][2])-c[0][1]*(c[0][1]*c[2][2]-c[1][2]*c[0][2])+c[0][2]*(c[0][1]*c[1][2]-c[1][1]*c[0][2])
    if (any(c[i][i] < 0 for i in range(3))
            or any(c[i][j] != c[j][i] for i in range(3) for j in range(3))
            or any(not number(v) or v < 0 for v in minors+[determinant])):
        raise ValueError('Symmetric PSD planar covariance required')
    eigen = (c[0][0]+c[1][1]+math.hypot(c[0][0]-c[1][1], 2*c[0][1]))/2
    if not number(eigen):raise ValueError('Covariance arithmetic overflow')
    return dict(xy_max_sigma_m=math.sqrt(eigen), yaw_sigma_rad=math.sqrt(c[2][2]),
                hard_position_bound_m=None, calibration='UNVERIFIED')


class HealthWindow:
    def __init__(self, *, robot_id, frames, budgets, key):
        if (set(frames) != {'map', 'odom', 'base', 'odom_child'} or
                any(not isinstance(v, str) or not v for v in frames.values())
                or any(not number(v) or v <= 0 for v in budgets.values())):
            raise ValueError('Explicit frame contract and existing positive observation budgets required')
        self.robot_id, self.frames, self.budgets, self.key = robot_id, dict(frames), dict(budgets), key
        self.samples, self.pins, self.fences, self.rejections, self.cursors = {}, {}, set(), {}, {}
        self.native_progress = None
        self.status_session, self.status_sequence = None, 0
        self.binding, self.last_ros, self.last_mono = None, None, None

    def reject(self, stream, reason):
        self.rejections[stream] = reason
        # An invalid replacement cannot leave the previous valid sample current.
        self.samples.pop(stream, None)
        return False

    def receive(self, stream, *, value, stamp_ns, receipt, source_id):
        if not number(receipt) or not isinstance(source_id, str) or not source_id:
            return self.reject(stream, 'UNKNOWN_SOURCE')
        if stream in self.pins and self.pins[stream] != source_id:
            self.fences.add('SOURCE_CHANGED:'+stream)
            return self.reject(stream, 'SOURCE_CHANGED')
        self.pins[stream] = source_id
        if stream == 'robot_status':
            try:
                if UUID(value['session']).int == 0 or value['robot_id'] != self.robot_id:
                    raise ValueError('Status identity')
                if self.status_session is not None and value['session'] != self.status_session:
                    self.fences.add('EXECUTOR_SESSION_CHANGED')
                    return self.reject(stream, 'SESSION_CHANGED')
                if type(value['sequence']) is not int or not self.status_sequence < value['sequence'] < 2**64:
                    return self.reject(stream, 'STATUS_ORDER')
                self.status_session, self.status_sequence = value['session'], value['sequence']
            except (KeyError, ValueError, TypeError):
                return self.reject(stream, 'STATUS_IDENTITY')
        old = self.cursors.get(stream)
        if stamp_ns is not None and (type(stamp_ns) is not int or stamp_ns <= 0):
            return self.reject(stream, 'INVALID_SOURCE_STAMP')
        if old and stamp_ns is not None and (stamp_ns < old['stamp_ns'] or
                (stamp_ns == old['stamp_ns'] and stream != 'robot_status')):
            if stamp_ns == old['stamp_ns'] and old['value'] == value:
                return False  # Republishing does not refresh an old measurement.
            self.fences.add('SOURCE_ORDER:'+stream)
            return self.reject(stream, 'SOURCE_ORDER')
        self.samples[stream] = dict(value=deepcopy(value), stamp_ns=stamp_ns, receipt=receipt, source_id=source_id)
        self.cursors[stream] = self.samples[stream]
        self.rejections.pop(stream, None)
        return True

    def native(self, packet, *, receipt):
        try:
            h = verify(packet['native_health'], self.key, domain=HEALTH_DOMAIN)
            if set(h) != {'native_status', 'sim_ns', 'target_linear', 'target_angular', 'joint_commands', 'update_sequence'}:
                raise ValueError('Complete signed update readback required')
            s = verify(h['native_status'], self.key, domain=STATUS_DOMAIN)
            if (any(k in packet and packet[k] != h[k] for k in
                    ('native_status','sim_ns','target_linear','target_angular','joint_commands'))
                    or ('state' in packet and packet['state'] != s['receiver_state'])):
                return self.reject('native','NATIVE_READBACK_CONFLICT')
            if s['robot_id'] != self.robot_id or s['movement_authorized'] is not False or s['ownership_release'] is not False:
                raise ValueError('Native robot/authority fence')
            if (any(type(s[k]) is not int or s[k] < 0 for k in
                    ('report_sequence','sequence','generation','steady_ns','verified_steady_ns'))
                    or s['report_sequence'] == 0 or s['steady_ns'] < s['verified_steady_ns']
                    or s['receiver_state'] not in ('NO_COMMAND','ACTIVE','TIMED_OUT','BLOCKED_REARM')
                    or not isinstance(s['receiver_session'],str) or len(s['receiver_session']) != 64):
                raise ValueError('Native status value fence')
            if type(h['update_sequence']) is not int or h['update_sequence'] <= 0:
                raise ValueError('Native update sequence required')
            old = self.native_progress
            if old and (h['update_sequence'] <= old[0] or s['report_sequence'] <= old[1] or s['steady_ns'] <= old[2]):
                return self.reject('native', 'NATIVE_REPLAY_OR_FROZEN')
            h['status'] = s
            accepted = self.receive('native', value=h, stamp_ns=h['sim_ns'], receipt=receipt,
                                    source_id=s['receiver_session'])
            if accepted:self.native_progress = h['update_sequence'], s['report_sequence'], s['steady_ns']
            return accepted
        except (KeyError, ValueError, TypeError, RecursionError):
            return self.reject('native', 'NATIVE_AUTHENTICATION_OR_SCHEMA')

    def native_issues(self, n):
        reasons = []
        if (not all(number(n[k]) and n[k] == 0 for k in ('target_linear','target_angular'))
                or len(n['joint_commands']) < 2 or any(not isinstance(v,list) or len(v) != 1
                    or not number(v[0]) or v[0] != 0. for v in n['joint_commands'])):
            reasons.append('NATIVE_TARGET_CONTRADICTION_OR_UNKNOWN')
        if n['status']['receiver_state'] != 'ACTIVE':reasons.append('NATIVE_LEASE_NOT_ACTIVE')
        return reasons

    def evaluate(self, *, ros_ns, now, context=None, known_command=None):
        reasons = sorted(self.fences)
        clock_known = type(ros_ns) is int and ros_ns > 0 and number(now)
        if not clock_known:reasons.append('CLOCK_UNKNOWN')
        else:
            if self.last_ros is not None and (ros_ns < self.last_ros or now < self.last_mono):
                self.fences.add('CLOCK_REWOUND');reasons.append('CLOCK_REWOUND')
            self.last_ros, self.last_mono = ros_ns, now
        current = {}
        for stream, budget in self.budgets.items():
            sample = self.samples.get(stream)
            observed = sample or self.cursors.get(stream)
            age = None if not observed or not number(now) else now-observed['receipt']
            source_age = None if not observed or observed['stamp_ns'] is None or not clock_known else (ros_ns-observed['stamp_ns'])/1e9
            valid = sample is not None and clock_known and 0 <= age < budget and (source_age is None or 0 <= source_age < budget)
            current[stream] = dict(current=valid, receipt_age_sec=age, source_age_sec=source_age,
                                   rejected=self.rejections.get(stream), source_id=self.pins.get(stream),
                                   source_stamp_ns=observed['stamp_ns'] if observed else None)
            if not valid:reasons.append('STALE_OR_UNKNOWN:'+stream)
        measured, derived = {}, {}
        def data(stream):return self.samples.get(stream, {}).get('value')
        try:
            o = data('odometry')
            if o is not None:
                if (o['frame'] != self.frames['odom'] or o['child'] != self.frames['odom_child']
                        or len(o['position']) != 3 or len(o['orientation']) != 4 or len(o['velocity']) != 3
                        or not all(number(v) for v in o['position']+o['orientation']+o['velocity'])
                        or not math.isclose(sum(v*v for v in o['orientation']),1.,rel_tol=1e-6)):
                    raise ValueError('ODOMETRY_FRAME_OR_VALUES')
                measured['odometry'] = o
                derived['linear_speed_m_s'] = math.hypot(*o['velocity'][:2])
                derived['angular_speed_rad_s'] = o['velocity'][2]
        except (KeyError, ValueError, TypeError, OverflowError) as error:
            reasons.append('INVALID_HEALTH:'+str(error))
        try:
            a = data('amcl')
            if a is not None:
                if a['frame'] != self.frames['map']:raise ValueError('AMCL_FRAME')
                if (len(a['position']) != 3 or len(a['orientation']) != 4
                        or not all(number(v) for v in a['position']+a['orientation'])
                        or not math.isclose(sum(v*v for v in a['orientation']),1.,rel_tol=1e-6)):
                    raise ValueError('AMCL_POSE_OR_QUATERNION')
                measured['amcl'] = a
                derived['localization'] = covariance_summary(a['covariance'])
        except (KeyError, ValueError, TypeError, OverflowError) as error:
            reasons.append('INVALID_HEALTH:'+str(error))
        try:
            tf = data('tf')
            if tf is not None:
                if tf['frame'] != self.frames['map'] or tf['child'] != self.frames['base'] or not tf['at_odometry_stamp']:
                    raise ValueError('TF_MEASUREMENT_FRAME')
                measured['map_pose'] = tf['position']+tf['orientation']
                qx,qy,qz,qw = tf['orientation']
                if (not all(number(v) for v in measured['map_pose']) or
                        not math.isclose(qx*qx+qy*qy+qz*qz+qw*qw, 1., rel_tol=1e-6)):
                    raise ValueError('TF_POSE_OR_QUATERNION')
                derived['yaw_rad'] = math.atan2(2*(qw*qz+qx*qy), 1-2*(qy*qy+qz*qz))
        except (KeyError, ValueError, TypeError, OverflowError) as error:
            reasons.append('INVALID_HEALTH:'+str(error))
        try:
            for role in ('amcl', 'controller_server', 'planner_server', 'bt_navigator'):
                if data('lifecycle:'+role) != 3:reasons.append('LIFECYCLE_NOT_ACTIVE:'+role)
            n = data('native')
            if n is not None:
                measured['native'] = n
                s = n['status']
                reasons.extend(self.native_issues(n))
            status = data('robot_status')
            if status is not None:
                measured['robot_status'] = status
                if status['robot_id'] != self.robot_id or status['state'] == 6:reasons.append('EXECUTOR_ID_OR_ERROR')
            if not context:
                reasons.append('NO_ACTUAL_PERMIT_CONTEXT')
            else:
                binding = (context['identity'], context['context_sha256'])
                if self.binding is None:self.binding = deepcopy(binding)
                if self.binding != binding:self.fences.add('CONTEXT_CHANGED');reasons.append('CONTEXT_CHANGED')
                i = context['identity']
                if not status or any(status[k] != i[v] for k,v in
                        [('session','executor_session'),('epoch','epoch'),('task_id','task_id')]):
                    reasons.append('EXECUTOR_CONTEXT_FENCE')
                if not n or any(n['status'][k] != v for k,v in {
                        'source_session': i['fm_session'], 'permit_id': i['permit_id'], 'generation': i['generation'],
                        'context_sha256': context['context_sha256']}.items()):
                    reasons.append('NATIVE_CONTEXT_FENCE')
                if not known_command or not n or (n['status']['command_sha256'],n['status']['sequence']) != known_command:
                    reasons.append('NATIVE_COMMAND_NOT_COMMITTED')
                if not context.get('claim_reserved'):
                    self.fences.add('PERMIT_CLOSED');reasons += ['PERMIT_NOT_RESERVED','PERMIT_CLOSED']
        except (KeyError, ValueError, TypeError, OverflowError) as error:
            reasons.append('INVALID_HEALTH:'+str(error))
        return dict(robot_id=self.robot_id, observations_current=not reasons, reasons=sorted(set(reasons)),
                    source_ages=current, measured=deepcopy(measured), derived=derived,
                    source_context_binding='ROS sources: receipt association, no authenticated epoch/session',
                    native_authentication='HMAC in shared FM/native fixture trust domain',
                    movement_eligible=False, physical_stop='UNKNOWN', ownership_release=False,
                    qualification_blockers=['SOURCE_IDENTITY_UNQUALIFIED','COVARIANCE_NOT_HARD_BOUND',
                                            'BRAKING_AND_DELAY_UNMEASURED','INDEPENDENT_FAIL_SAFE_UNVERIFIED','NONZERO_DISABLED'])


def observation_budgets(safety):
    return {'clock': safety.clock_pause_sec, 'odometry': safety.odometry_freshness_sec, 'tf': safety.odometry_freshness_sec,
            'amcl': safety.observation_age_sec, 'robot_status': ROBOT_STATUS_STALE_TIMEOUT_SEC,
            'native': safety.watchdog_gap_sec,
            **{'lifecycle:'+role: safety.transport_sec for role in ('amcl','controller_server','planner_server','bt_navigator')}}
