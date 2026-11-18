"""Opt-in child provenance. No motion, ACK, stop or release authority."""
from copy import deepcopy
import hashlib
from uuid import UUID, uuid4


def nonzero(value):
    try:
        return str(UUID(value)) == value and UUID(value).int != 0
    except (ValueError, TypeError, AttributeError):
        return False


class ChildBinding:
    """One NavigateToPose transaction, fenced irreversibly on any replacement.

    Source timestamps use the same ROS clock; receipt deadline is monotonic.
    Parent acceptance is confirmed from the actual NavigateToPose client handle.
    Replanning cannot roll a reservation over without qualified physical release.
    """
    def __init__(self, parent, nav_uuid, *, deadline, timeout_ns):
        if (not all(nonzero(parent[k]) for k in ('execute_uuid', 'executor_session'))
                or not nonzero(nav_uuid) or nav_uuid == parent['execute_uuid']
                or type(parent['epoch']) is not int or parent['epoch'] <= 0
                or not parent['task_id'] or timeout_ns <= 0):
            raise ValueError('Explicit real parent identity required')
        self.parent = deepcopy(parent)
        self.nav_uuid, self.context_id = nav_uuid, str(uuid4())
        self.deadline, self.timeout_ns = deadline, timeout_ns
        self.accepted = self.closed = False
        self.observer_session = None
        self.sequence = 0
        self.request = None

    def confirm_nav(self, actual_uuid):
        if self.closed or actual_uuid != self.nav_uuid:
            self.closed = True
            return False
        self.accepted = True
        return True

    def close(self, reason):
        if self.closed:
            return None
        self.closed = True
        if self.request is None:
            return None
        self.sequence += 1
        return self._event(2, reason, 0)

    def _event(self, kind, reason, terminal):
        p = deepcopy(self.request)
        p['child_provenance'] = dict(context_id=self.context_id, nav_uuid=self.nav_uuid,
            observer_session=self.observer_session, sequence=self.sequence, kind=kind,
            reason=reason, terminal_status=terminal)
        return p

    def observe(self, observation, *, now_ns, receipt_now, assignment):
        if self.closed or not self.accepted:
            return None
        if assignment != self.parent:
            return self.close('LOCAL_ASSIGNMENT_CHANGED')
        if receipt_now >= self.deadline:
            return self.close('OBSERVATION_TIMEOUT')
        o = observation
        if (o['context_id'] != self.context_id or o['nav_uuid'] != self.nav_uuid
                or o['executor_session'] != self.parent['executor_session']):
            return None
        if (not nonzero(o['observer_session']) or not nonzero(o['child_uuid'])
                or o['child_uuid'] in (self.nav_uuid, self.parent['execute_uuid'])
                or (self.observer_session is not None and o['observer_session'] != self.observer_session)):
            return None
        if not 0 <= now_ns - o['stamp_ns'] <= self.timeout_ns:
            return self.close('STALE_CHILD_OBSERVATION')
        if type(o['sequence']) is not int or o['sequence'] <= self.sequence:
            return None  # Replay/duplicate never refreshes the local deadline.
        if o['sequence'] != self.sequence + 1:
            return self.close('CHILD_SEQUENCE_GAP')
        if o['kind'] not in (1, 2, 3) or (o['kind'] == 3 and o['terminal_status'] not in (4, 5, 6)):
            return self.close('INVALID_CHILD_EVENT')
        if type(o['path_bytes']) is not bytes or not o['path_bytes']:
            return self.close('INVALID_CHILD_PATH')
        if self.request is None:
            if o['kind'] != 1:
                self.closed = True
                return None
            self.observer_session = o['observer_session']
            self.request = dict(self.parent, request_id=str(uuid4()), child_uuid=o['child_uuid'],
                path_bytes=o['path_bytes'].hex(), path_hash=hashlib.sha256(o['path_bytes']).hexdigest())
        elif (o['kind'] == 1 or o['child_uuid'] != self.request['child_uuid']
              or hashlib.sha256(o['path_bytes']).hexdigest() != self.request['path_hash']):
            return self.close('CHILD_OR_PATH_REPLACED')
        self.sequence = o['sequence']
        if o['kind'] != 1:
            self.closed = True
        return self._event(o['kind'], o['reason'], o['terminal_status'])
