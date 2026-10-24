"""Session-local admission and immutable assignment evidence.

No reset/reconciliation protocol is exposed here. A new process starts blocked;
only the isolated test harness supplies verified scenario-reset evidence.
Callers serialize access with the executor lock.
"""
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

UINT64_MAX = (1 << 64) - 1


@dataclass(frozen=True)
class AssignmentRecord:
    identity: tuple
    payload: bytes
    terminal: Optional[tuple] = None


class ExecutorSafety:
    def __init__(self, capacity: int):
        if type(capacity) is not int or capacity <= 0:
            raise ValueError('duplicate_record_capacity must be an explicit positive integer')
        self.capacity = capacity
        self.session_id = uuid4()
        self.status_seq = 0
        self.blocked = True
        self.reason = 'Scenario reset evidence required'
        self.records = {}

    def block(self, reason: str):
        self.blocked = True
        self.reason = reason

    def next_status(self):
        if self.status_seq == UINT64_MAX:
            self.block('Status sequence exhausted')
            return None
        self.status_seq += 1
        return self.status_seq

    def available(self, task_id, epoch):
        return (not self.blocked and len(self.records) < self.capacity
                and not any(k[:2] == (task_id, epoch) for k in self.records))

    def admit(self, identity, payload):
        if not self.available(*identity[:2]):
            return False
        if any(k[2] == identity[2] for k in self.records):
            return False
        self.records[identity] = AssignmentRecord(identity, bytes(payload))
        return True

    def finish(self, identity, payload, result):
        record = self.records.get(identity)
        if (record is None or record.payload != bytes(payload)
                or result.completed_epoch != identity[1]):
            self.block('Terminal identity or payload mismatch; review required')
            return False
        terminal = (int(result.status), result.completed_epoch, result.error_reason)
        if record.terminal is not None and record.terminal != terminal:
            self.block('Conflicting terminal result; review required')
            return False
        self.records[identity] = AssignmentRecord(identity, record.payload, terminal)
        return True


class StatusOrderGuard:
    """Pure contract guard for a future consumer; not a Fleet Manager adapter.

    Binding a known session does not grant assignment permission. A changed
    session permanently blocks this guard; reset requires a new scenario guard.
    """
    def __init__(self, session_id):
        self.session_id = bytes(session_id)
        self.last_seq = 0
        self.blocked = False

    def accept(self, session_id, sequence):
        if bytes(session_id) != self.session_id:
            self.blocked = True
        if self.blocked or not self.last_seq < sequence <= UINT64_MAX:
            return False
        self.last_seq = sequence
        return True
