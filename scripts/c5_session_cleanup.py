#!/usr/bin/env python3
"""Fail-closed cleanup for C5 sessions mounted from this worktree only."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shlex
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid


class CleanupError(RuntimeError):
    pass


def run(args: list[str], *, timeout: float = 30, check: bool = True,
        input_text: str | None = None) -> str:
    try:
        result = subprocess.run(args, input=input_text, text=True, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CleanupError(f"komut çalıştırılamadı: {' '.join(args)}: {error}") from error
    if check and result.returncode:
        raise CleanupError(f"komut başarısız ({result.returncode}): {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def docker_json(*args: str):
    output = run(["docker", *args])
    try:
        return json.loads(output)
    except json.JSONDecodeError as error:
        raise CleanupError(f"Docker JSON yanıtı çözümlenemedi: {args[0]}") from error


def docker_json_lines(*args: str) -> list[dict]:
    output = run(["docker", *args])
    try:
        return [json.loads(line) for line in output.splitlines() if line.strip()]
    except json.JSONDecodeError as error:
        raise CleanupError(f"Docker satır JSON yanıtı çözümlenemedi: {args[0]}") from error


def same_git_repository(source: Path, root: Path) -> bool:
    try:
        left = run(["git", "-C", str(source), "rev-parse", "--path-format=absolute", "--git-common-dir"]).strip()
        right = run(["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-common-dir"]).strip()
    except CleanupError:
        return False
    return bool(left and right and Path(left).resolve() == Path(right).resolve())


def c5_candidate(item: dict, root: Path) -> tuple[bool, str]:
    mounts = item.get("Mounts", [])
    source_mounts = [Path(mount["Source"]).resolve() for mount in mounts
                     if mount.get("Source") and mount.get("Destination") == "/workspace"]
    project_mount = next((source for source in source_mounts if same_git_repository(source, root)), None)
    config = item.get("Config", {})
    command = " ".join(str(part) for part in (config.get("Entrypoint") or []) + (config.get("Cmd") or []))
    exact_launcher = "docker/simulation-warehouse-grid/stage1_run.py" in command
    if not (project_mount and exact_launcher):
        return False, ""
    env = {}
    for entry in config.get("Env") or []:
        if "=" in entry:
            key, value = entry.split("=", 1)
            env[key] = value
    if not env.get("IGN_PARTITION") or not env.get("ROS_DOMAIN_ID"):
        raise CleanupError(f"C5 adayı {item.get('Name')} oturum/ROS domain kimliği eksik")
    if not env["ROS_DOMAIN_ID"].isdigit() or not 0 <= int(env["ROS_DOMAIN_ID"]) <= 232:
        raise CleanupError(f"C5 adayı {item.get('Name')} ROS_DOMAIN_ID geçersiz")
    if not any(mount.get("Destination") == "/evidence" for mount in mounts):
        raise CleanupError(f"C5 adayı {item.get('Name')} kanıt volume bağlaması eksik")
    env["_WORKSPACE_MOUNT"] = str(project_mount)
    return True, env


def host_ports(item: dict) -> list[int]:
    ports = set()
    for bindings in (item.get("NetworkSettings", {}).get("Ports") or {}).values():
        for binding in bindings or []:
            if binding.get("HostPort", "").isdigit():
                ports.add(int(binding["HostPort"]))
    return sorted(ports)


def critical_processes(process_table: str) -> list[dict]:
    roles = {
        "supervisor": "stage1_run.py", "gazebo": "ign gazebo", "bridge": "parameter_bridge",
        "nav2_launch": "nav2_bringup", "amcl": "/nav2_amcl/amcl",
        "executor": "executor_test_entry.py", "manager": "backend.dashboard.runtime",
        "api": "backend.dashboard.api",
    }
    result = []
    for line in process_table.splitlines():
        parts = line.strip().split(maxsplit=7)
        if len(parts) < 8 or not parts[0].isdigit():
            continue
        pid, ppid = int(parts[0]), int(parts[1])
        started = " ".join(parts[2:7])
        command = parts[7]
        lowered = command.lower()
        for role, marker in roles.items():
            if marker.lower() in lowered:
                result.append({"role": role, "pid": pid, "ppid": ppid,
                               "started": started, "command": command})
                break
    observed = {item["role"] for item in result}
    required = {"supervisor", "gazebo", "bridge", "nav2_launch", "amcl", "executor", "manager", "api"}
    if not required.issubset(observed):
        raise CleanupError(f"kritik C5 süreçleri eksik: {sorted(required - observed)}")
    return result


def gui_processes(port: int, root: Path) -> list[dict]:
    pids = run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"], check=False)
    processes = []
    for raw_pid in pids.splitlines():
        if not raw_pid.strip().isdigit():
            continue
        pid = int(raw_pid)
        ps_row = run(["ps", "-p", str(pid), "-o", "lstart=", "-o", "command="], check=False).strip()
        cwd_result = run(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"], check=False)
        cwd = next((line[1:] for line in cwd_result.splitlines() if line.startswith("n")), "")
        if not ps_row or not cwd:
            raise CleanupError(f"GUI listener port {port} sahibi çözümlenemedi (PID {pid})")
        try:
            cwd_path = Path(cwd).resolve()
            command = ps_row.split(maxsplit=5)[-1]
        except (OSError, IndexError) as error:
            raise CleanupError(f"GUI listener metadata çözümlenemedi (PID {pid})") from error
        in_frontend = cwd_path.name == "frontend" and same_git_repository(cwd_path, root)
        is_vite = "vite" in command.lower() or "npm run dev" in command.lower()
        port_in_command = re.search(rf"(?:--port(?:=|\s+)|:{port}\b){port}(?:\s|$)", command)
        if not (in_frontend and is_vite and (port_in_command or f"{port}" in command)):
            raise CleanupError(f"GUI port {port} başka/belirsiz süreçte dinleniyor; PID {pid} korunuyor")
        processes.append({"pid": pid, "started": ps_row[:24], "command": command, "cwd": str(cwd_path)})
    return processes


def stop_gui_processes(port: int, root: Path) -> list[dict]:
    processes = gui_processes(port, root)
    identified = list(processes)
    for process in identified:
        os.kill(process["pid"], signal.SIGTERM)
    deadline = time.monotonic() + 10
    while processes and time.monotonic() < deadline:
        alive = []
        for process in processes:
            try:
                os.kill(process["pid"], 0)
            except ProcessLookupError:
                continue
            alive.append(process)
        processes = alive
        if processes:
            time.sleep(0.1)
    if processes:
        raise CleanupError(f"Vite GUI kontrollü SIGTERM ile kapanmadı: {[item['pid'] for item in processes]}")
    return identified


def api_get(port: int, path: str) -> dict:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=4) as response:
            result = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        raise CleanupError(f"C5 API {port}{path} okunamadı: {error}") from error
    if not isinstance(result, dict):
        raise CleanupError(f"C5 API {port}{path} nesne döndürmedi")
    return result


def disable_task_ingress(container_id: str, socket_path: str, api_port: int) -> None:
    code = (
        "import json,os,stat,sys; p=sys.argv[1]; "
        "s=os.lstat(p) if os.path.lexists(p) else None; "
        "(os.unlink(p) if s and stat.S_ISSOCK(s.st_mode) else None); "
        "print(json.dumps({'path':p,'removed':bool(s and stat.S_ISSOCK(s.st_mode)),'absent':s is None}))"
    )
    output = run(["docker", "exec", "-u", "0", container_id, "python3", "-c", code, socket_path])
    try:
        socket_state = json.loads(output)
    except json.JSONDecodeError as error:
        raise CleanupError(f"{container_id}: task socket durumu alınamadı") from error
    if not (socket_state.get("removed") or socket_state.get("absent")):
        raise CleanupError(f"{container_id}: task socket beklenen Unix socket değil; API açık bırakıldı")
    try:
        catalog = api_get(api_port, "/api/task-catalog")
    except CleanupError as error:
        # The catalog uses the live fleet snapshot. If that dependency is
        # unavailable, task submission is also unavailable; confirm the API
        # process itself is still reachable before accepting this as closed.
        if "HTTP Error 503" not in str(error):
            raise
        health = api_get(api_port, "/api/health")
        if health.get("source") != "LIVE":
            raise CleanupError(f"{container_id}: API health/catalog kapanış doğrulaması başarısız") from error
        return {"unix_socket_absent": True, "task_catalog_http_503": True,
                "api_source": health.get("source")}
    if catalog.get("enabled") is not False:
        raise CleanupError(f"{container_id}: görev kabul kapısı kapandığı doğrulanamadı")
    return {"unix_socket_absent": True, "task_catalog_enabled": False}


def robot_ids(snapshot: dict) -> list[str]:
    robots = snapshot.get("robots")
    if not isinstance(robots, list) or not robots:
        raise CleanupError("robot snapshot boş veya geçersiz")
    values = [robot.get("robot_id") for robot in robots]
    if any(not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_]+", value) for value in values):
        raise CleanupError("robot snapshot içinde güvenli olmayan/eksik robot ID var")
    return values


def free_port(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.25)
        return probe.connect_ex(("127.0.0.1", port)) != 0


def c5_containers(root: Path) -> list[dict]:
    listed = docker_json_lines("ps", "--no-trunc", "--format", "{{json .}}")
    if not isinstance(listed, list):
        raise CleanupError("Docker çalışan container listesi geçersiz")
    ids = [str(row["ID"]) for row in listed]
    if not ids:
        return []
    inspected = docker_json("inspect", *ids)
    by_id = {item.get("Id"): item for item in inspected}
    result = []
    for row in listed:
        item = by_id.get(row.get("ID"))
        if not item:
            raise CleanupError(f"Docker inspect kaydı eksik: {row.get('Names')}")
        candidate, env = c5_candidate(item, root)
        if not candidate:
            continue
        process_table = run(["docker", "top", row["ID"], "-eo", "pid,ppid,lstart,args"])
        process_ids = critical_processes(process_table)
        socket_match = re.search(r"--task-socket\s+(\S+)", process_table)
        port_match = re.search(r"--api-port\s+(\d+)", process_table)
        ui_match = re.search(r"--origin\s+http://127\.0\.0\.1:(\d+)", process_table)
        if not socket_match or not port_match or not ui_match:
            raise CleanupError(f"C5 oturum API/task-ingress kimliği eksik: {row.get('Names')}")
        ports = host_ports(item)
        api_port = int(port_match.group(1))
        if api_port not in ports:
            raise CleanupError(f"C5 API portu published port ile eşleşmiyor: {row.get('Names')}")
        result.append({
            "id": row["ID"], "name": str(row.get("Names", "")).lstrip("/"),
            "created": item.get("Created"), "started_at": item.get("State", {}).get("StartedAt"),
            "container_pid": item.get("State", {}).get("Pid"),
            "compose_project": (item.get("Config", {}).get("Labels") or {}).get("com.docker.compose.project"),
            "compose_service": (item.get("Config", {}).get("Labels") or {}).get("com.docker.compose.service"),
            "workspace": env["_WORKSPACE_MOUNT"], "session_id": env["IGN_PARTITION"],
            "ros_domain_id": int(env["ROS_DOMAIN_ID"]), "api_port": api_port,
            "ports": ports, "ui_port": int(ui_match.group(1)),
            "task_socket": socket_match.group(1), "processes": process_ids,
            "process_table": process_table,
        })
    return result


def stopped_c5_gui_sessions(root: Path) -> list[dict]:
    """Find stale Vite ports left by a stopped C5 container from this Git repo."""
    listed = docker_json_lines("ps", "-a", "--no-trunc", "--format", "{{json .}}")
    ids = [str(row["ID"]) for row in listed]
    if not ids:
        return []
    inspected = docker_json("inspect", *ids)
    by_id = {item.get("Id"): item for item in inspected}
    result = []
    for row in listed:
        item = by_id.get(row.get("ID"))
        if not item:
            raise CleanupError(f"Docker inspect kaydı eksik: {row.get('Names')}")
        if item.get("State", {}).get("Running"):
            continue
        owned, _env = c5_candidate(item, root)
        if not owned:
            continue
        command = " ".join(str(part) for part in (item.get("Config", {}).get("Entrypoint") or []) +
                            (item.get("Config", {}).get("Cmd") or []))
        ui_match = re.search(r"--origin\s+http://127\.0\.0\.1:(\d+)", command)
        if not ui_match:
            raise CleanupError(f"Durdurulmuş C5 container GUI portu çözümlenemedi: {row.get('Names')}")
        result.append({"id": row["ID"], "name": str(row.get("Names", "")).lstrip("/"),
                       "ui_port": int(ui_match.group(1)),
                       "started_at": item.get("State", {}).get("StartedAt")})
    return result


def cleanup(root: Path, audit_dir: Path) -> dict:
    root = root.resolve()
    stale_guis = stopped_c5_gui_sessions(root)
    sessions = c5_containers(root)
    report = {"started_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "workspace": str(root), "stopped_session_guis": [], "sessions": [], "result": "PASS"}
    for stale in stale_guis:
        try:
            stopped = stop_gui_processes(stale["ui_port"], root)
            report["stopped_session_guis"].append({**stale, "processes_stopped": stopped})
        except CleanupError as error:
            report["result"] = "FAIL"
            raise CleanupError(f"Eski C5 GUI cleanup engellendi: {stale['name']}: {error}") from error
    for session in sessions:
        record = {key: value for key, value in session.items() if key != "process_table"}
        record["preserved_state"] = {"sqlite": "untouched", "logs": "untouched", "volumes": "untouched"}
        try:
            record["task_ingress"] = disable_task_ingress(
                session["id"], session["task_socket"], session["api_port"])
            robots = api_get(session["api_port"], "/api/robots")
            tasks = api_get(session["api_port"], "/api/tasks")
            record["robots_snapshot"] = robots
            record["tasks_snapshot"] = tasks
            ids = robot_ids(robots)
            probe_source = (root / "docker/simulation-warehouse-grid/c5_safe_stop_probe.py").read_text()
            command = (
                "source /opt/ros/humble/setup.bash && python3 - "
                f"--robot-ids {','.join(ids)} --duration 2 --timeout 20"
            )
            probe_output = run(["docker", "exec", "-i", session["id"], "bash", "-lc", command],
                               timeout=30, input_text=probe_source)
            try:
                probe_result = json.loads(probe_output.strip().splitlines()[-1])
            except (IndexError, json.JSONDecodeError) as error:
                raise CleanupError(f"güvenli duruş probe sonucu çözümlenemedi: {probe_output[-500:]}") from error
            record["safe_stop"] = probe_result
            if probe_result.get("result") != "SAFE_STOP_CONFIRMED":
                raise CleanupError(f"hareketin durduğu doğrulanamadı: {probe_result}")
            current_table = run(["docker", "top", session["id"], "-eo", "pid,ppid,lstart,args"])
            current_processes = critical_processes(current_table)
            before = {(p["role"], p["pid"], p["started"]) for p in session["processes"]}
            after = {(p["role"], p["pid"], p["started"]) for p in current_processes}
            if before != after:
                raise CleanupError(f"C5 kritik PID/start-time kimliği değişti: {session['name']}")
            record["process_identities_reconfirmed"] = current_processes
            record["gui_processes_stopped"] = stop_gui_processes(session["ui_port"], root)
            stop_result = run(["docker", "stop", "--time", "35", session["id"]], timeout=45)
            record["docker_stop"] = {"command": "docker stop --time 35", "output": stop_result.strip()}
            state = docker_json("inspect", session["id"])[0].get("State", {})
            if state.get("Running"):
                raise CleanupError(f"container kapanmadı: {session['name']}")
            record["container_stopped"] = True
            record["container_exit_code"] = state.get("ExitCode")
            record["docker_stop_escalated_after_grace"] = state.get("ExitCode") == 137
            if state.get("ExitCode") == 137:
                record["forced_stop_precondition"] = "SAFE_STOP_CONFIRMED"
            busy = [port for port in session["ports"] + [session["ui_port"]] if not free_port(port)]
            if busy:
                raise CleanupError(f"kapanan container portları hâlâ kullanımda: {busy}")
            record["ports_free"] = True
            record["result"] = "CLOSED"
        except CleanupError as error:
            record["result"] = "BLOCKED"
            record["error"] = str(error)
            report["sessions"].append(record)
            report["result"] = "FAIL"
            raise CleanupError(json.dumps(report, ensure_ascii=False)) from error
        report["sessions"].append(record)
    remaining = c5_containers(root)
    if remaining:
        report["result"] = "FAIL"
        raise CleanupError(f"C5 container kaldı: {[item['name'] for item in remaining]}")
    report["completed_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / f"cleanup-{uuid.uuid4().hex}.json"
    audit_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    report["audit_path"] = str(audit_path)
    return report


def choose_domain() -> int:
    listed = docker_json_lines("ps", "--no-trunc", "--format", "{{json .}}")
    ids = [str(row["ID"]) for row in listed]
    used = set()
    if ids:
        for item in docker_json("inspect", *ids):
            for entry in item.get("Config", {}).get("Env") or []:
                if entry.startswith("ROS_DOMAIN_ID="):
                    try:
                        used.add(int(entry.split("=", 1)[1]))
                    except ValueError:
                        raise CleanupError(f"ROS_DOMAIN_ID çözümlenemedi: {item.get('Name')}")
    start = uuid.uuid4().int % 33
    pool = list(range(200, 233))
    for offset in range(len(pool)):
        candidate = pool[(start + offset) % len(pool)]
        if candidate not in used:
            return candidate
    raise CleanupError("200–232 aralığında boş ROS_DOMAIN_ID kalmadı")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, default=Path("/tmp/c5-session-cleanup"))
    parser.add_argument("--choose-domain", action="store_true")
    args = parser.parse_args()
    try:
        if args.choose_domain:
            print(choose_domain())
            return 0
        report = cleanup(args.workspace, args.audit_dir)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    except CleanupError as error:
        print(f"C5 cleanup başarısız; yeni simülasyon başlatılmadı: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
