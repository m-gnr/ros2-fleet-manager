#!/usr/bin/env python3
"""Own one isolated C5 live demo session from startup through shutdown."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import time
import uuid


IMAGE = "ros2-fleet-c5-validation:humble-fortress"
RUNNER = "scripts/c5_demo_start.py"
_stop_signal: int | None = None


def signal_stop(signum: int, _frame) -> None:
    global _stop_signal
    _stop_signal = signum


def run(args: list[str], *, timeout: int = 30, check: bool = True) -> str:
    result = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def choose_domain(root: Path) -> int:
    output = run([sys.executable, str(root / "scripts/c5_session_cleanup.py"),
                  "--workspace", str(root), "--choose-domain"])
    return int(output)


def free_port(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.2)
        return probe.connect_ex(("127.0.0.1", port)) != 0


def session_container(root: Path, name: str) -> dict | None:
    raw = run(["docker", "inspect", name], check=False)
    if not raw:
        return None
    items = json.loads(raw)
    if items == []:
        return None
    if len(items) != 1:
        raise RuntimeError(f"unexpected Docker inspect result for {name}")
    item = items[0]
    mounts = [Path(m["Source"]).resolve() for m in item.get("Mounts", [])
              if m.get("Destination") == "/workspace" and m.get("Source")]
    command = " ".join(str(part) for part in
                       (item.get("Config", {}).get("Entrypoint") or []) +
                       (item.get("Config", {}).get("Cmd") or []))
    env = dict(entry.split("=", 1) for entry in item.get("Config", {}).get("Env", []) if "=" in entry)
    if (not re.fullmatch(r"c5-demo-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}", name)
            or root.resolve() not in mounts
            or item.get("Config", {}).get("Image") != IMAGE
            or "stage1_run.py" not in command
            or env.get("C5_SESSION_ID") != name
            or env.get("IGN_PARTITION") != name
            or not (env.get("ROS_DOMAIN_ID", "").isdigit())):
        raise RuntimeError(f"container {name} ownership could not be verified; leaving it untouched")
    return item


def gui_pid_from_evidence(evidence: Path, port: int, root: Path) -> int | None:
    session_file = evidence / "session.json"
    if not session_file.exists():
        return None
    session = json.loads(session_file.read_text())
    if session.get("ui_port") != port:
        raise RuntimeError("GUI port does not match this launcher's evidence")
    pid = session.get("vite_pid")
    if not isinstance(pid, int):
        # Startup may fail after Vite was spawned but before the final evidence update.
        listeners = run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"], check=False)
        candidates = [int(value) for value in listeners.splitlines() if value.isdigit()]
        for candidate in candidates:
            cwd = run(["lsof", "-a", "-p", str(candidate), "-d", "cwd", "-Fn"], check=False)
            command = run(["ps", "-p", str(candidate), "-o", "command="], check=False)
            if (any(line == f"n{root / 'frontend'}" for line in cwd.splitlines())
                    and "vite" in command.lower()):
                if pid is not None:
                    raise RuntimeError("multiple Vite listeners found on this session's port")
                pid = candidate
    if pid is None:
        return None
    process_state = run(["ps", "-p", str(pid), "-o", "stat="], check=False).strip()
    if not process_state or process_state.startswith("Z"):
        return None
    cwd = run(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"], check=False)
    command = run(["ps", "-p", str(pid), "-o", "command="], check=False)
    if not any(line == f"n{root / 'frontend'}" for line in cwd.splitlines()) or "vite" not in command.lower():
        raise RuntimeError(f"PID {pid} is not the verified Vite process; leaving it untouched")
    return pid


def stop_gui(evidence: Path, port: int | None, root: Path) -> None:
    if not port:
        return
    pid = gui_pid_from_evidence(evidence, port, root)
    if pid is None:
        if not free_port(port):
            raise RuntimeError(f"GUI port {port} remains busy, owner is not verified")
        return
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        state = run(["ps", "-p", str(pid), "-o", "stat="], check=False).strip()
        if not state or state.startswith("Z"):
            break
        time.sleep(0.1)
    else:
        raise RuntimeError(f"verified Vite process {pid} did not stop after SIGTERM")
    if not free_port(port):
        raise RuntimeError(f"GUI port {port} remains busy after Vite shutdown")


def stop_owned_container(root: Path, name: str) -> None:
    item = session_container(root, name)
    if item is None or not item.get("State", {}).get("Running"):
        return
    run(["docker", "stop", "--time", "120", name], timeout=135)
    item = session_container(root, name)
    if item and item.get("State", {}).get("Running"):
        raise RuntimeError(f"owned simulation container {name} remains running")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True, type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    if not (root / RUNNER).is_file():
        raise RuntimeError(f"C5 launcher is missing: {root / RUNNER}")
    if not (root / "frontend/node_modules/.bin/vite").exists():
        raise RuntimeError("frontend dependencies are unavailable; install them before starting the demo")
    run(["docker", "image", "inspect", IMAGE])
    name = "c5-demo-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12]
    domain = choose_domain(root)
    if session_container(root, name) is not None:
        raise RuntimeError(f"unique container name already exists: {name}")
    evidence = Path("/tmp") / name
    ui_port: int | None = None
    child: subprocess.Popen | None = None
    parent_pid = os.getppid()
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, signal_stop)
    try:
        env = os.environ.copy()
        env.update({"C5_SESSION_ID": name, "ROS_DOMAIN_ID": str(domain)})
        child = subprocess.Popen([sys.executable, str(root / RUNNER), str(root)], cwd=root,
                                 env=env, start_new_session=True)
        while child.poll() is None:
            if _stop_signal is not None or os.getppid() != parent_pid:
                if _stop_signal is None:
                    signal_stop(signal.SIGHUP, None)
                child.send_signal(signal.SIGTERM)
                try:
                    # c5_demo_start waits for Docker to finish the owned
                    # container's ordered ROS/Gazebo shutdown. Give that
                    # supervisor time to finish instead of killing its owner.
                    child.wait(timeout=150)
                except subprocess.TimeoutExpired:
                    raise RuntimeError("C5 session supervisor did not finish its graceful shutdown")
                if child.returncode != 0:
                    raise RuntimeError(f"C5 session supervisor exited {child.returncode} during shutdown")
                raise RuntimeError("startup interrupted")
            time.sleep(0.2)
        if child.returncode != 0:
            raise RuntimeError(f"existing C5 startup runner failed with exit {child.returncode}")
        session_path = evidence / "session.json"
        if not session_path.exists():
            raise RuntimeError("C5 startup reported success without session evidence")
        session = json.loads(session_path.read_text())
        ui_port = int(session["ui_port"])
        if session.get("session_id") != name or session.get("ros_domain_id") != domain:
            raise RuntimeError("session evidence does not match this launcher")
        url = f"http://127.0.0.1:{ui_port}/"
        print(f"\nREADY — üç robot, AMCL/Nav2/TF, API/WebSocket ve Vite hazır", flush=True)
        print(f"GUI: {url}", flush=True)
        print(f"Oturum: {name} (ROS_DOMAIN_ID={domain}); kanıt: {evidence}", flush=True)
        if sys.platform == "darwin":
            subprocess.run(["open", "-a", "Google Chrome", url], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(["google-chrome", url], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        while _stop_signal is None and os.getppid() == parent_pid:
            if not free_port(ui_port):
                time.sleep(1)
                continue
            raise RuntimeError("GUI listener stopped unexpectedly")
        print("\nKapanış sinyali alındı; bu oturumun servisleri durduruluyor…", flush=True)
        return 0
    finally:
        # Close the GUI first. The owned container's supervisor then stops API/manager,
        # ROS nodes, Nav2/AMCL and Gazebo in its established order.
        try:
            if ui_port is None and (evidence / "session.json").exists():
                ui_port = int(json.loads((evidence / "session.json").read_text()).get("ui_port"))
            stop_gui(evidence, ui_port, root)
        finally:
            stop_owned_container(root, name)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        print(f"Demo launcher failed: {error}", file=sys.stderr)
        raise SystemExit(2)
