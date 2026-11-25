"""Opt-in, read-only ROS health probe; never installed by the product launcher.

The context provider must read committed FM/T2 evidence. No source stamp is
replaced by receipt time. Lifecycle RPC receipts are explicitly not measurements.
"""
import gzip
import json
import math
import threading
import time
from uuid import UUID

from fleet_config.native_zero import strict
from ..domain.robot_health import HealthWindow, observation_budgets


def stamp_ns(stamp):
    return stamp.sec*10**9+stamp.nanosec


def xyz(point):
    return [point.x, point.y, point.z]


def quaternion(value):
    return [value.x, value.y, value.z, value.w]


class RobotHealthProbe:
    def callback(self, method, rid, topic, **options):
        # Installed Humble delivers only the message. Graph membership is NOT
        # the message's publisher identity; record the distinction explicitly.
        def receive(message):
            with self.lock:
                if self.closed:return
                now=time.monotonic()
                if now-self.graph_at.get(topic,0.) >= self.config.fleet.perception_safety.timer_period_sec:
                    endpoints=self.node.get_publishers_info_by_topic(topic)
                    self.graph_sources[topic]='|'.join(sorted(bytes(e.endpoint_gid).hex() for e in endpoints))
                    self.graph_at[topic]=now
                    self.raw.write(json.dumps(dict(stream='graph_endpoints',topic=topic,observed_monotonic=now,
                        endpoints=[dict(node=e.node_name,namespace=e.node_namespace,gid=bytes(e.endpoint_gid).hex()) for e in endpoints],
                        message_publisher_identity='UNKNOWN'))+'\n')
                return method(rid,message,self.graph_sources.get(topic,''),**options)
        return receive

    def __init__(self, node, config, params, keys, context_provider, output):
        from geometry_msgs.msg import PoseWithCovarianceStamped
        from nav_msgs.msg import Odometry
        from fleet_interfaces.msg import RobotStatus
        from rosgraph_msgs.msg import Clock
        from tf2_msgs.msg import TFMessage
        from std_msgs.msg import String
        from rclpy.qos import QoSProfile, DurabilityPolicy, qos_profile_sensor_data
        from tf2_ros import Buffer
        from lifecycle_msgs.srv import GetState
        self.node, self.config, self.context_provider = node, config, context_provider
        self.lock, self.windows, self.buffers, self.tf_sources = threading.RLock(), {}, {}, {}
        self.clients, self.pending, self.subscriptions = {}, {}, []
        self.latest, self.next_tick, self.query_at = {}, 0., {}
        self.graph_sources,self.graph_at = {},{}
        self.raw = gzip.open(output/'health-sources.jsonl.gz', 'wt')
        self.log = gzip.open(output/'health.jsonl.gz', 'wt')
        self.closed = False
        for robot in config.robots:
            rid, ns = robot.id, robot.namespace
            amcl = params[rid]['amcl']['ros__parameters']
            frames = dict(map=amcl['global_frame_id'], odom=amcl['odom_frame_id'], base=amcl['base_frame_id'],
                          odom_child=amcl['base_frame_id'])
            self.windows[rid] = HealthWindow(robot_id=rid, frames=frames,
                budgets=observation_budgets(config.fleet.perception_safety), key=keys[rid])
            self.buffers[rid] = Buffer()
            self.tf_sources[rid] = {}
            self.subscriptions += [
                node.create_subscription(Odometry,ns+'/odom',self.callback(self.odometry,rid,ns+'/odom'),qos_profile_sensor_data),
                node.create_subscription(PoseWithCovarianceStamped,ns+'/amcl_pose',self.callback(self.amcl,rid,ns+'/amcl_pose'),
                    QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL)),
                node.create_subscription(RobotStatus,ns+'/robot_status',self.callback(self.status,rid,ns+'/robot_status'),30),
                node.create_subscription(String,ns+'/native_actuator',self.callback(self.native,rid,ns+'/native_actuator'),1),
                node.create_subscription(TFMessage,ns+'/tf',self.callback(self.transforms,rid,ns+'/tf'),50),
                node.create_subscription(TFMessage,ns+'/tf_static',self.callback(self.transforms,rid,ns+'/tf_static',static=True),
                    QoSProfile(depth=20,durability=DurabilityPolicy.TRANSIENT_LOCAL))]
            for role in ('amcl','controller_server','planner_server','bt_navigator'):
                self.clients[rid,role] = node.create_client(GetState,ns+'/'+role+'/get_state')
        self.subscriptions.append(node.create_subscription(Clock,'/clock',self.callback(self.clock,None,'/clock'),10))

    def record(self, stream, rid, value, stamp, source):
        now = time.monotonic()
        try:
            raw=json.dumps(dict(stream=stream,robot=rid,source_id=source,source_stamp_ns=stamp,
                                received_monotonic=now,value=value,source_identity='GRAPH_SNAPSHOT_ONLY'),allow_nan=False)
        except (ValueError,TypeError):
            self.raw.write(json.dumps(dict(stream=stream,robot=rid,source_id=source,received_monotonic=now,
                rejected='NONFINITE_OR_UNSERIALIZABLE',raw_value_repr=repr(value)))+'\n')
            return self.windows[rid].reject(stream,'NONFINITE_OR_UNSERIALIZABLE')
        self.raw.write(raw+'\n')
        return self.windows[rid].receive(stream,value=value,stamp_ns=stamp,receipt=now,source_id=source)

    def clock(self, unused, message, source):
        with self.lock:
            for rid in self.windows:self.record('clock',rid,stamp_ns(message.clock),stamp_ns(message.clock),source)

    def odometry(self, rid, m, info):
        with self.lock:
            self.record('odometry',rid,dict(frame=m.header.frame_id,child=m.child_frame_id,
                position=xyz(m.pose.pose.position),orientation=quaternion(m.pose.pose.orientation),
                velocity=[m.twist.twist.linear.x,m.twist.twist.linear.y,m.twist.twist.angular.z],
                pose_covariance=[float(v) for v in m.pose.covariance],twist_covariance=[float(v) for v in m.twist.covariance]),stamp_ns(m.header.stamp),info)

    def amcl(self, rid, m, info):
        with self.lock:
            self.record('amcl',rid,dict(frame=m.header.frame_id,position=xyz(m.pose.pose.position),
                orientation=quaternion(m.pose.pose.orientation),covariance=[float(v) for v in m.pose.covariance]),stamp_ns(m.header.stamp),info)

    def status(self, rid, m, info):
        with self.lock:
            self.record('robot_status',rid,dict(robot_id=m.robot_id,sequence=m.status_seq,
                session=str(UUID(bytes=bytes(m.publisher_session_id.uuid))),epoch=m.current_epoch,
                task_id=m.current_task_id,state=m.state,phase=m.current_phase,loaded=m.is_loaded,
                pose_frame=m.pose.header.frame_id,pose_stamp_ns=stamp_ns(m.pose.header.stamp)),stamp_ns(m.header.stamp),info)

    def native(self, rid, m, info):
        with self.lock:
            try:
                packet = strict(m.data)
                if 'native_health' not in packet:return  # Ordinary T3A status is not a health sample.
                self.raw.write(json.dumps(dict(stream='native',robot=rid,received_monotonic=time.monotonic(),value=packet))+'\n')
                self.windows[rid].native(packet,receipt=time.monotonic())
            except (ValueError, TypeError, RecursionError):self.windows[rid].reject('native','MALFORMED_NATIVE')

    def transforms(self, rid, message, source, static=False):
        with self.lock:
            for transform in message.transforms:
                if static:self.buffers[rid].set_transform_static(transform,source)
                else:self.buffers[rid].set_transform(transform,source)
                self.tf_sources[rid][transform.header.frame_id,transform.child_frame_id] = source
                self.raw.write(json.dumps(dict(stream='tf_edge',robot=rid,source_id=source,
                    source_stamp_ns=stamp_ns(transform.header.stamp),received_monotonic=time.monotonic(),
                    static=static,frame=transform.header.frame_id,child=transform.child_frame_id,
                    position=xyz(transform.transform.translation),orientation=quaternion(transform.transform.rotation)))+'\n')

    def observe_transform(self,rid,now,ros_ns):
        from rclpy.time import Time
        from rclpy.clock import ClockType
        from tf2_ros import TransformException
        window=self.windows[rid]
        odom = window.samples.get('odometry')
        if odom:
            try:
                tf = self.buffers[rid].lookup_transform(window.frames['map'],window.frames['base'],
                    Time(nanoseconds=odom['stamp_ns'],clock_type=ClockType.ROS_TIME))
                edges = [(window.frames['map'],window.frames['odom']),
                         (window.frames['odom'],window.frames['base'])]
                sources = [self.tf_sources[rid].get(edge) for edge in edges]
                if not all(sources):raise TransformException('Unobserved transform edge source')
                source = '|'.join(sources)
                window.receive('tf',value=dict(frame=tf.header.frame_id,child=tf.child_frame_id,
                    position=xyz(tf.transform.translation),orientation=quaternion(tf.transform.rotation),
                    at_odometry_stamp=stamp_ns(tf.header.stamp)==odom['stamp_ns']),
                    stamp_ns=stamp_ns(tf.header.stamp),receipt=now,source_id=source)
            except TransformException as error:
                window.reject('tf','TF_AT_MEASUREMENT_UNAVAILABLE')
                self.raw.write(json.dumps(dict(stream='tf_lookup_error',robot=rid,
                    source_stamp_ns=odom['stamp_ns'],received_monotonic=now,error=str(error)))+'\n')

    def tick(self):
        from lifecycle_msgs.srv import GetState
        now = time.monotonic()
        if self.closed or now < self.next_tick:return
        self.next_tick = now+self.config.fleet.perception_safety.timer_period_sec
        with self.lock:
            ros_ns = self.node.get_clock().now().nanoseconds
            for (rid,role), client in self.clients.items():
                tag = rid,role
                if tag in self.pending or now < self.query_at.get(tag,0.) or not client.service_is_ready():continue
                start = now
                future = client.call_async(GetState.Request());self.pending[tag] = future
                # Poll within existing observation budgets without flooding
                # lifecycle services on every diagnostic evaluation tick.
                self.query_at[tag] = now+min(self.config.fleet.perception_safety.watchdog_gap_sec,
                                            self.config.fleet.perception_safety.transport_sec)
                def response(done,rid=rid,role=role,started=start,tag=tag):
                    with self.lock:
                        self.pending.pop(tag,None)
                        if self.closed:return
                        # Measure the RPC locally, never restamp a delayed reply.
                        if time.monotonic()-started >= self.config.fleet.perception_safety.transport_sec:
                            self.windows[rid].reject('lifecycle:'+role,'LIFECYCLE_RPC_DELAYED');return
                        try:
                            value = done.result().current_state.id
                            self.windows[rid].receive('lifecycle:'+role,value=value,stamp_ns=None,
                                receipt=started,source_id=rid+'/'+role+'/get_state')
                            self.raw.write(json.dumps(dict(stream='lifecycle:'+role,robot=rid,
                                rpc_requested_monotonic=started,received_monotonic=time.monotonic(),value=value,
                                source_stamp_ns=None,source_identity='UNAUTHENTICATED_RPC_ENDPOINT'))+'\n')
                        except Exception:self.windows[rid].reject('lifecycle:'+role,'LIFECYCLE_RPC_ERROR')
                future.add_done_callback(response)
            for rid, window in self.windows.items():
                self.observe_transform(rid,now,ros_ns)
                context, command = self.context_provider(rid,window.samples.get('native'))
                result = window.evaluate(ros_ns=ros_ns,now=now,context=context,known_command=command)
                self.latest[rid] = result
                self.log.write(json.dumps(dict(received_monotonic=now,ros_ns=ros_ns,**result),allow_nan=False)+'\n')

    def close(self):
        with self.lock:
            self.closed = True
            self.raw.close();self.log.close()
