"""Real typed ROS delivery with explicit synthetic publishers, not physics proof."""
import json
import time
from uuid import uuid4
import pytest

rclpy=pytest.importorskip('rclpy')
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile,DurabilityPolicy
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from std_msgs.msg import String
from geometry_msgs.msg import TransformStamped, PoseWithCovarianceStamped
from tf2_msgs.msg import TFMessage
from fleet_config import load_config
from backend.fleet_manager.adapters.robot_health import RobotHealthProbe
from test_robot_health import packet,KEY


def test_actual_typed_receipts_preserve_stamp_frames_gid_and_authenticated_readback(tmp_path):
    cfg=load_config('config/fleet.warehouse-30x18.yaml');rid=cfg.robots[0].id;ns=cfg.robots[0].namespace
    params={r.id:{'amcl':{'ros__parameters':dict(global_frame_id='map',odom_frame_id=r.id+'/odom',base_frame_id=r.id+'/base_link')}} for r in cfg.robots}
    rclpy.init();node=rclpy.create_node('t3b_component_'+uuid4().hex,parameter_overrides=[Parameter('use_sim_time',value=True)])
    probe=None
    try:
        probe=RobotHealthProbe(node,cfg,params,{r.id:KEY for r in cfg.robots},lambda r,n:(None,None),tmp_path)
        clock=node.create_publisher(Clock,'/clock',10);odom=node.create_publisher(Odometry,ns+'/odom',10)
        tf=node.create_publisher(TFMessage,ns+'/tf',10);native=node.create_publisher(String,ns+'/native_actuator',10)
        identity=dict(robot_id=rid,fm_session=str(uuid4()),permit_id=str(uuid4()))
        end=time.monotonic()+5.;seq=0
        while time.monotonic()<end:
            seq+=1;stamp=10_000_000_000+seq*1_000_000
            c=Clock();c.clock.sec=stamp//10**9;c.clock.nanosec=stamp%10**9;clock.publish(c)
            o=Odometry();o.header.stamp=c.clock;o.header.frame_id=rid+'/odom';o.child_frame_id=rid+'/base_link'
            o.pose.pose.orientation.w=1.;o.twist.twist.linear.x=.12;odom.publish(o)
            edges=[]
            for parent,child in [('map',rid+'/odom'),(rid+'/odom',rid+'/base_link')]:
                t=TransformStamped();t.header.stamp=c.clock;t.header.frame_id=parent;t.child_frame_id=child;t.transform.rotation.w=1.;edges.append(t)
            tf.publish(TFMessage(transforms=edges))
            native.publish(String(data=json.dumps(packet(identity,sequence=seq,sim_ns=stamp))))
            deadline=time.monotonic()+.06
            while time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.01)
            probe.tick();result=probe.latest.get(rid,{})
            if result.get('measured',{}).get('map_pose') and result.get('measured',{}).get('native'):break
        assert result['derived']['linear_speed_m_s']==.12
        assert result['source_ages']['odometry']['source_stamp_ns']==probe.windows[rid].samples['odometry']['stamp_ns']
        assert int(result['source_ages']['odometry']['source_id'],16)!=0
        assert result['measured']['native']['target_linear']==0.
        assert not result['movement_eligible'] and result['physical_stop']=='UNKNOWN'
        before=probe.windows[rid].samples['native']['receipt']
        # Legacy T3A status continues at its original cadence; it is not a new
        # health measurement and cannot refresh health age or erase that sample.
        native.publish(String(data=json.dumps(dict(native_status=result['measured']['native']['native_status']))))
        end=time.monotonic()+.08
        while time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.01)
        assert probe.windows[rid].samples['native']['receipt']==before
        o.header.stamp.nanosec+=1;o.twist.twist.linear.x=float('nan');odom.publish(o)
        end=time.monotonic()+2.
        while time.monotonic()<end and probe.windows[rid].rejections.get('odometry')!='NONFINITE_OR_UNSERIALIZABLE':rclpy.spin_once(node,timeout_sec=.02)
        assert probe.windows[rid].rejections['odometry']=='NONFINITE_OR_UNSERIALIZABLE'
        assert 'odometry' not in probe.windows[rid].samples
        amcl=node.create_publisher(PoseWithCovarianceStamped,ns+'/amcl_pose',QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        a=PoseWithCovarianceStamped();a.header.stamp=c.clock;a.header.frame_id='map';a.pose.pose.orientation.w=1.;a.pose.covariance[0]=-1.
        end=time.monotonic()+2.
        while time.monotonic()<end:
            amcl.publish(a);rclpy.spin_once(node,timeout_sec=.02);probe.tick()
            if any('PSD' in reason for reason in probe.latest[rid]['reasons']):break
        assert any('PSD' in reason for reason in probe.latest[rid]['reasons'])
    finally:
        if probe:probe.close()
        node.destroy_node();rclpy.try_shutdown()


def test_initial_fixture_admission_waits_current_ready_and_never_uses_historical_ready(tmp_path):
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('t3a_executor',Path('docker/experiments/c5-t3a/executor.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    (tmp_path/'reset-verified.json').write_text('{}')  # Explicit unit fixture, no physical claim.
    path=tmp_path/'startup-readiness.json';path.write_text(json.dumps(dict(status='READY',current_status='WAITING')))
    now=[0.]
    def wait(seconds):
        now[0]+=seconds
        if now[0]>=.1:path.write_text(json.dumps(dict(status='READY',current_status='READY')))
    result=module.wait_initial_readiness(tmp_path,timeout=.2,clock=lambda:now[0],sleep=wait)
    assert now[0]>=.1 and result['current_status']=='READY'
    path.write_text(json.dumps(dict(status='READY',current_status='WAITING')));now[0]=0.
    with pytest.raises(TimeoutError):
        module.wait_initial_readiness(tmp_path,timeout=.1,clock=lambda:now[0],sleep=lambda seconds:now.__setitem__(0,now[0]+seconds))


def test_odometry_fault_link_preserves_the_complete_serialized_measurement():
    import importlib.util
    from pathlib import Path
    from rclpy.serialization import serialize_message
    spec=importlib.util.spec_from_file_location('odom_link',Path('docker/experiments/c5-t3b/odometry_link.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    cfg=load_config('config/fleet.warehouse-30x18.yaml');ns=cfg.robots[0].namespace
    rclpy.init();node=rclpy.create_node('t3b_link_component_'+uuid4().hex)
    try:
        link=module.OdometryLink(node,cfg);seen=[]
        subscription=node.create_subscription(Odometry,ns+'/odom',lambda msg:seen.append(bytes(serialize_message(msg))),10)
        publisher=node.create_publisher(Odometry,ns+'/t3b_raw_odom',10)
        message=Odometry();message.header.frame_id='unit/odom';message.header.stamp.sec=12;message.header.stamp.nanosec=345
        message.child_frame_id='unit/base';message.pose.pose.orientation.w=1.;message.twist.twist.linear.x=-.12
        message.pose.covariance[0]=.07
        end=time.monotonic()+4.
        while not seen and time.monotonic()<end:publisher.publish(message);rclpy.spin_once(node,timeout_sec=.02)
        assert seen and all(value==bytes(serialize_message(message)) for value in seen)
    finally:node.destroy_node();rclpy.try_shutdown()


def test_split_probe_pairs_delayed_tf_with_original_odometry_receipt(tmp_path):
    """Typed synthetic sources: alignment must not restamp or rejuvenate data."""
    from backend.fleet_manager.adapters.split_health import SplitHealthProbe
    cfg=load_config('config/fleet.warehouse-30x18.yaml');rid=cfg.robots[0].id;ns=cfg.robots[0].namespace
    params={r.id:{'amcl':{'ros__parameters':dict(global_frame_id='map',odom_frame_id=r.id+'/odom',base_frame_id=r.id+'/base_link')},
        'local_costmap':{'local_costmap':{'ros__parameters':{'obstacle_layer':dict(plugin='fleet_perception::ObservedObstacleLayer',
            observation_sources='scan',scan=dict(topic='scan'))}}}} for r in cfg.robots}
    rclpy.init();node=rclpy.create_node('split_health_alignment_'+uuid4().hex,parameter_overrides=[Parameter('use_sim_time',value=True)])
    probe=None
    try:
        probe=SplitHealthProbe(node,cfg,params,{r.id:KEY for r in cfg.robots},lambda r,n:(None,None),tmp_path)
        clock=node.create_publisher(Clock,'/clock',10);odom=node.create_publisher(Odometry,ns+'/odom',10)
        tf=node.create_publisher(TFMessage,ns+'/tf',10)
        c=Clock();c.clock.sec=10;c.clock.nanosec=20_000_000
        o=Odometry();o.header.stamp.sec=10;o.header.stamp.nanosec=10_000_000
        o.header.frame_id=rid+'/odom';o.child_frame_id=rid+'/base_link';o.pose.pose.orientation.w=1.
        end=time.monotonic()+3.
        while time.monotonic()<end and not probe.pending_odometry[rid]:
            clock.publish(c);odom.publish(o);rclpy.spin_once(node,timeout_sec=.01)
        assert probe.pending_odometry[rid]
        receipt=probe.pending_odometry[rid][-1]['receipt']
        probe.tick();assert 'odometry' not in probe.windows[rid].samples
        edges=[]
        for parent,child in [('map',rid+'/odom'),(rid+'/odom',rid+'/base_link')]:
            t=TransformStamped();t.header.stamp=o.header.stamp;t.header.frame_id=parent;t.child_frame_id=child
            t.transform.rotation.w=1.;edges.append(t)
        end=time.monotonic()+3.
        while time.monotonic()<end and 'tf' not in probe.windows[rid].samples:
            clock.publish(c);tf.publish(TFMessage(transforms=edges))
            for _ in range(8):rclpy.spin_once(node,timeout_sec=0.)
            probe.tick();time.sleep(.01)
        w=probe.windows[rid];assert w.samples['odometry']['stamp_ns']==10_010_000_000
        assert w.samples['odometry']['receipt']==receipt
        assert w.samples['tf']['stamp_ns']==10_010_000_000
        assert not probe.latest[rid]['movement_eligible']
        before=w.samples['odometry']['receipt'];odom.publish(o)
        end=time.monotonic()+.1
        while time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.005);probe.tick()
        assert w.samples['odometry']['receipt']==before
    finally:
        if probe:probe.close()
        node.destroy_node();rclpy.try_shutdown()
