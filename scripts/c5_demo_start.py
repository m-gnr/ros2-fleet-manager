#!/usr/bin/env python3
"""Start the idle C5 warehouse dashboard without submitting a task."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import time
import urllib.request

from c5_session_cleanup import CleanupError, run


IMAGE = "ros2-fleet-c5-validation:humble-fortress"
OVERLAY_PACKAGES = (
    Path("interfaces/fleet_interfaces"), Path("ros2_ws/src/fleet_perception"),
    Path("ros2_ws/src/fleet_nav2_escape"),
)


def overlay_cache(root: Path) -> tuple[Path, str, str]:
    image_id = subprocess.check_output(
        ["docker", "image", "inspect", "--format", "{{.Id}}", IMAGE], text=True
    ).strip()
    digest = hashlib.sha256(image_id.encode())
    for package in OVERLAY_PACKAGES:
        package_root = root / package
        for path in sorted(item for item in package_root.rglob("*")
                            if item.is_file() and "__pycache__" not in item.parts
                            and item.suffix != ".pyc"):
            relative = path.relative_to(root).as_posix()
            digest.update(relative.encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
    fingerprint = digest.hexdigest()
    cache = Path("/tmp/ros2-fleet-c5-overlay") / fingerprint
    cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    metadata = {"fingerprint": fingerprint, "image_id": image_id,
                "packages": [package.as_posix() for package in OVERLAY_PACKAGES]}
    metadata_path = cache / "source.json"
    if not metadata_path.exists():
        temporary = cache / f"source.{os.getpid()}.tmp"
        temporary.write_text(json.dumps(metadata, indent=2) + "\n")
        os.replace(temporary, metadata_path)
    elif json.loads(metadata_path.read_text()) != metadata:
        raise CleanupError(f"overlay cache fingerprint mismatch: {cache}")
    return cache, fingerprint, image_id


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
    sys.path.insert(0, str(root))
    from fleet_config import load_config
    session_id = os.environ.get("C5_SESSION_ID", "")
    domain = os.environ.get("ROS_DOMAIN_ID", "")
    if not session_id or not domain.isdigit():
        raise CleanupError("C5_SESSION_ID veya benzersiz ROS_DOMAIN_ID eksik")
    profile = (root / os.environ.get("C5_DEMO_PROFILE", "config/fleet.warehouse-30x18.yaml")).resolve()
    try:
        profile.relative_to(root / "config")
    except ValueError as error:
        raise CleanupError("C5_DEMO_PROFILE yalnız bu workspace'in config dizininde olmalı") from error
    if not profile.is_file() or profile.suffix != ".yaml":
        raise CleanupError("C5_DEMO_PROFILE geçerli bir YAML dosyası olmalı")
    expected_robots = {robot.id for robot in load_config(profile).robots}
    config_check = subprocess.run([sys.executable, "-m", "fleet_config", str(profile)], cwd=root)
    if config_check.returncode:
        raise CleanupError("C5 profil doğrulaması başarısız")
    test_check = subprocess.run([sys.executable, "docker/simulation-warehouse-grid/test_startup_readiness.py"], cwd=root)
    if test_check.returncode:
        raise CleanupError("AMCL/Nav2/TF readiness testi başarısız")
    cache, _fingerprint, _image_id = overlay_cache(root)

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
        "if [[ ! -f /c5-cache/install/local_setup.bash ]]; then "
        "exec 9>/c5-cache/build.lock; flock 9; "
        "if [[ ! -f /c5-cache/install/local_setup.bash ]]; then "
        "colcon --log-base /c5-cache/log build "
        f"--base-paths {' '.join(shlex.quote(str(path)) for path in OVERLAY_PACKAGES)} "
        "--build-base /c5-cache/build --install-base /c5-cache/install; fi; "
        "flock -u 9; exec 9>&-; fi; "
        "source /c5-cache/install/local_setup.bash; "
        "export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:"
        "/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:${PYTHONPATH:-}; "
        "exec python3 docker/simulation-warehouse-grid/stage1_run.py "
        f"{shlex.quote(str(profile.relative_to(root)))} /evidence/live "
        f"--api-port {api_port} --scene-port {scene_port} "
        f"--origin http://127.0.0.1:{ui_port} --ros-overlay /c5-cache/install "
        "--peer-awareness-experiment --warehouse-escape"
    )
    run([
        "docker", "run", "--detach", "--init", "--name", session_id, "--network", "bridge",
        "--add-host", "scene:127.0.0.1",
        "--workdir", "/workspace", "--env", f"ROS_DOMAIN_ID={domain}",
        "--env", f"IGN_PARTITION={session_id}", "--env", "RMW_IMPLEMENTATION=rmw_cyclonedds_cpp",
        "--env", "ROS_LOCALHOST_ONLY=0", "--env", f"C5_SESSION_ID={session_id}",
        "--publish", f"127.0.0.1:{api_port}:{api_port}",
        "--volume", f"{evidence}:/evidence", "--volume", f"{root}:/workspace:ro",
        "--volume", f"{cache}:/c5-cache",
        IMAGE, "bash", "-ec", build,
    ], timeout=60)
    (evidence / "session.json").write_text(json.dumps({
        "session_id": session_id, "ros_domain_id": int(domain), "workspace": str(root),
        "container_name": session_id, "api_port": api_port, "scene_port": scene_port,
        "ui_port": ui_port, "started_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "expected_robots": sorted(expected_robots), "profile": str(profile.relative_to(root)), "task_submissions": 0,
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
            phases_ready = bool(readiness and set(readiness.get("robots", {})) == expected_robots and
                                set(readiness.get("required_phases", [])) == {"amcl", "nav2", "tf"} and
                                all(readiness["robots"][robot].get(phase, {}).get("ready") is True
                                    for robot in expected_robots for phase in ("amcl", "nav2", "tf")))
            if (readiness and readiness.get("status") == "READY" and
                    readiness.get("current_status") == "READY" and phases_ready and
                    health.get("source") == "LIVE" and ids == expected_robots and idle and
                    tasks.get("task_counts", {}).get("total") == 0 and
                    tasks.get("task_counts", {}).get("active") == 0):
                break
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(0.5)
    else:
        raise CleanupError(f"300 sn içinde AMCL/Nav2/TF readiness sağlanmadı; container={session_id}")

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
        "robots": sorted(expected_robots), "profile": str(profile.relative_to(root)), "readiness": readiness,
        "tasks": tasks, "task_submissions": 0,
    }, indent=2) + "\n")
    print(json.dumps({"result": "READY", "session_id": session_id, "ros_domain_id": int(domain),
                      "container": session_id, "api": f"http://127.0.0.1:{api_port}",
                      "gui": f"http://127.0.0.1:{ui_port}/", "robots": sorted(expected_robots),
                      "task_counts": tasks.get("task_counts"), "evidence": str(evidence)}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CleanupError as error:
        print(f"C5 demo start başarısız: {error}", file=sys.stderr)
        raise SystemExit(2)
