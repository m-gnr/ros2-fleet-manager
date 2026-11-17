#!/usr/bin/env python3
"""Serialize launchers across a C5 repository, clean old sessions, then exec."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import uuid


def git_common_dir(root: Path) -> Path:
    try:
        value = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            text=True, stderr=subprocess.PIPE,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError(f"Git ortak deposu belirlenemedi: {root}: {error}") from error
    if not value:
        raise RuntimeError(f"Git ortak deposu boş döndü: {root}")
    return Path(value).resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--allow-concurrent-simulation", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("Compose komutu gerekli")
    root = args.workspace.resolve()
    try:
        repository = git_common_dir(root)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 2
    lock_key = hashlib.sha256(str(repository).encode()).hexdigest()[:20]
    lock_path = Path(os.environ.get("TMPDIR", "/tmp")) / f"c5-launch-{lock_key}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Bu C5 deposu için başka bir launcher çalışıyor; başlangıç engellendi.", file=sys.stderr)
            return 2

        if not args.allow_concurrent_simulation:
            cleanup = [sys.executable, str(root / "scripts/c5_session_cleanup.py"),
                       "--workspace", str(root)]
            result = subprocess.run(cleanup)
            if result.returncode:
                return result.returncode
        else:
            print("OVERRIDE: --allow-concurrent-simulation; eski C5 oturumları korunuyor.")

        domain_result = subprocess.run(
            [sys.executable, str(root / "scripts/c5_session_cleanup.py"),
             "--workspace", str(root), "--choose-domain"],
            text=True, capture_output=True)
        if domain_result.returncode:
            print(domain_result.stderr, file=sys.stderr)
            return domain_result.returncode
        domain = domain_result.stdout.strip()
        if not domain.isdigit():
            print("Boş ROS_DOMAIN_ID seçilemedi; başlangıç engellendi.", file=sys.stderr)
            return 2
        session_id = f"c5-{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:10]}"
        env = os.environ.copy()
        env["C5_SESSION_ID"] = session_id
        env["ROS_DOMAIN_ID"] = domain
        env["IGN_PARTITION"] = session_id
        print(f"Yeni C5 oturumu: {session_id} | ROS_DOMAIN_ID={domain}", flush=True)
        return subprocess.run(command, cwd=root, env=env).returncode


if __name__ == "__main__":
    raise SystemExit(main())
