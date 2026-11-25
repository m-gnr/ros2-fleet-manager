"""Opt-in crash capture for this zero-only fixture; no signal/exit masking."""
import json
import os
from pathlib import Path
import resource
import sys


def prefix(output):
    return [sys.executable,str(Path(__file__).resolve()),str(output),'--']


def wrap(name,command,output):
    if os.environ.get('C5_1B_DIAGNOSTICS')=='1' and name=='command_bridge':
        return prefix(output/'cores'/name)+command
    return command


def main():
    output=Path(sys.argv[1]).resolve()/str(os.getpid());output.mkdir(parents=True,exist_ok=False)
    command=sys.argv[2:]
    if command[0]=='--':command=command[1:]
    soft,hard=resource.getrlimit(resource.RLIMIT_CORE)
    resource.setrlimit(resource.RLIMIT_CORE,(hard,hard))
    (output/'process.json').write_text(json.dumps(dict(pid=os.getpid(),argv=command,previous_core_limit=[soft,hard]),indent=2)+'\n')
    os.chdir(output)
    if (os.environ.get('C5_1B_MEMCHECK')=='1' and 'command_bridge' in output.parts):
        command=['valgrind','--error-exitcode=91','--leak-check=no','--track-origins=yes',
            '--num-callers=30','--log-file='+str(output/'memcheck.log'),*command]
    os.execvp(command[0],command)


if __name__=='__main__':main()
