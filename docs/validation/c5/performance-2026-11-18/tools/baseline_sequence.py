import time,json,subprocess,sys
from pathlib import Path
m=json.loads(Path('/tmp/c5-perf-active.json').read_text());assert Path(m['root']).resolve()==Path.cwd().resolve(), 'Foreign workspace manifest';root=Path('/tmp')/m['name'];deadline=time.monotonic()+320
while time.monotonic()<deadline:
 try:
  s=json.loads((root/'session.json').read_text())
  if len(s.get('robots',[]))==3:break
 except (ValueError,OSError):pass
 time.sleep(1)
else:raise RuntimeError('launcher readiness not complete')
subprocess.run(['docker','cp','/tmp/c5-perf-tools',m['name']+':/tmp/perf-tools'],check=True)
for label,seconds,mode,extra in [('idle-minimal',25,'minimal',[]),('idle-probes',25,'probes',[]),('baseline-three-moving',180,'chrome',['submit'])]:
 print('START',label,flush=True);subprocess.run([sys.executable,'/tmp/c5-perf-tools/run_window.py',label,str(seconds),mode]+extra,check=True);print('END',label,flush=True)
subprocess.run([sys.executable,'/tmp/c5-perf-tools/summary.py',str(root)],check=True)
