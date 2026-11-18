"""Child/Path transaction provenance must never imply movement or release."""
import asyncio
from copy import deepcopy
from dataclasses import asdict
import hashlib
from uuid import uuid4

import pytest

from fleet_robot_executor.traffic import MovementGate
from backend.fleet_manager.domain.traffic import PermitIdentity, ReleaseEvidence
from backend.fleet_manager.event_loop import Event
from test_traffic_protocol import setup, request, ack


def test_committed_child_observation_and_terminal_cannot_open_send_or_release(tmp_path):
    async def scenario():
        consumer, p = await setup(tmp_path)
        try:
            decision = await consumer.submit(request(p))
            gate = MovementGate(clock=lambda: 1.)
            gate.prepare(p, 2.)
            assert gate.receive(dict(decision, committed=True))
            raw = bytes.fromhex(p['path_bytes'])
            observed = gate.observe_child_accepted(p['child_uuid'], raw)
            assert observed['actual_child_uuid'] == p['child_uuid']
            assert observed['actual_path_hash'] == hashlib.sha256(raw).hexdigest()
            assert observed['identity'] == decision['identity']
            observed['identity']['epoch'] = 999
            assert gate.child_observation['identity']['epoch'] == p['epoch']
            assert not gate.observe_child_terminal(str(uuid4()), 4)
            assert gate.observe_child_terminal(p['child_uuid'], 5)
            assert gate.applied_ack(ack(decision))  # Still unqualified metadata.
            sent = []
            assert not gate.send(lambda: sent.append(1)) and sent == []
            assert gate.child_observation['physical_stop'] == 'UNKNOWN'
            assert not gate.child_observation['ownership_release']
            evidence = ReleaseEvidence(PermitIdentity(**decision['identity']),
                                       (decision['identity']['permit_id'],), child_terminal='STATUS_CANCELED')
            result = await consumer.submit(Event('TRAFFIC_RELEASE', {'evidence': asdict(evidence)}))
            assert result['reason'] == 'RELEASE_THRESHOLDS_UNVERIFIED'
            assert result['movement_authorized'] is False
        finally:
            await consumer.close(); consumer.store.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('mismatch', ['uuid', 'path'])
def test_wrong_actual_child_or_changed_path_closes_old_request(tmp_path, mismatch):
    async def scenario():
        consumer, p = await setup(tmp_path)
        try:
            d = await consumer.submit(request(p))
            gate = MovementGate(clock=lambda: 1.); gate.prepare(p, 2.)
            assert gate.receive(dict(d, committed=True))
            raw = bytes.fromhex(p['path_bytes'])
            actual = str(uuid4()) if mismatch == 'uuid' else p['child_uuid']
            assert gate.observe_child_accepted(actual, raw+b'changed' if mismatch == 'path' else raw) is None
            assert gate.state == 'CHILD_PATH_IDENTITY_MISMATCH'
            assert gate.observe_child_accepted(p['child_uuid'], raw) is None
            assert not gate.observe_child_terminal(p['child_uuid'], 4)
        finally:
            await consumer.close(); consumer.store.close()
    asyncio.run(scenario())


def test_conflicting_terminal_and_old_generation_remain_closed(tmp_path):
    async def scenario():
        consumer, p = await setup(tmp_path)
        try:
            d = await consumer.submit(request(p))
            gate = MovementGate(clock=lambda: 1.); gate.prepare(p, 2.)
            assert gate.receive(dict(d, committed=True))
            assert gate.observe_child_accepted(p['child_uuid'], bytes.fromhex(p['path_bytes']))
            assert gate.observe_child_terminal(p['child_uuid'], 4)
            assert not gate.observe_child_terminal(p['child_uuid'], 6)
            assert gate.child_observation is None and gate.state == 'CHILD_TERMINAL_CHANGED'
            new = deepcopy(p); new.update(request_id=str(uuid4()), child_uuid=str(uuid4()))
            gate.prepare(new, 2.)
            assert not gate.observe_child_terminal(p['child_uuid'], 4)
            assert not gate.receive(dict(d, committed=True))
            assert gate.child_observation is None
        finally:
            await consumer.close(); consumer.store.close()
    asyncio.run(scenario())
