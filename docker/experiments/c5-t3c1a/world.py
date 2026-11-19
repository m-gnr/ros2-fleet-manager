"""Explicit split-actuator fixture. Product launchers never import this module."""
import importlib.util
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('t3a_world',ROOT/'docker/experiments/c5-t3a/world.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
server=base.t2.native.server
original_generate=server.generate;original_run=server.run_simulation
configuration=None
output=None


def atomic(path,value):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)


def generate(*args,**kwargs):
    global configuration,output
    configuration=original_generate(*args,**kwargs);output=args[1].parent
    tree=ET.parse(args[1]/'warehouse.sdf');world=tree.find('world')
    physics=[p for p in world.findall('plugin') if p.get('name')=='ignition::gazebo::systems::Physics']
    assert len(physics)==1
    physics[0].set('name','c5::test::PhysicsObserver');physics[0].set('filename','/b6b7-native/libc5-physics-observer.so')
    stock=list(Path('/usr/lib').glob('*/ign-gazebo-6/plugins/libignition-gazebo-physics-system.so'))
    assert len(stock)==1
    ET.SubElement(physics[0],'stock_library').text=str(stock[0])
    for robot in configuration.robots:
        drivers=[p for p in world.find('model[@name="'+robot.id+'"]').findall('plugin') if 'DiffDrive' in p.get('name','')]
        assert len(drivers)==1
        drivers[0].set('name','c5::test::SplitZeroDiffDrive')
        drivers[0].remove(drivers[0].find('authorization_file'))
    tree.write(args[1]/'warehouse.sdf',encoding='utf-8',xml_declaration=True)
    return configuration


def run(commands,namespaces,emit):
    original_popen=subprocess.Popen;tree=ET.parse(output/'generated/warehouse.sdf')
    workers={};endpoints=[];gazebo_fds=[];trace_ends=[];manifest={};restart_stop=threading.Event()
    recorder=None
    def start_worker(rid,config,fd,restart=False):
        label=rid+('-restart' if restart else '')
        with (output/(label+'-worker.log')).open('w') as log:
            child=original_popen(['/b6b7-native/native-zero-worker',str(config)],pass_fds=[fd],stdout=log,stderr=subprocess.STDOUT)
        workers[label]=child;return child
    try:
        for robot in configuration.robots:
            writer,worker=socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET|socket.SOCK_NONBLOCK)
            trace,sink=socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET|socket.SOCK_NONBLOCK)
            endpoints.extend([writer,worker,trace,sink]);gazebo_fds.extend([writer.fileno(),trace.fileno()]);trace_ends.append((sink.fileno(),robot.id))
            provision=Path('/run/c5-b6b7')/(robot.id+'.json');budgets=json.loads(provision.read_text())
            driver=tree.find('.//model[@name="'+robot.id+'"]/plugin[@name="c5::test::SplitZeroDiffDrive"]')
            boot=secrets.token_hex(32)
            config=output/(robot.id+'-worker-config.json')
            atomic(config,dict(fd=worker.fileno(),boot=boot,provision=str(provision),namespace=robot.namespace,robot_id=robot.id,
                odom_frame=driver.findtext('frame_id'),child_frame=driver.findtext('child_frame_id'),
                audit=str(output/(robot.id+'-worker-audit.jsonl')),fault_file=str(output/(robot.id+'-worker-fault.json'))))
            child=start_worker(robot.id,config,worker.fileno())
            for key,value in dict(split_fd=writer.fileno(),trace_fd=trace.fileno(),writer_boot=boot,worker_pid=child.pid,
                ticket_sec=budgets['ticket_sec'],lease_sec=budgets['lease_sec'],
                trace_period_sec=configuration.fleet.perception_safety.timer_period_sec).items():
                ET.SubElement(driver,key).text=str(value)
            manifest[robot.id]=dict(pid=child.pid,writer_boot=boot,config=str(config),worker_fd=worker.fileno(),
                fixture_retains_restart_endpoint=True,auto_restart=False)
        tree.write(output/'generated/warehouse.sdf',encoding='utf-8',xml_declaration=True)
        record_command=['/b6b7-native/split-recorder',str(output/'writer.jsonl')]
        for fd,rid in trace_ends:record_command.extend([str(fd),rid])
        with (output/'recorder.log').open('w') as log:
            recorder=original_popen(record_command,pass_fds=[fd for fd,_ in trace_ends],stdout=log,stderr=subprocess.STDOUT)
        for name,command in commands:
            if name=='gazebo':
                engine=command[command.index('--physics-engine')+1]
                command[:]=['/b6b7-native/split-server',str(output/'generated/warehouse.sdf'),engine]
        def launch(command,*args,**kwargs):
            if command[0]=='/b6b7-native/split-server':
                kwargs['pass_fds']=gazebo_fds
            return original_popen(command,*args,**kwargs)
        atomic(output/'workers.json',manifest)
        def restarts():
            while not restart_stop.wait(.05):
                if (output/'workers-stop-request.json').exists():
                    stopped={}
                    for label,child in workers.items():
                        if child.poll() is None:child.send_signal(signal.SIGCONT);child.send_signal(signal.SIGINT)
                    for label,child in workers.items():
                        try:child.wait(timeout=4.)
                        except subprocess.TimeoutExpired:stopped[label+'_timeout']=True
                        stopped[label]=child.poll()
                    atomic(output/'workers-stopped.json',stopped)
                    return
                path=output/'worker-restart-request.json'
                if not path.exists():continue
                rid=json.loads(path.read_text())['robot_id'];entry=manifest[rid]
                if 'restart_pid' in entry:continue
                assert workers[rid].poll() is not None
                child=start_worker(rid,Path(entry['config']),entry['worker_fd'],restart=True)
                entry['restart_pid']=child.pid;atomic(output/'workers.json',manifest)
        thread=threading.Thread(target=restarts,daemon=True);thread.start()
        subprocess.Popen=launch
        return original_run(commands,namespaces,emit)
    finally:
        subprocess.Popen=original_popen;restart_stop.set()
        if 'thread' in locals():thread.join(timeout=2.)
        exits={}
        for name,child in workers.items():
            if child.poll() is None:
                child.send_signal(signal.SIGCONT);child.send_signal(signal.SIGINT)
            try:child.wait(timeout=4.)
            except subprocess.TimeoutExpired:child.kill();child.wait();exits[name+'_forced']=True
            exits[name]=child.returncode
        if recorder:
            if recorder.poll() is None:recorder.send_signal(signal.SIGINT)
            try:recorder.wait(timeout=3.)
            except subprocess.TimeoutExpired:recorder.kill();recorder.wait();exits['recorder_forced']=True
            exits['recorder']=recorder.returncode
        for endpoint in endpoints:endpoint.close()
        if output:atomic(output/'worker-shutdown.json',exits)
        if any(v!=0 and v!=-9 for v in exits.values()) or any(k.endswith('_forced') for k in exits):
            raise RuntimeError('Split fixture shutdown failed: '+str(exits))


server.generate=generate;server.run_simulation=run
if __name__=='__main__':raise SystemExit(server.main())
