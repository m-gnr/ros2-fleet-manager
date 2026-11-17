#!/usr/bin/env python3
"""Start the idle C5 warehouse dashboard without submitting a task."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

from c5_session_cleanup import CleanupError, run


IMAGE = "ros2-fleet-c5-validation:humble-fortress"
EXPECTED_ROBOTS = {"robot_alpha", "robot_beta", "robot_gamma"}


def available_port(start: int, excluded: set[int]) -> int:
    for port in range(start, start + 100):
        if port in excluded:
            continue
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
        return port
    raise CleanupError(f"{start} aralığında boş port bulunamadı")


def api_get(port: int, path: str) -> dict:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=3) as response:
        return json.load(response)


def main() -> int:
    root = Path(sys.argv[1]).resolve()
    session_id = os.environ.get("C5_SESSION_ID", "")
    domain = os.environ.get("ROS_DOMAIN_ID", "")
    if not session_id or not domain.isdigit():
        raise CleanupError("C5_SESSION_ID veya benzersiz ROS_DOMAIN_ID eksik")
    profile = root / "config/fleet.warehouse-30x18.yaml"
    config_check = subprocess.run([sys.executable, "-m", "fleet_config", str(profile)], cwd=root)
    if config_check.returncode:
        raise CleanupError("Üç robotlu C5 profil doğrulaması başarısız")
    test_check = subprocess.run([sys.executable, "docker/simulation-warehouse-grid/test_startup_readiness.py"], cwd=root)
    if test_check.returncode:
        raise CleanupError("Üç robotlu AMCL/Nav2/TF readiness testi başarısız")
    run(["docker", "image", "inspect", IMAGE])

    api_port = available_port(int(os.environ.get("C5_API_PORT", "21482")), set())
    ui_port = available_port(int(os.environ.get("C5_UI_PORT", str(api_port + 2))), {api_port})
    scene_port = api_port + 1
    if scene_port in (api_port, ui_port):
        scene_port = available_port(api_port + 3, {api_port, ui_port})

    evidence = Path("/tmp") / session_id
    evidence.mkdir(mode=0o700, parents=True, exist_ok=False)
    (evidence / "live").mkdir()
    build = (
        "set -e; source /opt/ros/humble/setup.bash; cd /workspace; "
        "colcon --log-base /evidence/overlay-log build "
        "--base-paths interfaces/fleet_interfaces ros2_ws/src/fleet_perception "
        "--build-base /evidence/overlay-build --install-base /evidence/overlay-install; "
        "source /evidence/overlay-install/setup.bash; "
        "export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:"
        "/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:${PYTHONPATH:-}; "
        "exec python3 docker/simulation-warehouse-grid/stage1_run.py "
        "config/fleet.warehouse-30x18.yaml /evidence/live "
        f"--api-port {api_port} --scene-port {scene_port} "
        f"--origin http://127.0.0.1:{ui_port} --ros-overlay /evidence/overlay-install"
    )
    run([
        "docker", "run", "--detach", "--init", "--name", session_id, "--network", "bridge",
        "--add-host", "scene:127.0.0.1",
        "--workdir", "/workspace", "--env", f"ROS_DOMAIN_ID={domain}",
        "--env", f"IGN_PARTITION={session_id}", "--env", "RMW_IMPLEMENTATION=rmw_cyclonedds_cpp",
        "--env", "ROS_LOCALHOST_ONLY=0", "--env", f"C5_SESSION_ID={session_id}",
        "--publish", f"127.0.0.1:{api_port}:{api_port}",
        "--volume", f"{evidence}:/evidence", "--volume", f"{root}:/workspace:ro",
        IMAGE, "bash", "-ec", build,
    ], timeout=60)
    (evidence / "session.json").write_text(json.dumps({
        "session_id": session_id, "ros_domain_id": int(domain), "workspace": str(root),
        "container_name": session_id, "api_port": api_port, "scene_port": scene_port,
        "ui_port": ui_port, "started_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "expected_robots": sorted(EXPECTED_ROBOTS), "task_submissions": 0,
    }, indent=2) + "\n")

    readiness_path = evidence / "live/startup-readiness.json"
    deadline = time.monotonic() + 300
    readiness = None
    snapshot = None
    while time.monotonic() < deadline:
        state = json.loads(run(["docker", "inspect", session_id]))[0].get("State", {})
        if not state.get("Running"):
            log = run(["docker", "logs", session_id], check=False)
            raise CleanupError(f"C5 container erken çıktı: {state}; son log: {log[-2000:]}")
        if readiness_path.exists():
            try:
                readiness = json.loads(readiness_path.read_text())
            except (OSError, json.JSONDecodeError):
                readiness = None
        try:
            health = api_get(api_port, "/api/health")
            snapshot = api_get(api_port, "/api/robots")
            tasks = api_get(api_port, "/api/tasks")
            robot_rows = snapshot.get("robots", [])
            ids = {item.get("robot_id") for item in robot_rows}
            idle = all(item.get("active_task_id") is None and item.get("state") == "IDLE"
                       and item.get("telemetry") == "LIVE" and item.get("pose_reliability") == "LIVE"
                       for item in robot_rows)
            phases_ready = bool(readiness and set(readiness.get("robots", {})) == EXPECTED_ROBOTS and
                                set(readiness.get("required_phases", [])) == {"amcl", "nav2", "tf"} and
                                all(readiness["robots"][robot].get(phase, {}).get("ready") is True
                                    for robot in EXPECTED_ROBOTS for phase in ("amcl", "nav2", "tf")))
            if (readiness and readiness.get("status") == "READY" and
                    readiness.get("current_status") == "READY" and phases_ready and
                    health.get("source") == "LIVE" and ids == EXPECTED_ROBOTS and idle and
                    tasks.get("task_counts", {}).get("total") == 0 and
                    tasks.get("task_counts", {}).get("active") == 0):
                break
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(0.5)
    else:
        raise CleanupError(f"300 sn içinde üç robot için gerçek AMCL/Nav2/TF readiness sağlanmadı; container={session_id}")

    gui_log = (evidence / "gui-vite.log").open("ab", buffering=0)
    gui_env = os.environ.copy()
    gui_env.update({"C5_API_PORT": str(api_port), "C5_UI_PORT": str(ui_port),
                    "C5_SESSION_ID": session_id, "ROS_DOMAIN_ID": str(domain)})
    gui = subprocess.Popen([str(root / "frontend/node_modules/.bin/vite"), "--host", "127.0.0.1",
                            "--port", str(ui_port), "--strictPort"], cwd=root / "frontend",
                           env=gui_env, stdout=gui_log, stderr=subprocess.STDOUT, start_new_session=True)
    ui_deadline = time.monotonic() + 20
    while time.monotonic() < ui_deadline:
        if gui.poll() is not None:
            raise CleanupError(f"Vite GUI dev server erken çıktı; log={evidence / 'gui-vite.log'}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{ui_port}/", timeout=1) as response:
                if response.status == 200:
                    break
        except OSError:
            time.sleep(0.25)
    else:
        raise CleanupError(f"GUI HTTP readiness timeout; log={evidence / 'gui-vite.log'}")
    (evidence / "session.json").write_text(json.dumps({
        "session_id": session_id, "ros_domain_id": int(domain), "workspace": str(root),
        "container_name": session_id, "api_port": api_port, "scene_port": scene_port,
        "ui_port": ui_port, "vite_pid": gui.pid,
        "started_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "ready_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "robots": sorted(EXPECTED_ROBOTS), "readiness": readiness,
        "tasks": tasks, "task_submissions": 0,
    }, indent=2) + "\n")
    print(json.dumps({"result": "READY", "session_id": session_id, "ros_domain_id": int(domain),
                      "container": session_id, "api": f"http://127.0.0.1:{api_port}",
                      "gui": f"http://127.0.0.1:{ui_port}/", "robots": sorted(EXPECTED_ROBOTS),
                      "task_counts": tasks.get("task_counts"), "evidence": str(evidence)}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CleanupError as error:
        print(f"C5 demo start başarısız: {error}", file=sys.stderr)
        raise SystemExit(2)
