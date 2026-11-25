"""Reuse 1A's real product/Physics fixture and T3B's real health sources, zero-only."""
from copy import deepcopy
import importlib.util
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import time
from uuid import UUID

from backend.fleet_manager.adapters.split_health import SplitHealthProbe
from backend.fleet_manager.domain.stop_envelope import stop_envelope,StopInputs
from fleet_config.native_zero import sign,compact,load_key,sha
from backend.fleet_manager.domain.split_health import VETO_DOMAIN
from diagnostics import wrap
from fixture_readiness import scene_ready

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('split_live',ROOT/'docker/experiments/c5-t3c1a/live.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
spec=importlib.util.spec_from_file_location('health_live',ROOT/'docker/experiments/c5-t3b/live.py')
health=importlib.util.module_from_spec(spec);spec.loader.exec_module(health)


def factory(node,cfg,args,database):
    paths=['backend/fleet_manager/adapters/split_health.py','backend/fleet_manager/adapters/robot_health.py',
        'backend/fleet_manager/domain/split_health.py','backend/fleet_manager/domain/robot_health.py',
        'docker/experiments/c5-t3b/live.py','docker/experiments/c5-t3c1a/live.py',
        'docker/experiments/c5-t3c1b/live.py','docker/experiments/c5-t3c1b/world.py']
    (args.output/'observer-source-sha256.json').write_text(json.dumps({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},indent=2)+'\n')
    return health.factory(node,cfg,args,database,probe_class=SplitHealthProbe)


def prepare(node,cfg,args,probe,until):
    """Initialize real AMCL before any task, never substitute a health publisher.

    Humble AMCL's set_initial_pose=true path sends an all-zero covariance.
    Use its own particle-filter initialization variances as an uncalibrated
    localization prior at the verified fixture reset pose. These are NOT bounds.
    """
    from nav2_msgs.srv import SetInitialPose
    evidence={}
    for robot in cfg.robots:
        client=node.create_client(SetInitialPose,robot.namespace+'/set_initial_pose')
        until(client.service_is_ready)
        request=SetInitialPose.Request();m=request.pose
        m.header.frame_id=probe.windows[robot.id].frames['map'];m.header.stamp=node.get_clock().now().to_msg()
        m.pose.pose.position.x=robot.initial_pose.x;m.pose.pose.position.y=robot.initial_pose.y
        m.pose.pose.orientation.z=math.sin(robot.initial_pose.yaw/2);m.pose.pose.orientation.w=math.cos(robot.initial_pose.yaw/2)
        m.pose.covariance[0]=m.pose.covariance[7]=.5*.5;m.pose.covariance[35]=(math.pi/12)**2
        future=client.call_async(request);until(future.done);future.result()
        evidence[robot.id]=dict(service=robot.namespace+'/set_initial_pose',source='Nav2 1.1.20 initOdometry default prior',
            stamp_ns=m.header.stamp.sec*10**9+m.header.stamp.nanosec,diagonal=[m.pose.covariance[i] for i in (0,7,35)],
            prior_is_safety_bound=False)
    (args.output/'localization-initialization.json').write_text(json.dumps(evidence,indent=2)+'\n')
    # The original startup file predates the initialization above. Wait for
    # real new measurements and active lifecycle, not that historical flag.
    until(lambda:all(scene_ready(probe.latest.get(r.id,{}),evidence[r.id]['stamp_ns']) for r in cfg.robots))
    (args.output/'scene-ready.json').write_text(json.dumps(dict(initialization=evidence,
        health={r.id:deepcopy(probe.latest[r.id]) for r in cfg.robots},
        permit_authorized=False,physical_stop='UNKNOWN'),indent=2)+'\n')


def before(case,c):
    probe,rid,until=c['probe'],c['robot_id'],c['until']
    def current():
        if not c['writer'][rid]:return False
        w=c['writer'][rid][-1]
        return (not w['latched'] and w['health']['health_seen'] and w['health']['health_digest'] in probe.packets[rid]
                and probe.latest.get(rid,{}).get('observations_current'))
    until(current)
    w=deepcopy(c['writer'][rid][-1]);packet=deepcopy(probe.packets[rid][w['health']['health_digest']])
    assert packet['body']['observations_current'] and packet['body']['sequence']==w['health']['health_sequence']
    result=deepcopy(probe.latest[rid]);assert not result['movement_eligible']
    evidence=dict(writer=w,health=result,packet=packet,actual_task_identity=c['ack']['identity'])
    c['health_before']=evidence;c['save']('health-before.json',evidence)
    mappings=[]
    for entry in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            argv=entry.read_bytes().split(b'\0')
            robot=next((r for r in c['config'].robots if ('__ns:='+r.namespace).encode() in argv),None)
            if not robot:continue
            libraries=[v for v in entry.with_name('maps').read_text().splitlines() if
                'nav2_costmap' in v or 'c5-costmap-cleanup' in v or 'observed_obstacle_layer' in v]
            if libraries:mappings.append(dict(robot_id=robot.id,namespace=robot.namespace,pid=int(entry.parent.name),
                argv=[v.decode(errors='replace') for v in argv if v],libraries=libraries))
        except (FileNotFoundError,ProcessLookupError,PermissionError):continue
    c['save']('ros-library-mappings.json',mappings)


def faults(case,c):
    from std_msgs.msg import String
    probe,rid,until=c['probe'],c['robot_id'],c['until']
    robot=next(r for r in c['config'].robots if r.id==rid)
    evidence={}
    if case in ('tf-loss','odometry-loss','amcl-loss'):
        stream={'tf-loss':'tf','odometry-loss':'odometry','amcl-loss':'amcl'}[case]
        if case=='amcl-loss':pid=health.process_matching(['/nav2_amcl/amcl','__ns:='+robot.namespace])
        else:
            manifest=json.loads((c['args'].output/'fault-processes.json').read_text())
            pid=manifest['tf_helper' if case=='tf-loss' else 'odometry_link']['pid']
        os.kill(pid,signal.SIGSTOP)
        try:
            until(lambda:'STALE_OR_UNKNOWN:'+stream in probe.latest.get(rid,{}).get('reasons',[]),6.)
            until(lambda:c['writer'][rid][-1]['latched'])
            evidence=dict(pid=pid,signal='SIGSTOP',stream=stream,health_during=deepcopy(probe.latest[rid]),
                writer_during=deepcopy(c['writer'][rid][-1]))
        finally:os.kill(pid,signal.SIGCONT)
    elif case=='controller-inactive':
        from nav2_msgs.srv import ManageLifecycleNodes
        # Ask the existing lifecycle owner to pause; an out-of-band transition
        # races its bond-recovery thread and does not model a stable inactive node.
        client=c['node'].create_client(ManageLifecycleNodes,robot.namespace+'/lifecycle_manager_navigation/manage_nodes');until(client.service_is_ready)
        request=ManageLifecycleNodes.Request();request.command=ManageLifecycleNodes.Request.PAUSE
        future=client.call_async(request);until(future.done);assert future.result().success
        until(lambda:'LIFECYCLE_NOT_ACTIVE:controller_server' in probe.latest.get(rid,{}).get('reasons',[]))
        evidence=dict(health_during=deepcopy(probe.latest[rid]))
    elif case=='observation-loss':
        assert c['node'].destroy_subscription(probe.observation_subscriptions[rid])
        until(lambda:'STALE_OR_UNKNOWN:observation:local' in probe.latest.get(rid,{}).get('reasons',[]))
        evidence=dict(cut='Actual observer subscription removed; sensor/costmap still run',health_during=deepcopy(probe.latest[rid]))
    elif case=='health-flow-loss':
        probe.publishing=False;evidence=dict(cut='Health veto publication stopped; observations continue')
    elif case in ('health-context','health-session','health-old'):
        old=deepcopy(c['health_before']['packet']);probe.publishing=False
        if case=='health-old':
            # The baseline snapshot really was accepted. Advance to a newer health sequence first.
            probe.publishing=True
            until(lambda:c['writer'][rid][-1]['health']['health_sequence']>old['body']['sequence'])
            probe.publishing=False;wire=old['wire']
        else:
            p=deepcopy(probe.sent[rid]['body']);p['sequence']+=10000
            p['context_sha256' if case=='health-context' else 'observer_session']='f'*64
            wire=sign(compact(p),load_key('/run/c5-b6b7/'+rid+'.json'),domain=VETO_DOMAIN)
        probe.publishers[rid].publish(String(data=wire));evidence=dict(negative_fixture=True,wire=wire)
    elif case=='replan':
        until(lambda:any(a['status']=='NATIVE_ZERO_REVOKED' for a in c['decisions']('native-ack:')))
        evidence=dict(native_revoke_acks=c['decisions']('native-ack:'))
    elif case=='cancel':
        from action_msgs.srv import CancelGoal
        client=c['node'].create_client(CancelGoal,robot.namespace+'/execute_task/_action/cancel_goal');until(client.service_is_ready)
        request=CancelGoal.Request();request.goal_info.goal_id.uuid=list(UUID(c['ack']['identity']['execute_uuid']).bytes)
        future=client.call_async(request);until(future.done)
        assert future.result().return_code==0
        evidence=dict(actual_execute_uuid=c['ack']['identity']['execute_uuid'],cancel_return_code=future.result().return_code)
    c['save']('health-fault.json',evidence)


def validate(case,c):
    from std_msgs.msg import String
    rid=c['robot_id'];probe=c['probe'];w=deepcopy(c['writer'][rid][-1])
    assert w['latched'] and w['pre_selected_joint_targets']==[0.,0.]
    assert c['health_before']['writer']['health']['health_seen']
    old=c['health_before']['packet']['wire'];before=w['accepted']
    # A real previously accepted health packet cannot clear a closed context.
    probe.publishers[rid].publish(String(data=old))
    target=w['post_completed_physics_updates']+20
    c['until'](lambda:c['writer'][rid][-1]['post_completed_physics_updates']>target)
    after=deepcopy(c['writer'][rid][-1]);assert after['latched'] and after['accepted']==before
    latest=deepcopy(probe.latest[rid]);point=latest.get('measured',{}).get('map_pose',[0.,0.]);speed=latest.get('derived',{})
    stop=stop_envelope(x=point[0],y=point[1],linear_speed=speed.get('linear_speed_m_s'),angular_speed=speed.get('angular_speed_rad_s'),
        footprint_radius=probe.t3b_inventory[rid]['footprint_radius_m'],inputs=StopInputs())
    assert stop['status']=='UNBOUNDED' and stop['tube'] is None and not stop['movement_authorized']
    result=dict(before=c['health_before'],after=after,health_after=latest,stop_envelope=stop,
        movement_authorized=False,physical_stop='UNKNOWN',ownership_release=False)
    c['save']('health-validation.json',result);return dict(valid=True,writer_health_sequence=after['health']['health_sequence'])


if __name__=='__main__':
    base.main(extra_cases=('tf-loss','odometry-loss','amcl-loss','controller-inactive','observation-loss','health-flow-loss',
            'health-context','health-session','health-old','replan','cancel'),observer_factory=factory,
        fault_handler=faults,validator=validate,before_fault=before,world_path=Path(__file__).with_name('world.py'),
        extra_commands=('/health_veto@std_msgs/msg/String]ignition.msgs.StringMsg',),spin_batch=32,prepare=prepare,defer_release=True,process_wrapper=wrap)
