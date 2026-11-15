"""Test-only authenticated zero-command sink. Never connects to a real actuator.

HMAC possession authenticates a fixture principal, not a ROS publisher identity.
Tickets and permit deadlines originate exclusively at this receiver's monotonic clock.
"""
import ctypes
import hashlib
import hmac
import json
import math
import secrets
import time


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sign(body, key):
    return json.dumps({'body': body, 'mac': hmac.new(key, canonical(body), hashlib.sha256).hexdigest()})


class NativeLease:
    def __init__(self, library):
        self.lib = ctypes.CDLL(library)
        self.lib.lease_new.restype = ctypes.c_void_p
        for name in ('lease_tick', 'lease_receive', 'lease_block', 'lease_delete'):
            getattr(self.lib, name).argtypes = [ctypes.c_void_p]
        self.ptr = self.lib.lease_new()

    def tick(self):
        return ('NO_COMMAND', 'ACTIVE', 'TIMED_OUT', 'BLOCKED_REARM')[self.lib.lease_tick(self.ptr)]

    def receive(self):
        self.lib.lease_receive(self.ptr)

    def block(self):
        self.lib.lease_block(self.ptr)

    def close(self):
        if self.ptr:
            self.lib.lease_delete(self.ptr)
            self.ptr = None


class ZeroSink:
    # Immutable product inhibition: no enable/rearm API and no output transport.
    target = (0.,) * 6
    ownership_release = False
    movement_authorized = False

    def __init__(self, library, key, source_session, context, permit_id, generation):
        self.lease = NativeLease(library)
        self.key = key
        self.source = source_session
        self.session = secrets.token_hex(16)
        self.context = json.loads(canonical(context))
        self.permit = (permit_id, generation)
        self.permit_until = time.monotonic() + 10.
        self.sequence = 0
        self.last_digest = None
        self.tickets = {}
        self.receipts = []

    def ticket(self):
        # Trusted fixture provisioning only. Not a network challenge/rearm service.
        self.tickets = {k: v for k, v in self.tickets.items() if v > time.monotonic()}
        if len(self.tickets) >= 32:
            raise ValueError('ticket capacity')
        nonce = secrets.token_hex(16)
        self.tickets[nonce] = time.monotonic() + .20
        return nonce

    def receive(self, wire):
        now = time.monotonic()
        state = self.lease.tick()
        try:
            if not isinstance(wire, str) or len(wire) > 16384:
                return 'MALFORMED'
            packet = json.loads(wire)
            if not isinstance(packet, dict) or set(packet) != {'body', 'mac'} or not isinstance(packet['mac'], str) or not isinstance(packet['body'], dict):
                return 'MALFORMED'
            body = packet['body']
            digest = canonical(body)
            if not hmac.compare_digest(packet['mac'], hmac.new(self.key, digest, hashlib.sha256).hexdigest()):
                return 'UNAUTHENTICATED'
            if state in ('TIMED_OUT', 'BLOCKED_REARM'):
                self.lease.block()
                return 'BLOCKED_REARM'
            if set(body) != {'source_session', 'actuator_session', 'command_sequence', 'permit_id',
                             'permit_generation', 'issued_at', 'velocity', 'command_context', 'ticket'}:
                return 'SCHEMA'
            if body['source_session'] != self.source or body['actuator_session'] != self.session:
                return 'SESSION'
            seq = body['command_sequence']
            if type(seq) is not int or not 0 < seq < 2**64:
                return 'SEQUENCE'
            if seq <= self.sequence:
                return 'CHANGED_PAYLOAD' if seq == self.sequence and digest != self.last_digest else 'REPLAY'
            if (body['permit_id'], body['permit_generation']) != self.permit or type(body['permit_generation']) is not int or now >= self.permit_until:
                return 'PERMIT'
            if canonical(body['command_context']) != canonical(self.context):
                return 'CONTEXT'
            # Source time is diagnostic only; never subtracted from receiver time.
            stamp = body['issued_at']
            if set(stamp) != {'clock', 'value'} or stamp['clock'] != 'source_monotonic' or type(stamp['value']) not in (int, float) or not math.isfinite(stamp['value']):
                return 'CLOCK_SCHEMA'
            if self.tickets.pop(body['ticket'], -1) <= now:
                return 'EXPIRED_OR_USED_TICKET'
            velocity = body['velocity']
            if not isinstance(velocity, list) or len(velocity) != 6 or any(type(v) not in (int, float) or not math.isfinite(v) or v != 0 for v in velocity):
                self.lease.block()
                return 'NONZERO_DISABLED'
            self.sequence, self.last_digest = seq, digest
            self.receipts.append(now)
            self.lease.receive()
            return 'ACCEPTED_ZERO'
        except (ValueError, KeyError, TypeError, OverflowError):
            return 'MALFORMED'


def command(sink, sequence=1):
    return dict(source_session=sink.source, actuator_session=sink.session,
                command_sequence=sequence, permit_id=sink.permit[0], permit_generation=sink.permit[1],
                issued_at={'clock': 'source_monotonic', 'value': 123.}, velocity=[0.] * 6,
                command_context=sink.context, ticket=sink.ticket())
