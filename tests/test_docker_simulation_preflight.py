import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "scripts/docker_simulation_preflight.py"


FAKE_DOCKER = textwrap.dedent(
    r'''
    #!/usr/bin/env python3
    import json, os, sys
    args = sys.argv[1:]
    scenario = os.environ.get("PREFLIGHT_SCENARIO", "single")
    log = os.environ["DOCKER_CALL_LOG"]
    with open(log, "a") as stream:
        stream.write(" ".join(args) + "\\n")
    def output(value):
        print(json.dumps(value))
    if args[:1] == ["compose"]:
        raise SystemExit(0)
    if args[:1] == ["ps"]:
        rows = []
        if scenario == "conflict":
            rows = [
                {"ID":"sim-id", "Names":"other-sim", "State":"running"},
                {"ID":"sim-two-id", "Names":"other-sim-two", "State":"running"},
                {"ID":"api-id", "Names":"other-api", "State":"running"},
            ]
        elif scenario == "single":
            rows = [{"ID":"current-id", "Names":"current-sim", "State":"running"}]
        for row in rows:
            output(row)
    elif args[:1] == ["inspect"]:
        result = []
        for cid in args[1:]:
            service = "simulation" if cid in ("sim-id", "sim-two-id", "current-id") else "backend"
            project = "current-demo" if cid == "current-id" else "manual-demo"
            result.append({
                "Id": cid,
                "State": {"Status":"running"},
                "Config": {"Labels": {
                    "com.docker.compose.project":project,
                    "com.docker.compose.service":service,
                    "com.docker.compose.project.config_files":"docker-compose.simulation.yml",
                }},
            })
        print(json.dumps(result))
    elif args[:1] == ["stats"]:
        if scenario == "conflict":
            output({"Name":"other-sim", "CPUPerc":"25.0%", "MemUsage":"512MiB / 4GiB"})
            output({"Name":"other-sim-two", "CPUPerc":"15.0%", "MemUsage":"384MiB / 4GiB"})
            output({"Name":"other-api", "CPUPerc":"5.0%", "MemUsage":"128MiB / 4GiB"})
        elif scenario == "single":
            output({"Name":"current-sim", "CPUPerc":"10.0%", "MemUsage":"256MiB / 4GiB"})
    elif args[:1] == ["top"]:
        if args[1] in ("sim-id", "sim-two-id", "current-id"):
            print("PID COMMAND\\n10 ign gazebo -r warehouse.sdf")
        else:
            print("PID COMMAND\\n11 python3 -m backend.dashboard.api")
    elif args[:1] == ["info"]:
        if scenario == "measurement-fail":
            print("Docker info unavailable", file=sys.stderr)
            raise SystemExit(1)
        output({"NCPU":8, "MemTotal":8589934592})
    else:
        raise SystemExit("unexpected fake docker args: " + repr(args))
    '''
).lstrip()


class DockerSimulationPreflightTests(unittest.TestCase):
    def run_preflight(self, scenario, *preflight_args):
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            docker_bin = bin_dir / "docker"
            docker_bin.write_text(FAKE_DOCKER)
            docker_bin.chmod(0o755)
            log = Path(tmp) / "docker-calls.log"
            env = os.environ.copy()
            env.update({
                "PATH": str(bin_dir) + os.pathsep + env.get("PATH", ""),
                "DDS_TEST_PAYLOAD": "current-demo",
                "DOCKER_CALL_LOG": str(log),
                "PREFLIGHT_SCENARIO": scenario,
            })
            proc = subprocess.run(
                ["python3", str(PREFLIGHT), "--project-name", "current-demo", *preflight_args], cwd=ROOT, env=env,
                text=True, capture_output=True,
            )
            return proc, log.read_text() if log.exists() else ""

    def test_single_existing_simulation_in_target_project_is_reported(self):
        proc, calls = self.run_preflight("single")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Hedef Compose projesinde zaten aktif simülasyon var: current-demo", proc.stdout)
        self.assertIn("Başka aktif Gazebo/Nav2 simülasyonu saptanmadı", proc.stdout)
        self.assertNotIn("stop", calls)

    def test_other_simulation_blocks_startup_without_stopping_containers(self):
        proc, calls = self.run_preflight("conflict")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("other-sim", proc.stdout)
        self.assertIn("other-sim-two", proc.stdout)
        self.assertIn("Başlangıç engellendi", proc.stdout)
        self.assertNotIn("compose -p", calls)
        self.assertNotIn("stop", calls)

    def test_explicit_concurrent_override_is_logged_and_reaches_compose(self):
        proc, calls = self.run_preflight("conflict", "--allow-concurrent-simulation")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OVERRIDE: --allow-concurrent-simulation kullanıldı", proc.stdout)
        self.assertNotIn("stop", calls)

    def test_unavailable_resource_measurement_fails_closed(self):
        proc, calls = self.run_preflight("measurement-fail")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("ölçümü başarısız", proc.stderr)
        self.assertNotIn("compose -p", calls)


if __name__ == "__main__":
    unittest.main()
