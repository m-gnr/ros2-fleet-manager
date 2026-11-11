"""Sample process CPU/RSS and cgroup memory; short observations do not prove peak load."""
import json
import os
from pathlib import Path
import signal
import sys
import time
stopping=False

def stop(*_):
    global stopping
    stopping=True
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
previous={};ticks=os.sysconf('SC_CLK_TCK');page=os.sysconf('SC_PAGE_SIZE')
with Path(sys.argv[1]).open('w') as out:
    while not stopping:
        now=time.monotonic();rows=[]
        for folder in Path('/proc').glob('[0-9]*'):
            try:
                command=(folder/'cmdline').read_bytes().replace(b'\x00',b' ').decode(errors='replace')
                if not any('/'+x in command for x in ('amcl','planner_server','controller_server','ign gazebo','gz-sim','ign-gazebo')):continue
                stat=(folder/'stat').read_text().rsplit(')',1)[1].split();cpu=(int(stat[11])+int(stat[12]))/ticks
                pid=int(folder.name);old=previous.get(pid);previous[pid]=(now,cpu)
                rows.append(dict(pid=pid,command=command,cpu_percent=100*(cpu-old[1])/(now-old[0]) if old else None,rss_bytes=int(stat[21])*page))
            except (OSError,ValueError,IndexError):pass
        out.write(json.dumps(dict(monotonic=now,processes=rows))+'\n');out.flush();time.sleep(.5)
