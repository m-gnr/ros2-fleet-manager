"""Own only this fixture's odometry bridge and TF helper; stop before physics."""
import json
from pathlib import Path
import signal
import subprocess
import sys
import time


def main():
    output=Path(sys.argv[1]);commands=dict(odometry_link=json.loads(sys.argv[2]),tf_helper=json.loads(sys.argv[3]))
    stopping=False
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    children={};exits={}
    try:
        for name,command in commands.items():children[name]=subprocess.Popen(command)
        temporary=output/'fault-processes.tmp'
        temporary.write_text(json.dumps({n:dict(pid=p.pid,command=commands[n]) for n,p in children.items()},indent=2)+'\n')
        temporary.replace(output/'fault-processes.json')
        while not stopping:
            if any(p.poll() is not None for p in children.values()):raise RuntimeError('Fixture transport exited')
            time.sleep(.05)
    finally:
        for child in children.values():
            if child.poll() is None:child.send_signal(signal.SIGINT)
        for name,child in children.items():
            try:child.wait(timeout=2.)
            except subprocess.TimeoutExpired:
                child.kill();child.wait();exits[name+'_forced']=True
            exits[name]=child.returncode
        (output/'transport-shutdown.json').write_text(json.dumps(exits,indent=2)+'\n')
        if any(value!=0 for value in exits.values()):raise RuntimeError('Fixture transport shutdown failed: '+str(exits))


if __name__=='__main__':main()
