"""Finite sequential experiment plan; preserve failures and return aggregate failure."""
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    plan_path=Path(sys.argv[1]);plan=json.loads(plan_path.read_text());results=[]
    for item in plan:
        command=[sys.executable,'docker/simulation-warehouse-grid/stage13_run.py',*item['args'],'--collect-after-shutdown-failure']
        started=time.monotonic();result=subprocess.run(command)
        results.append(dict(name=item['name'],command=command,exit_code=result.returncode,wall_s=time.monotonic()-started))
        plan_path.with_suffix('.results.json').write_text(json.dumps(results,indent=2))
    raise SystemExit(1 if any(r['exit_code'] for r in results) else 0)

if __name__=='__main__':main()
