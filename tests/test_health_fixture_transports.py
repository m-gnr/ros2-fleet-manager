"""Real owned-process cleanup test; no ROS, simulator or robot is started."""
import json
from pathlib import Path
import signal
import subprocess
import sys
import time


def test_fixture_transport_wrapper_stops_both_owned_children_cleanly(tmp_path):
    child=tmp_path/'child.py'
    child.write_text('import signal,time\nstop=False\ndef end(*_):\n global stop\n stop=True\nsignal.signal(signal.SIGINT,end)\nwhile not stop:time.sleep(.01)\n')
    command=json.dumps([sys.executable,str(child)])
    process=subprocess.Popen([sys.executable,'docker/experiments/c5-t3b/transports.py',str(tmp_path),command,command])
    try:
        deadline=time.monotonic()+5.
        while not (tmp_path/'fault-processes.json').exists() and time.monotonic()<deadline:time.sleep(.01)
        assert (tmp_path/'fault-processes.json').exists()
        time.sleep(.1)
        process.send_signal(signal.SIGINT);assert process.wait(timeout=5.)==0
        assert json.loads((tmp_path/'transport-shutdown.json').read_text())=={'odometry_link':0,'tf_helper':0}
    finally:
        if process.poll() is None:process.send_signal(signal.SIGTERM);process.wait(timeout=5.)
