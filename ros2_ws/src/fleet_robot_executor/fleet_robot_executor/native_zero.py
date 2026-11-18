"""Opt-in B6B.7 zero-only forwarding, downstream of the real T2 MovementGate.

No key is held by the Executor. No ACK, applied state, physical stop or release
is fabricated here. Only the native receiver can validate the FM envelope.
"""
import threading
import time
from fleet_config.native_zero import strict, compact, decisions, sha


class NativeZeroLink:
    def __init__(self, node, observer, *, state_timeout=.15, period=.03):
        from rclpy.clock import Clock, ClockType
        from rclpy.callback_groups import ReentrantCallbackGroup
        from std_msgs.msg import String
        if observer is None or state_timeout <= 0 or period <= 0:
            raise ValueError('Explicit actual-child observer and positive test timing required')
        self.node,self.observer = node,observer
        self.state_timeout,self.lock = state_timeout,threading.RLock()
        self.latest,self.receiver,self.request_id = None,None,None
        self.last_sequence,self.last_hash = 0,None
        self.forwarded,self.rejected = [],[]
        group=ReentrantCallbackGroup()
        self.publisher=node.create_publisher(String,node._qualify('authorized_zero'),16)
        self.exchange=node.create_publisher(String,node._qualify('native_permit_exchange'),16)
        self.subscription=node.create_subscription(String,node._qualify('native_actuator'),self.state,16,callback_group=group)
        self.envelopes=node.create_subscription(String,node._qualify('native_permit_envelope'),self.envelope,16,callback_group=group)
        self.timer=node.create_timer(period,self.tick,clock=Clock(clock_type=ClockType.STEADY_TIME),callback_group=group)

    def close(self, reason):
        self.observer.close(reason)
        self.observer.gate.revoke(reason)

    def state(self,message):
        try:
            value=strict(message.data)
            if 'native_status' not in value:return
            # The FM verifies this signed status. Here an untrusted change can
            # only close the gate; it cannot manufacture permission or an ACK.
            fields=strict(value['native_status']['body'])
            with self.lock:
                self.latest=(value,fields,time.monotonic())
                if self.receiver and (fields['receiver_session']!=self.receiver or
                        fields['receiver_state'] in ('TIMED_OUT','BLOCKED_REARM')):
                    self.close('NATIVE_RECEIVER_CHANGED_OR_LATCHED')
        except (ValueError,KeyError,TypeError,RecursionError):
            return

    def tick(self):
        from std_msgs.msg import String
        with self.lock:
            if self.latest is None:return
            if time.monotonic()-self.latest[2] >= self.state_timeout:
                if self.receiver:self.close('NATIVE_STATUS_STALE')
                return
            gate=self.observer.gate
            with gate.lock:
                if gate.request and gate.decision and gate.child_observation:
                    self.request_id=gate.request['request_id']
            if self.request_id is not None:
                self.exchange.publish(String(data=compact(dict(request_id=self.request_id,
                    native_status=self.latest[0]['native_status']))))

    def envelope(self,message):
        from std_msgs.msg import String
        with self.lock:
            try:
                packet=strict(message.data)
                body=strict(packet['body'])
                context=body['command_context'];permit,_=decisions(context)
                revoke=context['operation']=='REVOKE_ZERO'
                if (set(packet)!={'body','mac'} or body['velocity']!=[0.]*6
                        or permit['identity']['robot_id']!=self.node.robot_id
                        or self.latest is None or time.monotonic()-self.latest[2]>=self.state_timeout
                        or body['actuator_session']!=self.latest[1]['receiver_session']
                        or body['source_session']!=permit['identity']['fm_session']
                        or body['permit_id']!=permit['identity']['permit_id']
                        or body['permit_generation']!=permit['identity']['generation']
                        or not self.observer.gate.native_zero_matches(context,revoke=revoke)):
                    raise ValueError('Zero-only local context fence')
                sequence=body['command_sequence'];digest=sha(packet['body'])
                if (type(sequence) is not int or sequence<self.last_sequence
                        or (sequence==self.last_sequence and digest!=self.last_hash)):
                    raise ValueError('Changed or old transfer')
                self.receiver=body['actuator_session']
                self.last_sequence,self.last_hash=sequence,digest
                self.publisher.publish(message)  # Exact immutable FM bytes, including MAC.
                self.forwarded.append(dict(sequence=sequence,body_sha256=digest,operation=context['operation']))
            except (ValueError,KeyError,TypeError,RecursionError):
                self.rejected.append('LOCAL_CONTEXT_FENCE')
