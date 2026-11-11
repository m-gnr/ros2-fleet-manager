"""Repeated real Battery Simulator SIGINT/SIGTERM shutdown under live Gazebo traffic."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import rclpy
from fleet_interfaces.msg import BatteryState
from rclpy.signals import SignalHandlerOptions


def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('profile');cli.add_argument('output',type=Path)
    cli.add_argument('--count',type=int,default=30);cli.add_argument('--require-clean',action='store_true');args=cli.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO);node=rclpy.create_node('stage12_shutdown_observer')
    received=[];node.create_subscription(BatteryState,'/robot_beta/battery_state',lambda msg:received.append(bytes(msg.publisher_session_id.uuid).hex()),10)
    rows=[]
    wrapper="""import json,threading,rclpy
from fleet_battery_simulator.node import main
try:
    main()
finally:
    print('LIFECYCLE_FINAL '+json.dumps(dict(context_ok=rclpy.ok(),threads=[t.name for t in threading.enumerate()])),flush=True)
"""
    try:
        for i in range(args.count):
            received.clear();log=args.output/f'child-{i+1}.log';begin=time.monotonic()
            with log.open('w') as stream:
                child=subprocess.Popen([sys.executable,'-c',wrapper,'--fleet-config',args.profile,'--robot-id','robot_beta'],stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
                deadline=time.monotonic()+15
                while not received and child.poll() is None and time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.005)
                ready=bool(received);pre_threads=[]
                try:pre_threads=[p.name for p in Path(f'/proc/{child.pid}/task').iterdir()]
                except OSError:pass
                sig=signal.SIGINT if i%4!=3 else signal.SIGTERM
                # Different live-message phases; no artificial context destruction.
                until=time.monotonic()+[0.,.005,.02,.08,.2][i%5]
                while time.monotonic()<until:rclpy.spin_once(node,timeout_sec=.001)
                sent=time.monotonic();child.send_signal(sig)
                try:code=child.wait(timeout=5)
                except subprocess.TimeoutExpired:child.kill();code=child.wait()
            row=dict(trial=i+1,signal=sig.name,ready=ready,child_exit=code,parent_context_ok=rclpy.ok(),
                shutdown_s=time.monotonic()-sent,total_s=time.monotonic()-begin,pre_thread_count=len(pre_threads),
                process_exists=Path(f'/proc/{child.pid}').exists(),log=log.name)
            rows.append(row);(args.output/'results.json').write_text(json.dumps(rows,indent=2));print(json.dumps(row),flush=True)
    finally:
        node.destroy_node();rclpy.try_shutdown()
        (args.output/'parent.json').write_text(json.dumps(dict(context_ok=rclpy.ok(),pid=os.getpid(),completed=len(rows))))

    if args.require_clean and any(not r['ready'] or r['child_exit'] or r['process_exists'] for r in rows):
        raise RuntimeError('Battery lifecycle acceptance failed')

if __name__=='__main__':main()
