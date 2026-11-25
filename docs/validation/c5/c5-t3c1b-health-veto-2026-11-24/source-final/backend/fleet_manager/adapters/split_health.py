"""Explicit split-actuator health probe. Evaluations may only veto zero-only output."""
import json
import secrets
import time
from collections import deque

from fleet_config.native_zero import compact,sha
from ..domain.split_health import SplitHealthWindow
from .robot_health import RobotHealthProbe, stamp_ns


class SplitHealthProbe(RobotHealthProbe):
    def __init__(self,*args,**kwargs):
        from fleet_interfaces.msg import ObservationHealth
        from std_msgs.msg import String
        from std_srvs.srv import Empty
        from rclpy.qos import qos_profile_sensor_data
        super().__init__(*args,**kwargs)
        params=args[2];self.observer_session=secrets.token_hex(32);self.sequence=0;self.sent={};self.publishing=True
        self.publishers={};self.last_emit={};self.packets={};self.observation_subscriptions={}
        self.amcl_clients={};self.amcl_pending={};self.amcl_query_at={};self.refresh_amcl=True
        self.pending_odometry={r.id:deque(maxlen=32) for r in self.config.robots}
        self.pending_native={r.id:deque(maxlen=32) for r in self.config.robots}
        self.odometry_seen={}
        for robot in self.config.robots:
            rid=robot.id;old=self.windows[rid]
            layer=params[rid]['local_costmap']['local_costmap']['ros__parameters']['obstacle_layer']
            assert layer['plugin']=='fleet_perception::ObservedObstacleLayer'
            topics=[layer[name]['topic'] for name in layer['observation_sources'].split()]
            self.windows[rid]=SplitHealthWindow(robot_id=rid,frames=old.frames,budgets=old.budgets,key=old.key,
                observations={'local':topics},scan_budget=self.config.fleet.perception_safety.scan_age_sec)
            self.publishers[rid]=self.node.create_publisher(String,robot.namespace+'/health_veto',1)
            self.amcl_clients[rid]=self.node.create_client(Empty,robot.namespace+'/request_nomotion_update')
            topic=robot.namespace+'/local_costmap/perception_observations'
            subscription=self.node.create_subscription(ObservationHealth,topic,
                self.callback(self.observation,rid,topic,role='local'),qos_profile_sensor_data)
            self.subscriptions.append(subscription);self.observation_subscriptions[rid]=subscription
            self.packets[rid]={}

    def record(self,stream,rid,value,stamp,source):
        if stream!='odometry':return super().record(stream,rid,value,stamp,source)
        now=time.monotonic()
        try:
            line=json.dumps(dict(stream=stream,robot=rid,value=value,source_stamp_ns=stamp,
                received_monotonic=now,source_id=source,source_identity='UNKNOWN'),allow_nan=False)
        except (ValueError,TypeError):
            self.pending_odometry[rid].clear()
            return self.windows[rid].reject(stream,'NONFINITE_OR_UNSERIALIZABLE')
        self.raw.write(line+'\n')
        old=self.odometry_seen.get(rid)
        if type(stamp) is not int or stamp<=0:return self.windows[rid].reject(stream,'INVALID_SOURCE_STAMP')
        if old:
            if source!=old['source_id']:
                self.windows[rid].fences.add('SOURCE_CHANGED:odometry')
                return self.windows[rid].reject(stream,'SOURCE_CHANGED')
            if stamp<=old['stamp_ns']:
                if stamp==old['stamp_ns'] and value==old['value']:return False
                self.windows[rid].fences.add('SOURCE_ORDER:odometry')
                self.pending_odometry[rid].clear()
                return self.windows[rid].reject(stream,'SOURCE_ORDER')
        self.odometry_seen[rid]=dict(value=value,stamp_ns=stamp,source_id=source)
        self.pending_odometry[rid].append(dict(value=value,stamp_ns=stamp,receipt=now,source_id=source))

    def observe_transform(self,rid,now,ros_ns):
        from rclpy.time import Time
        from rclpy.clock import ClockType
        from tf2_ros import TransformException
        window=self.windows[rid];pending=self.pending_odometry[rid]
        # DDS odometry and its TF arrive independently. Select a real measured
        # sample with an exact-time transform; never latest-TF or restamp it.
        for sample in reversed(pending):
            if not 0<sample['stamp_ns']<=ros_ns:continue
            try:self.buffers[rid].lookup_transform(window.frames['map'],window.frames['base'],
                Time(nanoseconds=sample['stamp_ns'],clock_type=ClockType.ROS_TIME))
            except TransformException:continue
            window.receive('odometry',**sample)
            while pending and pending[0]['stamp_ns']<=sample['stamp_ns']:pending.popleft()
            break
        pending=self.pending_native[rid]
        ready=[p for p in pending if p[0]<=ros_ns]
        if ready:
            _,packet,receipt=ready[-1];window.native(packet,receipt=receipt)
            while pending and pending[0][0]<=ros_ns:pending.popleft()
        super().observe_transform(rid,now,ros_ns)

    def observation(self,rid,message,source,role):
        value=dict(session=message.layer_session,sequence=message.sequence,processed_ns=stamp_ns(message.processed_at),
            topics=list(message.topics),stamps=[stamp_ns(stamp) for stamp in message.measurement_stamps],used=list(message.used))
        now=time.monotonic()
        self.raw.write(json.dumps(dict(stream='observation:'+role,robot=rid,source_identity='UNKNOWN',
            received_monotonic=now,value=value))+'\n')
        return self.windows[rid].observation(role,value,receipt=now,source=source)

    def native(self,rid,message,source):
        try:
            packet=json.loads(message.data)
            if 'split_readback' not in packet:return
            now=time.monotonic()
            self.raw.write(json.dumps(dict(stream='split_native',robot=rid,received_monotonic=now,value=packet))+'\n')
            stamp=json.loads(packet['split_readback']['body'])['writer']['sim_ns']
            if type(stamp) is not int:raise ValueError('Invalid writer stamp')
            self.pending_native[rid].append((stamp,packet,now))
        except (KeyError,ValueError,TypeError):
            self.pending_native[rid].clear()
            self.windows[rid].reject('native','SPLIT_READBACK_INVALID')

    def tick(self):
        from std_msgs.msg import String
        from std_srvs.srv import Empty
        if self.refresh_amcl:
            for rid,client in self.amcl_clients.items():
                now=time.monotonic()
                if rid in self.amcl_pending or now<self.amcl_query_at.get(rid,0.) or not client.service_is_ready():continue
                self.amcl_query_at[rid]=now+self.config.fleet.perception_safety.watchdog_gap_sec
                future=client.call_async(Empty.Request());self.amcl_pending[rid]=future
                def done(result,rid=rid):self.amcl_pending.pop(rid,None)
                future.add_done_callback(done)
        before=self.next_tick
        super().tick()
        if self.closed or self.next_tick==before:return
        now=time.monotonic();ros_ns=self.node.get_clock().now().nanoseconds
        for rid,window in self.windows.items():
            result=self.latest.get(rid)
            if not result:continue
            context,known=self.context_provider(rid,window.samples.get('native'))
            result=window.evaluate(ros_ns=ros_ns,now=now,context=context,known_command=known)
            self.latest[rid]=result
            self.sequence+=1
            wire=window.veto_packet(result,context=context,observer_session=self.observer_session,
                sequence=self.sequence,ros_ns=ros_ns,now=now)
            if wire:
                packet=json.loads(wire);self.sent[rid]=dict(wire=wire,body=json.loads(packet['body']))
                self.packets[rid][sha(packet['body'])]=self.sent[rid]
                if len(self.packets[rid])>512:self.packets[rid].pop(next(iter(self.packets[rid])))
                self.raw.write(json.dumps(dict(stream='health_veto_packet',robot=rid,received_monotonic=now,
                    publishing=self.publishing,packet=packet))+'\n')
                if self.publishing:self.publishers[rid].publish(String(data=wire))
