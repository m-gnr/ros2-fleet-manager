#!/usr/bin/env python3
"""Host runner and 0.5-second interval resource monitor for Stage B3 retry.
Monitors both simulation and backend containers using docker stats from container
start to teardown, reporting entire run and navigation window metrics separately.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parent.parent


def parse_mem_to_mb(mem_str):
    """Parse docker stats memory string like '123.4MiB / 7.748GiB' to MB float."""
    try:
        used_part = mem_str.split('/')[0].strip()
        match = re.match(r'^([0-9.]+)\s*([a-zA-Z]+)$', used_part)
        if not match:
            return None
        val = float(match.group(1))
        unit = match.group(2).lower()
        if unit in ('gib', 'gb'):
            return val * 1024.0
        elif unit in ('mib', 'mb'):
            return val
        elif unit in ('kib', 'kb'):
            return val / 1024.0
        elif unit in ('b', 'bytes'):
            return val / (1024.0 * 1024.0)
        return val
    except Exception:
        return None


def parse_cpu_pct(cpu_str):
    """Parse docker stats CPU percentage like '45.67%' to float."""
    try:
        cleaned = cpu_str.replace('%', '').strip()
        return float(cleaned)
    except Exception:
        return None


class HostDockerStatsMonitor:
    def __init__(self, docker_bin, target_substrings, interval=0.5):
        self.docker_bin = docker_bin
        self.target_substrings = target_substrings
        self.interval = interval
        self.samples = []
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)

    def _run(self):
        cmd = [
            self.docker_bin, 'stats', '--no-stream',
            '--format', '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'
        ]

        while not self._stop_event.is_set():
            t_sample = time.time()
            try:
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=2.0)
                if res.returncode == 0:
                    for line in res.stdout.strip().splitlines():
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            name = parts[0].strip()
                            # Check if matches target containers
                            matched_target = None
                            for tgt in self.target_substrings:
                                if tgt in name:
                                    matched_target = tgt
                                    break
                            if matched_target:
                                cpu = parse_cpu_pct(parts[1])
                                mem = parse_mem_to_mb(parts[2])
                                if cpu is not None and mem is not None:
                                    self.samples.append({
                                        'time': t_sample,
                                        'target': matched_target,
                                        'container': name,
                                        'cpu_pct': cpu,
                                        'mem_mb': mem,
                                    })
            except Exception:
                pass
            time.sleep(self.interval)

    def compute_stats(self, window_start=None, window_end=None):
        out = {}
        for tgt in self.target_substrings:
            c_samples = [
                s for s in self.samples
                if s['target'] == tgt and
                (window_start is None or s['time'] >= window_start) and
                (window_end is None or s['time'] <= window_end)
            ]
            if not c_samples:
                out[tgt] = {
                    'sample_count': 0,
                    'avg_cpu_pct': None,
                    'peak_cpu_pct': None,
                    'peak_mem_mb': None,
                }
            else:
                cpus = [s['cpu_pct'] for s in c_samples]
                mems = [s['mem_mb'] for s in c_samples]
                out[tgt] = {
                    'sample_count': len(c_samples),
                    'avg_cpu_pct': round(sum(cpus) / len(cpus), 2),
                    'peak_cpu_pct': round(max(cpus), 2),
                    'peak_mem_mb': round(max(mems), 2),
                }
        return out


def main():
    parser = argparse.ArgumentParser(description='Run B3 retry with host-level docker stats resource monitoring.')
    parser.add_argument('--token', required=True, help='Payload run token')
    parser.add_argument('--domain', default='45', help='ROS_DOMAIN_ID')
    args = parser.parse_args()

    docker_bin = shutil.which('docker') or '/usr/local/bin/docker'
    if not os.path.exists(docker_bin):
        print(f'Error: docker binary not found at {docker_bin}', file=sys.stderr)
        return 1

    sim_target = 'simulation-b3-retry-simulation'
    backend_target = 'simulation-b3-retry-backend'

    monitor = HostDockerStatsMonitor(docker_bin, [sim_target, backend_target], interval=0.5)
    monitor.start()

    compose_cmd = [
        docker_bin, 'compose',
        '-f', 'docker-compose.dds.yml',
        '-f', 'docker-compose.simulation-check.yml',
        '-f', 'docker-compose.simulation-b3-retry.yml',
        'up', '--abort-on-container-exit', '--exit-code-from', 'backend'
    ]

    env = os.environ.copy()
    env['DDS_TEST_PAYLOAD'] = args.token
    env['ROS_DOMAIN_ID'] = str(args.domain)
    env['ROS_LOCALHOST_ONLY'] = '0'
    env['PATH'] = env.get('PATH', '') + ':/usr/local/bin:/opt/homebrew/bin'

    print(f'=== LAUNCHING B3 RETRY RUN: {args.token} (Domain: {args.domain}) ===', flush=True)
    t_run_start = time.time()
    t_nav_start = None
    t_nav_end = None

    proc = subprocess.Popen(
        compose_cmd,
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    for line in iter(proc.stdout.readline, ''):
        print(line, end='', flush=True)
        if 'NAVIGATION_WINDOW_START' in line:
            t_nav_start = time.time()
        elif 'NAVIGATION_WINDOW_END' in line:
            t_nav_end = time.time()

    proc.wait()
    t_run_end = time.time()

    time.sleep(1.0)
    monitor.stop()

    entire_stats = monitor.compute_stats(window_start=t_run_start, window_end=t_run_end)
    nav_stats = monitor.compute_stats(window_start=t_nav_start, window_end=t_nav_end)

    report = {
        'run_token': args.token,
        'domain_id': int(args.domain),
        'exit_code': proc.returncode,
        'run_duration_s': round(t_run_end - t_run_start, 2),
        'nav_duration_s': round(t_nav_end - t_nav_start, 2) if (t_nav_start and t_nav_end) else None,
        'entire_run_stats': entire_stats,
        'navigation_window_stats': nav_stats,
    }

    print('\n' + '=' * 60, flush=True)
    print('=== HOST DOCKER STATS RESOURCE MEASUREMENT REPORT ===', flush=True)
    print(json.dumps(report, indent=2), flush=True)
    print('=' * 60, flush=True)

    return proc.returncode


if __name__ == '__main__':
    sys.exit(main())
