import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'scripts'));import start_demo
m=json.loads(Path('/tmp/c5-perf-active.json').read_text());p=Path('/tmp')/m['name'];root=Path(m['root']);assert root.resolve()==Path.cwd().resolve(), 'Foreign workspace manifest'
s=json.loads((p/'session.json').read_text());start_demo.stop_gui(p,s['ui_port'],root);import subprocess
item=json.loads(subprocess.check_output(['docker','inspect',m['name']]))[0]
env=dict(x.split('=',1) for x in item['Config']['Env'] if '=' in x)
assert item['Name']=='/'+m['name'] and env['C5_SESSION_ID']==m['name'] and env['IGN_PARTITION']==m['name'] and int(env['ROS_DOMAIN_ID'])==int(m['domain'])
assert any(x['Destination']=='/workspace' and Path(x['Source']).resolve()==root.resolve() and not x['RW'] for x in item['Mounts'])
assert item['Config']['Image']=='ros2-fleet-c5-validation:humble-fortress'
subprocess.run(['docker','stop','--time','120',m['name']],check=True)
print('closed',m['name'])
