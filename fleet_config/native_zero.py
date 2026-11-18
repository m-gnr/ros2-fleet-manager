"""B6B.7 zero-only envelope helpers. No movement or physical evidence API."""
import hashlib
import hmac
import json
import os
import stat

STATUS_DOMAIN = b'C5_NATIVE_ZERO_STATUS_V1\n'


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def strict(value):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = item
        return result
    if not isinstance(value, str) or len(value.encode()) > 32768:
        raise ValueError('Bounded JSON required')
    return json.loads(value, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def sign(body, key, *, domain=b''):
    return compact(dict(body=body, mac=hmac.new(key, domain+body.encode(), hashlib.sha256).hexdigest()))


def verify(packet, key, *, domain=b''):
    value = strict(packet) if isinstance(packet, str) else packet
    if (not isinstance(value, dict) or set(value) != {'body', 'mac'}
            or not isinstance(value['body'], str) or not isinstance(value['mac'], str)
            or not hmac.compare_digest(value['mac'], hmac.new(key, domain+value['body'].encode(), hashlib.sha256).hexdigest())):
        raise ValueError('Unauthenticated native envelope')
    return strict(value['body'])


def load_key(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077
                or not 0 < info.st_size <= 8192):
            raise ValueError('Owner-only native provision required')
        with os.fdopen(fd, 'r', closefd=False) as stream:
            data = strict(stream.read())
        key = bytes.fromhex(data['key_hex'])
        if len(key) != 32:
            raise ValueError('256-bit key required')
        return key
    finally:
        os.close(fd)


def bundle(permit_event, permit_raw, child_event, child_raw, operation='INSTALL_ZERO'):
    return dict(operation=operation, permit_event_id=permit_event,
                permit_decision=permit_raw, permit_decision_sha256=sha(permit_raw),
                child_event_id=child_event, child_decision=child_raw, child_decision_sha256=sha(child_raw))


def decisions(context):
    if set(context) != {'operation','permit_event_id','permit_decision','permit_decision_sha256',
                       'child_event_id','child_decision','child_decision_sha256'}:
        raise ValueError('Complete durable context bundle required')
    if (context['operation'] not in ('INSTALL_ZERO','REVOKE_ZERO')
            or sha(context['permit_decision']) != context['permit_decision_sha256']
            or sha(context['child_decision']) != context['child_decision_sha256']):
        raise ValueError('Context operation/digest fence')
    permit, child = strict(context['permit_decision']), strict(context['child_decision'])
    if (permit.get('status') != 'RESERVED' or child.get('status') != 'RESERVED'
            or permit.get('movement_authorized') is not False or child.get('movement_authorized') is not False
            or any(permit.get(k) != child.get(k) for k in ('identity','request_id','geometry_digest','movement_kind','station_id'))
            or child.get('physical_stop') != 'UNKNOWN' or child.get('ownership_release') is not False
            or child.get('child_provenance',{}).get('kind') != 1
            or child['child_provenance'].get('sequence') != 1
            or context['permit_event_id'] != 'permit:'+permit['request_id']
            or context['child_event_id'] != 'child:'+child['child_provenance']['context_id']+':1'):
        raise ValueError('Committed permit/actual-child mismatch')
    return permit, child
