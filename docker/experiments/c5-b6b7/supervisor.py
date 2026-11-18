"""Use existing C5 supervision with only the isolated simulation entry changed."""
import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "docker/simulation-warehouse-grid"))
original = subprocess.Popen


def popen(command, *args, **kwargs):
    if isinstance(command, list) and len(command) > 1 and command[1] == "docker/simulation-warehouse-grid/serve.py":
        command = command.copy()
        command[1] = str(Path(__file__).with_name("server.py"))
    return original(command, *args, **kwargs)


subprocess.Popen = popen
spec = importlib.util.spec_from_file_location("stage1_supervisor", ROOT / "docker/simulation-warehouse-grid/stage1_run.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
if __name__ == "__main__":
    module.main()
