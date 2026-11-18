"""Product Executor plus optional T2 observer / zero-only link, in its own process."""
import argparse
import json
from pathlib import Path
import signal
import time

import rclpy
from rclpy.parameter import Parameter
from rclpy.executors import MultiThreadedExecutor
from rclpy.signals import SignalHandlerOptions
from fleet_config import load_config
from fleet_robot_executor.node import RobotExecutorNode
from fleet_robot_executor.native_zero import NativeZeroLink
import yaml


def wait_initial_readiness(output, *, timeout=15., clock=time.monotonic, sleep=time.sleep):
    """Initial fixture admission only. Never unblocks a restarted Executor."""
    assert (output/'reset-verified.json').is_file()
    deadline=clock()+timeout
    while True:
        try:
            current=json.loads((output/'startup-readiness.json').read_text())
            if current.get('current_status')=='READY':return current
        except (FileNotFoundError,json.JSONDecodeError):pass
        if clock()>=deadline:raise TimeoutError('Current readiness required for initial Executor admission')
        sleep(.05)


def main():
    p=argparse.ArgumentParser();p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('robot');p.add_argument('--initial',action='store_true');p.add_argument('--replan',action='store_true')
    args=p.parse_args();cfg=load_config(args.profile);robot=next(r for r in cfg.robots if r.id==args.robot)
    if args.initial:
        proof=wait_initial_readiness(args.output)
        (args.output/(robot.id+'-initial-admission.json')).write_text(json.dumps(dict(
            observed_monotonic=time.monotonic(),current_readiness=proof),indent=2)+'\n')
    # Initial reset proof is never reused to unblock a restarted Executor.
    settings=json.loads(Path('config/simulation-c3-3-3.json').read_text())
    params=yaml.safe_load((args.output/'generated'/('nav2-'+robot.id+'.yaml')).read_text())
    radius=params['local_costmap']['local_costmap']['ros__parameters']['robot_radius']
    template=Path('/opt/ros/humble/share/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml')
    if not args.replan:template=Path(__file__).with_name('single_plan.xml').resolve()
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    stop=False
    def stopping(*_):
        nonlocal stop
        stop=True
    signal.signal(signal.SIGTERM,stopping);signal.signal(signal.SIGINT,stopping)
    label='initial' if args.initial else 'restart'
    node=RobotExecutorNode('t3a_executor_'+robot.id,_test_reset_verified=args.initial,
        parameter_overrides=[Parameter('fleet_config_path',value=str(args.profile)),Parameter('robot_id',value=robot.id),
            Parameter('robot_namespace',value=robot.namespace),Parameter('use_sim_time',value=True),
            Parameter('duplicate_record_capacity',value=settings['executor_duplicate_record_capacity'])],
        _traffic_child_test_profile=dict(template=str(template),output_dir=str(args.output/'trees'/(robot.id+'-'+label)),
            map_revision='t3a-map',geometry_revision='t3a-geometry',frame=cfg.warehouse.frame_id,radius=radius,timeout=30.))
    link=NativeZeroLink(node,node._traffic_child_observer)
    pool=MultiThreadedExecutor(num_threads=6);pool.add_node(node)
    session=args.output/(robot.id+'-'+label+'-session.tmp')
    session.write_text(json.dumps(dict(executor_session=str(node.safety.session_id),
        blocked_on_start=node.safety.blocked,reset_verified=args.initial,holds_native_key=False),indent=2)+'\n')
    session.replace(args.output/(robot.id+'-'+label+'-session.json'))
    try:
        while not stop:pool.spin_once(timeout_sec=.05)
    finally:
        node._stopping.set();pool.shutdown(timeout_sec=5.)
        (args.output/(robot.id+'-'+label+'-link.json')).write_text(json.dumps(dict(forwarded=link.forwarded,rejected=link.rejected),indent=2)+'\n')
        node.destroy_node();rclpy.try_shutdown()


if __name__=='__main__':main()
