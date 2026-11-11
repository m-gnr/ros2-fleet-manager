"""Run a finite live regression plan; preserve evidence before removing own projects."""
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time


def main():
    plan_path=Path(sys.argv[1]).resolve();plan=json.loads(plan_path.read_text());results=[]
    for case in plan:
        project=case['project']
        if not project.startswith('fleet-c5-stage13-'):raise ValueError('Only this task owns these projects')
        out=plan_path.parent/case['name'];out.mkdir(exist_ok=False)
        env={**os.environ,'DDS_TEST_PAYLOAD':project,'ROS_DOMAIN_ID':str(case['domain']),
            'ROS_LOCALHOST_ONLY':'0','C333_HIGH_PREEMPTION':str(int(case.get('high',False))),
            'C333_AUTO_ROUTES':'0','C333_ENERGY_POLICY':'0','C43_EVIDENCE_DIR':str(out)}
        command=['docker','compose','-p',project]
        for layer in case['layers']:command+=['-f',layer]
        config=subprocess.check_output([*command,'config','--format','json'],env=env,text=True)
        (out/'compose.json').write_text(config)
        settings=json.loads(config)
        for service in settings['services'].values():
            subprocess.run(['docker','image','inspect',service['image']],stdout=subprocess.DEVNULL,check=True)
            for volume in service.get('volumes',[]):
                if volume.get('type')=='bind' and not Path(volume['source']).exists():raise FileNotFoundError(volume['source'])
        started=time.monotonic();code=None;error=None
        try:
            with (out/'run.log').open('w') as log:
                run=subprocess.run([*command,'up','--no-build','--abort-on-container-exit','--exit-code-from','backend'],
                    stdout=log,stderr=subprocess.STDOUT,env=env,timeout=480)
                code=run.returncode
        except subprocess.TimeoutExpired as exc:
            error=str(exc)
            subprocess.run([*command,'stop','--timeout','40'],env=env,stdout=subprocess.DEVNULL)
        finally:
            ids=subprocess.check_output([*command,'ps','-a','-q'],env=env,text=True).splitlines()
            inspections=json.loads(subprocess.check_output(['docker','inspect',*ids],text=True)) if ids else []
            (out/'docker-inspect.json').write_text(json.dumps(inspections,indent=2))
            backend=next((d['Id'] for d in inspections if d['Config']['Labels'].get('com.docker.compose.service')=='backend'),None)
            copies=[]
            if backend:
                for path in case.get('databases',[]):
                    dest=out/Path(path).name
                    copied=subprocess.run(['docker','cp',backend+':'+path,str(dest)],capture_output=True,text=True)
                    copies.append(dict(source=path,exit_code=copied.returncode,error=copied.stderr.strip()))
            checks=[]
            for db in list(out.glob('*.db'))+list(out.glob('*.sqlite3')):
                with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True) as con:
                    checks.append(dict(file=db.name,integrity=con.execute('PRAGMA integrity_check').fetchall(),foreign_keys=con.execute('PRAGMA foreign_key_check').fetchall()))
            text=(out/'run.log').read_text()
            clean='"event": "SIMULATION_SHUTDOWN", "clean": true' in text
            markers={pattern:bool(re.search(pattern,text)) for pattern in case['markers']}
            all_exits=len(inspections)==2 and all(d['State']['ExitCode']==0 and not d['State']['OOMKilled'] for d in inspections)
            passed=code==0 and clean and all_exits and all(markers.values()) and all(c['exit_code']==0 for c in copies)
            passed=passed and all(c['integrity']==[('ok',)] and not c['foreign_keys'] for c in checks)
            result=dict(name=case['name'],project=project,domain=case['domain'],compose_exit=code,error=error,shutdown_clean=clean,
                all_container_exits_clean=all_exits,markers=markers,database_copies=copies,sqlite=checks,passed=passed,wall_s=time.monotonic()-started)
            (out/'result.json').write_text(json.dumps(result,indent=2))
            results.append(result);plan_path.with_suffix('.results.json').write_text(json.dumps(results,indent=2))
            # Only the finite, named project above is removed; volumes remain intact.
            with (out/'down.log').open('w') as log:
                subprocess.run([*command,'down'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        print(json.dumps(result),flush=True)
    raise SystemExit(1 if any(not r['passed'] for r in results) else 0)

if __name__=='__main__':main()
