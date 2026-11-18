import time,json,subprocess,sys
from pathlib import Path
m=json.loads(Path('/tmp/c5-perf-active.json').read_text());assert Path(m['root']).resolve()==Path.cwd().resolve(), 'Foreign workspace manifest';root=Path('/tmp')/m['name'];deadline=time.monotonic()+310
while time.monotonic()<deadline:
 try:
  s=json.loads((root/'session.json').read_text())
  if len(s.get('robots',[]))==3:break
 except (ValueError,OSError):pass
 time.sleep(1)
else:raise RuntimeError('launcher readiness not complete')
subprocess.run(['docker','cp','/tmp/c5-perf-tools',m['name']+':/tmp/perf-tools'],check=True)
if sys.argv[1]=='composition':
 subprocess.run(['docker','exec',m['name'],'bash','-c','source /opt/ros/humble/setup.bash; python3 /tmp/perf-tools/composition_audit.py'],check=True)
subprocess.run([sys.executable,'/tmp/c5-perf-tools/run_window.py',sys.argv[1],'180','chrome','submit'],check=True)
for script in ['summary.py','details.py']:subprocess.run([sys.executable,'/tmp/c5-perf-tools/'+script,str(root)],check=True)
