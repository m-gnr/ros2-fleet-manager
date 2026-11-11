"""Real process regression for controlled ROS entity/context shutdown on Unix signals."""
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time
import pytest

pytest.importorskip('rclpy',reason='Requires ROS 2 Humble runtime')
pytest.importorskip('fleet_interfaces.msg',reason='Requires generated fleet_interfaces')


@pytest.mark.parametrize('stop_signal',[signal.SIGINT,signal.SIGTERM])
def test_battery_process_finishes_entities_and_context_on_signal(stop_signal):
    from fleet_config import load_config
    profile=Path(__file__).resolve().parents[1]/'config/fleet.yaml'
    robot=load_config(profile).robots[0].id
    code='''import rclpy
from fleet_battery_simulator.node import BatterySimulatorNode, main
original=BatterySimulatorNode.from_config

def ready(*args):
    node=original(*args)
    print('BATTERY_READY',flush=True)
    return node
BatterySimulatorNode.from_config=ready
try:
    main()
finally:
    print('CONTEXT_CLOSED='+str(not rclpy.ok()),flush=True)
'''
    child=subprocess.Popen([sys.executable,'-c',code,'--fleet-config',str(profile),'--robot-id',robot],
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,bufsize=0,env={**os.environ,'PYTHONUNBUFFERED':'1'})
    try:
        prefix=b''
        deadline=time.monotonic()+15
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout,selectors.EVENT_READ)
            while b'BATTERY_READY\n' not in prefix:
                remaining=deadline-time.monotonic()
                assert remaining>0 and selector.select(timeout=remaining),prefix.decode(errors='replace')
                chunk=os.read(child.stdout.fileno(),4096)
                assert chunk,prefix.decode(errors='replace')
                prefix+=chunk
        child.send_signal(stop_signal)
        remainder=(prefix+child.communicate(timeout=5)[0]).decode(errors='replace')
        assert child.returncode==0,remainder
        assert 'CONTEXT_CLOSED=True' in remainder
        assert 'Traceback' not in remainder
    finally:
        if child.poll() is None:
            child.kill();child.wait(timeout=5)
