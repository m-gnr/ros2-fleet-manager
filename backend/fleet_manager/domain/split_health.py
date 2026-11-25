"""Real split-writer observations and veto-only snapshots; no movement permission."""
from copy import deepcopy
import math

from fleet_config.native_zero import verify, sign, compact, sha, STATUS_DOMAIN
from .robot_health import HealthWindow, number

READBACK_DOMAIN=b'C5_SPLIT_ZERO_READBACK_V1\n'
VETO_DOMAIN=b'C5_HEALTH_VETO_V1\n'


def digest(value):
    return isinstance(value,str) and len(value)==64 and not set(value)-set('0123456789abcdef')


class SplitHealthWindow(HealthWindow):
    def __init__(self, *, observations, scan_budget, **kwargs):
        super().__init__(**kwargs)
        self.observations=deepcopy(observations);self.scan_budget=scan_budget
        self.layer_order={};self.layer_receipts={};self.writer_boot=None
        for role in observations:self.budgets['observation:'+role]=self.scan_budget

    def observation(self, role, value, *, receipt, source):
        stream='observation:'+role
        try:
            old=self.layer_order.get(role);session=value['session'];sequence=value['sequence']
            if (not isinstance(session,str) or not session or type(sequence) is not int or sequence<=0
                    or value['topics']!=self.observations[role]
                    or len(value['used'])!=len(value['topics']) or len(value['stamps'])!=len(value['topics'])
                    or type(value['processed_ns']) is not int or value['processed_ns']<=0
                    or any(type(v) is not bool for v in value['used'])
                    or any(type(v) is not int or v<=0 for v in value['stamps'])):raise ValueError('Observation schema')
            if old and session!=old[0]:
                self.fences.add('OBSERVATION_SESSION_CHANGED:'+role);raise ValueError('Observation session changed')
            if old and sequence<=old[1]:return False
            previous=self.cursors.get(stream);source_id=source+'|'+session
            if stream in self.pins and self.pins[stream]!=source_id:
                self.fences.add('SOURCE_CHANGED:'+stream);raise ValueError('Observation source changed')
            if old and (value['processed_ns']<old[2] or any(a<b for a,b in zip(value['stamps'],previous['value']['stamps']))):
                self.fences.add('SOURCE_ORDER:'+stream);raise ValueError('Observation rewind')
            if not number(receipt) or not source:raise ValueError('Observation receipt/source')
            # Layer evaluation sequence/processed_at is not a new measurement.
            # Keep each buffer's first real receipt until its sensor stamp changes.
            receipts=self.layer_receipts.get(role)
            if previous:
                receipts=[receipt if a>b else prior for a,b,prior in zip(value['stamps'],previous['value']['stamps'],receipts)]
            else:receipts=[receipt]*len(value['stamps'])
            self.layer_order[role]=(session,sequence,value['processed_ns']);self.layer_receipts[role]=receipts
            self.pins[stream]=source_id
            sample=dict(value=deepcopy(value),stamp_ns=min(value['stamps']),receipt=min(receipts),source_id=source_id)
            self.samples[stream]=sample;self.cursors[stream]=sample;self.rejections.pop(stream,None)
            return True
        except (KeyError,ValueError,TypeError):return self.reject(stream,'OBSERVATION_INVALID')

    def native(self, packet, *, receipt):
        try:
            h=verify(packet['split_readback'],self.key,domain=READBACK_DOMAIN)
            s=verify(h['native_status'],self.key,domain=STATUS_DOMAIN);r=h['writer']
            if (h['robot_id']!=self.robot_id or s['robot_id']!=self.robot_id
                    or h['movement_authorized'] is not False or h['ownership_release'] is not False
                    or s['movement_authorized'] is not False or s['ownership_release'] is not False
                    or packet['native_status']!=h['native_status']
                    or not digest(r['writer_boot']) or not digest(s['receiver_session'])
                    or r['native_session']!=s['receiver_session']
                    or not digest(r['context_sha256']) or r['context_sha256']!=s['context_sha256']
                    or any(type(r[k]) is not int or r[k]<=0 for k in ('physics_steps','iteration','sim_ns','health_ticket'))
                    or any(type(s[k]) is not int or s[k]<0 for k in
                        ('report_sequence','sequence','generation','steady_ns','verified_steady_ns'))
                    or s['report_sequence']==0 or s['steady_ns']<s['verified_steady_ns']
                    or type(r['latched']) is not bool or type(r['velocity_known']) is not bool):
                raise ValueError('Split readback identity')
            if self.writer_boot is not None and self.writer_boot!=r['writer_boot']:
                self.fences.add('WRITER_BOOT_CHANGED');raise ValueError('Writer boot changed')
            self.writer_boot=r['writer_boot']
            old=self.native_progress
            progress=(r['physics_steps'],s['report_sequence'],s['steady_ns'])
            if old and any(a<=b for a,b in zip(progress,old)):return self.reject('native','NATIVE_REPLAY_OR_FROZEN')
            accepted=self.receive('native',value=dict(status=s,writer=r),stamp_ns=r['sim_ns'],receipt=receipt,source_id=s['receiver_session'])
            if accepted:self.native_progress=progress
            return accepted
        except (KeyError,ValueError,TypeError):return self.reject('native','SPLIT_READBACK_INVALID')

    def native_issues(self,n):
        r=n['writer'];issues=[]
        if (r['selected']!=[0.,0.] or not all(number(v) for v in r['selected']) or not r['velocity_known'] or len(r['joint_velocity'])!=2
                or len(r['body_velocity'])!=6 or not all(number(v) for v in r['joint_velocity']+r['body_velocity'])):
            issues.append('WRITER_TARGET_OR_READBACK_INVALID')
        if n['status']['receiver_state']!='ACTIVE':issues.append('NATIVE_LEASE_NOT_ACTIVE')
        if r['latched']:issues.append('WRITER_LATCHED')
        return issues

    def evaluate(self, *, ros_ns, now, context=None, known_command=None):
        result=super().evaluate(ros_ns=ros_ns,now=now,context=context,known_command=known_command)
        reasons=result['reasons']
        native=self.samples.get('native',{}).get('value')
        if native:
            r=native['writer']
            if not context or context.get('writer_command')!=[r['command_sha256'],r['command_sequence']]:
                reasons.append('WRITER_COMMAND_NOT_COMMITTED')
        for role in self.observations:
            value=self.samples.get('observation:'+role,{}).get('value')
            if value and (not all(value['used']) or any(not 0<=(ros_ns-stamp)/1e9<self.scan_budget for stamp in value['stamps'])):
                reasons.append('OBSERVATION_UNUSED_OR_OLD:'+role)
        result['reasons']=sorted(set(reasons));result['observations_current']=not reasons
        return result

    def veto_packet(self, result, *, context, observer_session, sequence, ros_ns, now):
        """Preserve source cursors/remaining ages, anchored by the writer's own ticket."""
        n=self.samples.get('native',{}).get('value')
        if not n or not context:return None
        r=n['writer'];sources={};remaining=[]
        for stream,budget in self.budgets.items():
            sample=self.samples.get(stream) or self.cursors.get(stream)
            if not sample:return None
            age=now-sample['receipt'];source_age=None if sample['stamp_ns'] is None else (ros_ns-sample['stamp_ns'])/1e9
            left=min(budget-age,budget-source_age if source_age is not None else budget)
            if stream.startswith('observation:'):
                left=min(left,*(self.scan_budget-(ros_ns-v)/1e9 for v in sample['value']['stamps']))
            left_ns=max(0,math.floor(left*1e9));remaining.append(left_ns)
            # Lifecycle has no source stamp: its real RPC request cursor stays stable between replies.
            cursor=dict(stamp_ns=sample['stamp_ns'],source_id=sample['source_id'],receipt_cursor=sample['receipt'])
            stamps=[]
            if stream.startswith('observation:'):
                stamps=sample['value']['stamps']
                cursor=dict(stamp_ns=min(stamps),source_id=sample['source_id'],measurement_stamps=stamps)
            sources[stream]=dict(measurement_id=sha(compact(cursor)),stamp_ns=sample['stamp_ns'],remaining_ns=left_ns,
                measurement_stamps_ns=stamps,receipt_age_sec=age,source_age_sec=source_age,source_identity='UNKNOWN')
        body=dict(robot_id=self.robot_id,observer_session=observer_session,sequence=sequence,
            receiver_session=n['status']['receiver_session'],writer_boot=r['writer_boot'],context_sha256=context['context_sha256'],
            identity_sha256=sha(compact(context['identity'])),ticket=r['health_ticket'],
            observations_current=result['observations_current'],remaining_ns=min(remaining),sources=sources,
            reasons=result['reasons'],movement_eligible=False,physical_stop='UNKNOWN',ownership_release=False)
        return sign(compact(body),self.key,domain=VETO_DOMAIN)
