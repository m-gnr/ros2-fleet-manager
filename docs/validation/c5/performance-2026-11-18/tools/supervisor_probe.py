import sys,subprocess,runpy
old=subprocess.Popen
def popen(cmd,*a,**k):
 if isinstance(cmd,list) and cmd[1:3]==['-m','backend.dashboard.runtime']:cmd=[cmd[0],'/perf-tools/runtime_probe.py','manager']+cmd[3:]
 return old(cmd,*a,**k)
subprocess.Popen=popen
sys.path.insert(0,'/workspace/docker/simulation-warehouse-grid')
runpy.run_path('/workspace/docker/simulation-warehouse-grid/stage1_run.py',run_name='__main__')
