"""Durable FM -> native zero-only transfers. No distributed atomicity or APPLIED."""
from copy import deepcopy
import json
from uuid import UUID, uuid5

from fleet_config.native_zero import STATUS_DOMAIN, verify, bundle, decisions, compact, sha
from .store import encode
from .traffic_protocol import context_reason
from .traffic import process_traffic


def denied(reason):
    return dict(status='DENIED', reason=reason, movement_authorized=False, ownership_release=False)


def save(db, event_id, kind, payload, result):
    db.execute('INSERT INTO traffic_decisions VALUES (?,?,?)',
               (event_id, encode(dict(kind=kind,payload=payload)), encode(result)))
    db.execute('INSERT INTO traffic_outbox(event_id,payload) VALUES (?,?)',(event_id,encode(result)))


def process_native(store, event, core, now, session, profile):
    from ..event_loop import Event
    db, p = store.connection, event.payload
    if not db.in_transaction:
        raise RuntimeError('Consumer transaction required')
    if profile is None or session is None:
        return denied('NATIVE_TEST_MODE_DISABLED')
    robot = p['robot_id']
    try:
        s = verify(p['native_status'], profile['keys'][robot], domain=STATUS_DOMAIN)
        fields = {'robot_id','receiver_session','ticket','report_sequence','receiver_state','source_session',
                  'sequence','permit_id','generation','context_sha256','command_sha256','operation',
                  'verified_steady_ns','steady_ns','movement_authorized','ownership_release'}
        if (set(s) != fields or s['robot_id'] != robot or s['movement_authorized'] is not False
                or s['ownership_release'] is not False or type(s['report_sequence']) is not int or not 0 < s['report_sequence'] < 2**63
                or type(s['sequence']) is not int or not 0 <= s['sequence'] < 2**64
                or any(not isinstance(s[k],str) or len(s[k])!=64 or set(s[k])-set('0123456789abcdef')
                       for k in ('receiver_session','ticket'))):
            raise ValueError('Native status schema fence')
    except (KeyError, ValueError, TypeError, RecursionError):
        return denied('NATIVE_STATUS_AUTHENTICATION_FENCE')
    # Only a real T2 child COMMIT with its existing permit and Outbox can be selected.
    permit_event = 'permit:'+p['request_id']
    row = db.execute('SELECT d.payload,d.decision,o.payload FROM traffic_decisions d JOIN traffic_outbox o '
                     'ON o.event_id=d.event_id WHERE d.event_id=?',(permit_event,)).fetchone()
    if not row or row[1] != row[2]:
        return denied('COMMITTED_PERMIT_OUTBOX_REQUIRED')
    source = json.loads(row[0])['payload']
    proof = source.get('child_provenance',{})
    if source['robot_id'] != robot or proof.get('kind') != 1 or proof.get('sequence') != 1:
        return denied('ACTUAL_CHILD_REQUIRED')
    child_event = 'child:'+proof['context_id']+':1'
    child_row = db.execute('SELECT d.decision,o.payload FROM traffic_decisions d JOIN traffic_outbox o '
                           'ON o.event_id=d.event_id WHERE d.event_id=?',(child_event,)).fetchone()
    if not child_row or child_row[0] != child_row[1]:
        return denied('COMMITTED_CHILD_OUTBOX_REQUIRED')
    context = bundle(permit_event,row[2],child_event,child_row[1])
    try:
        decision, child = decisions(context)
    except (ValueError, KeyError, TypeError):
        return denied('COMMITTED_CHILD_IDENTITY_FENCE')
    identity = decision['identity']
    if identity['fm_session'] != session:
        return denied('FM_SESSION_FENCE')
    cursor = db.execute('SELECT * FROM traffic_native_receivers WHERE robot_id=?',(robot,)).fetchone()
    if cursor and (cursor['fenced'] or cursor['receiver_session'] != s['receiver_session'] or cursor['fm_session'] != session):
        db.execute('UPDATE traffic_native_receivers SET fenced=1 WHERE robot_id=?',(robot,))
        process_traffic(store, Event('TRAFFIC_BLOCK',dict(robot_id=robot,reason='NATIVE_RECEIVER_SESSION_CHANGED'),
                                     'native-fence:'+robot+':'+s['receiver_session']))
        return denied('NATIVE_RECEIVER_SESSION_CHANGED')
    if cursor and s['report_sequence'] <= cursor['report_seq']:
        return denied('DUPLICATE_OR_OLD_NATIVE_REPORT')
    if not cursor:
        db.execute('INSERT INTO traffic_native_receivers VALUES (?,?,?,?,0)',
                   (robot,session,s['receiver_session'],s['report_sequence']))
    else:
        db.execute('UPDATE traffic_native_receivers SET report_seq=? WHERE robot_id=?',(s['report_sequence'],robot))
    reason = context_reason(core,source,now)
    snapshot = json.loads(db.execute('SELECT snapshot FROM traffic_state WHERE singleton=1').fetchone()[0])
    reserved = any(v['claim']['identity']==identity and v['state']=='RESERVED' for v in snapshot['state']['claims'].values())
    history = db.execute('SELECT payload FROM traffic_decisions WHERE event_id LIKE ?',('child:'+proof['context_id']+':%',))
    closed = any(json.loads(r[0]).get('kind')=='TRAFFIC_PROTOCOL_CHILD' and
                 json.loads(r[0])['payload']['child_provenance']['kind']!=1 for r in history)
    reason = reason or ('CHILD_OR_PERMIT_CLOSED' if closed or not reserved else '')
    prefix = 'native-transfer:'+sha(robot)[:16]+':'
    # ACK is a MAC-authenticated observation of the exact previously committed body.
    prior = db.execute('SELECT event_id,decision FROM traffic_decisions WHERE event_id LIKE ? '
                       'AND json_extract(decision,\'$.command_sha256\')=?',
                       (prefix+'%',s['command_sha256'])).fetchone()
    expected_context = sha(compact(context))
    if s['sequence'] == 0:
        consistent = (s['source_session']=='' and s['permit_id']=='' and s['generation']==0
                      and s['context_sha256']==s['command_sha256']=='' and s['operation']=='NONE')
    else:
        consistent = (s['source_session']==session and s['permit_id']==identity['permit_id']
                      and s['generation']==identity['generation'] and s['context_sha256']==expected_context
                      and prior is not None and json.loads(prior['decision'])['command_sequence']==s['sequence'])
    if not consistent:
        db.execute('UPDATE traffic_native_receivers SET fenced=1 WHERE robot_id=?',(robot,))
        process_traffic(store,Event('TRAFFIC_BLOCK',dict(robot_id=robot,reason='NATIVE_CONTEXT_FENCE'),
                                   'native-context-fence:'+robot+':'+str(s['report_sequence'])))
        return denied('NATIVE_CONTEXT_FENCE')
    ack = None
    if prior:
        transfer = json.loads(prior['decision'])
        b = json.loads(transfer['body'])
        normalized = {**b['command_context'],'operation':'INSTALL_ZERO'}
        matches = (transfer['identity']==identity and s['receiver_session']==b['actuator_session'] and s['source_session']==b['source_session']
                   and s['sequence']==b['command_sequence'] and s['permit_id']==b['permit_id']
                   and s['generation']==b['permit_generation'] and s['operation']==b['command_context']['operation']
                   and s['context_sha256']==sha(compact(normalized)))
        ack_id = 'native-ack:'+prior['event_id']
        if matches and not db.execute('SELECT 1 FROM traffic_decisions WHERE event_id=?',(ack_id,)).fetchone():
            current = (not reason and 0 <= now-transfer['prepared_at'] <= profile['ack_timeout']
                       and s['receiver_state']=='ACTIVE' and s['operation']=='INSTALL_ZERO')
            stage = ('NATIVE_ZERO_REVOKED' if s['operation']=='REVOKE_ZERO' else
                     'NATIVE_ZERO_VERIFIED' if current else 'NATIVE_ZERO_VERIFIED_LATE')
            ack = dict(status=stage,identity=transfer['identity'],transfer_id=prior['event_id'],
                native_status=s,native_verified=True,fm_context_valid_at_ack=current,receiver_live_now='UNKNOWN',
                movement_authorized=False,physical_stop='UNKNOWN',ownership_release=False)
            save(db,ack_id,'NATIVE_ZERO_ACK',p,ack)
            # Existing traffic_outbox is intentionally always PENDING. Keep
            # verification as a separate immutable linked record, never APPLIED.
        if not reason and now-transfer['prepared_at'] > profile['ack_timeout']:
            reason='NATIVE_ACK_TOO_OLD'
            process_traffic(store,Event('TRAFFIC_BLOCK',dict(robot_id=robot,reason=reason),
                                       'native-ack-timeout:'+prior['event_id']))
    if s['receiver_state'] not in ('NO_COMMAND','ACTIVE'):
        return {**denied('NATIVE_RECEIVER_LATCHED'), 'ack':ack}
    operation = 'REVOKE_ZERO' if reason else 'INSTALL_ZERO'
    context['operation'] = operation
    transfer_id = prefix+str(uuid5(UUID(session),s['receiver_session']+':'+s['ticket']+':'+p['request_id']+':'+operation))
    previous = db.execute('SELECT decision FROM traffic_decisions WHERE event_id=?',(transfer_id,)).fetchone()
    if previous:
        previous = json.loads(previous[0])
        if now-previous['prepared_at'] > profile['ack_timeout']:
            return {**denied('TRANSFER_RETRY_EXPIRED'),'ack':ack}
        return dict(status='ZERO_TRANSFER_RETRY',transfer=previous,ack=ack,movement_authorized=False)
    last = db.execute('SELECT decision FROM traffic_decisions WHERE event_id LIKE ? ORDER BY rowid DESC LIMIT 1',
                      (prefix+'%',)).fetchone()
    sequence = max(s['sequence'],json.loads(last[0])['command_sequence'] if last else 0)+1
    if sequence >= 2**64:
        return denied('NATIVE_SEQUENCE_EXHAUSTED')
    body = compact(dict(source_session=session,actuator_session=s['receiver_session'],command_sequence=sequence,
        permit_id=identity['permit_id'],permit_generation=identity['generation'],command_context=context,
        ticket=s['ticket'],issued_at=dict(clock='source_monotonic',value=now),velocity=[0.]*6))
    transfer = dict(status='ZERO_TRANSFER_PREPARED',transfer_id=transfer_id,identity=identity,
        body=body,command_sha256=sha(body),command_sequence=sequence,prepared_at=now,
        movement_authorized=False,physical_stop='UNKNOWN',ownership_release=False)
    save(db,transfer_id,'NATIVE_ZERO_TRANSFER',dict(request_id=p['request_id'],native_status=p['native_status']),transfer)
    return dict(status='ZERO_TRANSFER_PREPARED',transfer=transfer,ack=ack,movement_authorized=False)
