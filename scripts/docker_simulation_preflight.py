#!/usr/bin/env python3
"""Report Docker resources and gate C5 demo startup on other simulations."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from typing import Any


class PreflightError(RuntimeError):
    pass


def docker(*args: str) -> str:
    try:
        result = subprocess.run(
            ["docker", *args], check=True, text=True, capture_output=True
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise PreflightError(f"docker {' '.join(args)} başarısız: {detail.strip()}") from exc
    return result.stdout


def json_lines(output: str) -> list[dict[str, Any]]:
    rows = []
    for line in output.splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def parse_bytes(value: str) -> int:
    match = re.fullmatch(r"\s*([\d.]+)\s*([KMGTPE]?i?B)?\s*", value, re.I)
    if not match:
        raise ValueError(f"ölçü birimi çözümlenemedi: {value!r}")
    number = float(match.group(1))
    unit = (match.group(2) or "B").upper()
    powers = {"B": 0, "KB": 1, "KIB": 1, "MB": 2, "MIB": 2,
              "GB": 3, "GIB": 3, "TB": 4, "TIB": 4, "PB": 5,
              "PIB": 5, "EB": 6, "EIB": 6}
    return int(number * (1024 ** powers[unit]))


def parse_stats(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    stats: dict[str, dict[str, float | int]] = {}
    for row in rows:
        name = str(row["Name"]).lstrip("/")
        cpu = float(str(row["CPUPerc"]).rstrip("%"))
        used, _limit = str(row["MemUsage"]).split("/", 1)
        stats[name] = {"cpu_pct": cpu, "memory_bytes": parse_bytes(used)}
    return stats


def command_markers(output: str) -> set[str]:
    text = output.lower()
    markers: set[str] = set()
    if any(token in text for token in ("ign gazebo", "gz sim", "gzserver", "ignition-gazebo", "gz-sim")):
        markers.add("Gazebo")
    if any(token in text for token in ("nav2", "amcl", "planner_server", "controller_server", "bt_navigator", "behavior_server")):
        markers.add("Nav2")
    if any(token in text for token in ("/opt/ros/", "ros2", "rclcpp", "component_container")):
        markers.add("ROS 2")
    if any(token in text for token in ("fleet_manager", "fleet-manager", "backend.dashboard", "fleet manager")):
        markers.add("Fleet Manager")
    return markers


def docker_snapshot() -> tuple[list[dict[str, Any]], dict[str, dict[str, float | int]], dict[str, Any]]:
    listed = json_lines(docker("ps", "--no-trunc", "--format", "{{json .}}"))
    ids = [str(row["ID"]) for row in listed]
    inspected: dict[str, dict[str, Any]] = {}
    if ids:
        values = json.loads(docker("inspect", *ids))
        inspected = {str(item["Id"]): item for item in values}
    stat_rows = json_lines(docker("stats", "--no-stream", "--format", "{{json .}}"))
    stats = parse_stats(stat_rows)

    for row in listed:
        container_id = str(row["ID"])
        inspect = inspected.get(container_id)
        if inspect is None:
            raise PreflightError(f"Container inspect sonucu eksik: {row.get('Names', container_id)}")
        labels = inspect.get("Config", {}).get("Labels") or {}
        row["labels"] = labels
        row["project"] = labels.get("com.docker.compose.project", "")
        row["service"] = labels.get("com.docker.compose.service", "")
        row["top"] = docker("top", container_id, "-eo", "pid,comm,args")
        row["markers"] = command_markers(row["top"])
        row["state"] = inspect.get("State", {}).get("Status", row.get("State", "unknown"))
        row["name"] = str(row.get("Names", container_id)).lstrip("/")
        row["cpu_pct"] = stats[row["name"]]["cpu_pct"]
        row["memory_bytes"] = stats[row["name"]]["memory_bytes"]
    vm = json.loads(docker("info", "--format", "{{json .}}"))
    return listed, stats, vm


def simulation_projects(containers: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Treat process evidence as primary; Compose labels group companion services."""
    primary_by_project: dict[str, list[dict[str, Any]]] = {}
    unlabeled: list[dict[str, Any]] = []
    for container in containers:
        markers = container["markers"]
        primary = bool(markers.intersection({"Gazebo", "Nav2"}))
        labels = container["labels"]
        config_files = labels.get("com.docker.compose.project.config_files", "").lower()
        service = str(container["service"]).lower()
        ros_fleet_runtime = "ROS 2" in markers and (
            "Fleet Manager" in markers or "simulation" in service or "simulation" in config_files
        )
        if not primary and not ros_fleet_runtime:
            continue
        project = str(container["project"])
        if project:
            primary_by_project.setdefault(project, []).append(container)
        else:
            unlabeled.append(container)

    groups: dict[str, list[dict[str, Any]]] = {}
    for project, candidates in primary_by_project.items():
        # Reused Compose project names can still contain multiple independent demo
        # containers. Do not collapse them into one session; attach companions only
        # when there is exactly one process-identified simulation in that project.
        if len(candidates) == 1:
            candidate = candidates[0]
            companions = [
                row for row in containers
                if row["project"] == project and row is not candidate
                and row["markers"].intersection({"ROS 2", "Fleet Manager"})
            ]
            groups[project] = [candidate, *companions]
        else:
            for candidate in candidates:
                groups[f"{project} / {candidate['name']}"] = [candidate]
    for container in unlabeled:
        groups[f"etiketsiz / {container['name']}"] = [container]
    return groups


def fmt_memory(byte_count: int) -> str:
    return f"{byte_count / (1024 ** 2):.1f} MiB"


def report_and_gate(
    containers: list[dict[str, Any]],
    vm: dict[str, Any],
    target_project: str,
    allow_concurrent: bool,
) -> int:
    try:
        cpu_capacity = int(vm["NCPU"])
        memory_capacity = int(vm["MemTotal"])
        if cpu_capacity <= 0 or memory_capacity <= 0:
            raise ValueError("Docker VM kapasitesi sıfır veya negatif")
        cpu_load = sum(float(row["cpu_pct"]) for row in containers)
        memory_load = sum(int(row["memory_bytes"]) for row in containers)
    except (KeyError, TypeError, ValueError) as exc:
        print(f"UYARI: Docker VM kapasite/yük ölçümü eksik: {exc}", file=sys.stderr)
        print("Preflight temiz kabul edilmedi; simülasyon başlatılmadı.", file=sys.stderr)
        return 2

    print("=== Docker preflight: çalışan container'lar ===")
    if not containers:
        print("Çalışan container yok.")
    for row in containers:
        markers = ", ".join(sorted(row["markers"])) or "özel simülasyon süreci saptanmadı"
        compose = f"project={row['project'] or '—'} service={row['service'] or '—'}"
        print(
            f"{row['name']} | {row['state']} | CPU {float(row['cpu_pct']):.1f}% | "
            f"RAM {fmt_memory(int(row['memory_bytes']))} | {compose} | süreç: {markers}"
        )
    print(
        f"Docker VM: {cpu_capacity} CPU | {fmt_memory(memory_capacity)} RAM kapasitesi; "
        f"çalışan container ölçümleri toplamı CPU {cpu_load:.1f}% / {cpu_capacity} CPU, "
        f"RAM {fmt_memory(memory_load)} / {fmt_memory(memory_capacity)}."
    )
    print("Yük toplamı container ölçümleridir; Docker VM içindeki container dışı süreçleri kapsamaz.")
    if cpu_load >= cpu_capacity * 100:
        print("UYARI: Container CPU toplamı bildirilen Docker VM kapasitesine ulaştı veya aştı.")
    if memory_load >= memory_capacity:
        print("UYARI: Container bellek toplamı bildirilen Docker VM kapasitesine ulaştı veya aştı.")

    projects = simulation_projects(containers)
    other = {
        name: rows for name, rows in projects.items()
        if all(str(row["project"]) != target_project for row in rows)
    }
    own = [
        row for rows in projects.values() for row in rows
        if str(row["project"]) == target_project
    ]
    if own:
        print(f"Hedef Compose projesinde zaten aktif simülasyon var: {target_project} (yeniden kullanım).")
    if not other:
        print("Başka aktif Gazebo/Nav2 simülasyonu saptanmadı.")
        return 0

    print("Başka aktif simülasyon(lar) bulundu:")
    other_names: list[str] = []
    for project, rows in other.items():
        names = [str(row["name"]) for row in rows]
        other_names.extend(names)
        cpu = sum(float(row["cpu_pct"]) for row in rows)
        memory = sum(int(row["memory_bytes"]) for row in rows)
        evidence = sorted({marker for row in rows for marker in row["markers"]})
        print(
            f"- Compose projesi {project}: {', '.join(names)}; "
            f"CPU toplamı {cpu:.1f}%, bellek toplamı {fmt_memory(memory)}; "
            f"kanıt: {', '.join(evidence) or 'Compose etiketi ve süreçler'}."
        )
    print("Kapatmayı değerlendirilebilecek container'lar: " + ", ".join(other_names))
    if allow_concurrent:
        print("OVERRIDE: --allow-concurrent-simulation kullanıldı; ikinci simülasyon başlatılmasına izin veriliyor.")
        return 0
    print("Başlangıç engellendi. Çakışan oturumları kendiniz inceleyin; preflight container durdurmaz.")
    print("Bilinçli olarak birlikte çalıştırmak için --allow-concurrent-simulation seçeneğini verin.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-name", required=True, help="Bu Compose çalıştırmasının proje adı")
    parser.add_argument("--allow-concurrent-simulation", action="store_true")
    args = parser.parse_args()
    try:
        containers, _stats, vm = docker_snapshot()
    except (PreflightError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"Docker preflight ölçümü başarısız: {exc}", file=sys.stderr)
        print("Sistem temiz kabul edilmedi; simülasyon başlatılmadı.", file=sys.stderr)
        return 2
    return report_and_gate(containers, vm, args.project_name, args.allow_concurrent_simulation)


if __name__ == "__main__":
    raise SystemExit(main())
