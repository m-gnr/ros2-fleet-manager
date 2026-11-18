import os,sys,time,json,threading,subprocess
from pathlib import Path
out=Path(sys.argv[1]);seconds=float(sys.argv[2]);out.mkdir(exist_ok=True,parents=True)
end=time.monotonic()+seconds
lock=threading.Lock(); f=(out/'system.jsonl').open('w')
def record(kind,**v):
 with lock:f.write(json.dumps(dict(kind=kind,mono=time.monotonic(),utc=time.time(),**v))+'\n')
def stats():
 p=subprocess.Popen(['ign','topic','-e','-t','/world/warehouse_grid/stats','--json-output','-d',str(seconds)],stdout=subprocess.PIPE,text=True)
 for line in p.stdout:
  try:record('gazebo',data=json.loads(line))
  except ValueError:pass
 p.wait()
t=threading.Thread(target=stats,daemon=True);t.start()
page=os.sysconf('SC_PAGE_SIZE');ticks=os.sysconf('SC_CLK_TCK');prev={};last_seq=None;next_proc=0
while time.monotonic()<end:
 now=time.monotonic()
 try:
  path=Path('/tmp/stage1/latest.json'); s=json.loads(path.read_text());seq=s['fleet']['sequence']
  record('snapshot',age=(time.monotonic_ns()-s['captured_monotonic_ns'])/1e9,sequence=seq,mtime=path.stat().st_mtime,changed=seq!=last_seq)
  last_seq=seq
 except (OSError,ValueError,KeyError):pass
 if now>=next_proc:
  next_proc=now+1;rows=[]
  for d in Path('/proc').glob('[0-9]*'):
   try:
    cmd=(d/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
    a=(d/'stat').read_text().rsplit(')',1)[1].split();cpu=(int(a[11])+int(a[12]))/ticks
    ctx=0
    for td in (d/'task').glob('*'):
     ctx+=sum(int(line.split(':')[1]) for line in (td/'status').read_text().splitlines() if line.startswith(('voluntary_ctxt_switches:','nonvoluntary_ctxt_switches:')))
    pid=int(d.name);old=prev.get(pid);prev[pid]=(now,cpu,ctx)
    rows.append(dict(pid=pid,cmd=cmd,cpu=100*(cpu-old[1])/(now-old[0]) if old else None,rss=int(a[21])*page,ctx_s=(ctx-old[2])/(now-old[0]) if old else None))
   except (OSError,ValueError,IndexError):pass
  cg={}
  for name in ('memory.current','memory.peak','memory.max','cpu.stat','cpu.max','cpu.pressure','memory.pressure'):
   try:cg[name]=Path('/sys/fs/cgroup',name).read_text().strip()
   except OSError:pass
  record('proc',rows=rows,cgroup=cg)
 time.sleep(.1)
t.join(timeout=2);f.close()
