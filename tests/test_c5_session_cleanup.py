import json
import fcntl
import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import c5_launch_guard
import c5_session_cleanup as cleanup


def session(name="old-c5", container_id="c5-id", port=21482):
    processes = [{"role": role, "pid": index + 100, "ppid": 1,
                  "started": "Tue Nov 17 00:00:02 2026", "command": role}
                 for index, role in enumerate(("supervisor", "gazebo", "bridge", "nav2_launch",
                                               "amcl", "executor", "manager", "api"))]
    return {
        "id": container_id, "name": name, "created": "2026-11-17T00:00:00Z",
        "started_at": "2026-11-17T00:00:01Z", "compose_project": "generic-project",
        "compose_service": "backend", "workspace": str(ROOT), "session_id": name,
        "ros_domain_id": 199, "api_port": port, "ports": [port], "ui_port": port + 1,
        "task_socket": "/tmp/stage1/latest.tasks.sock", "processes": processes,
    }


def snapshot(robot_ids=("robot_alpha", "robot_beta")):
    return {"robots": [{"robot_id": robot, "state": "IDLE", "active_task_id": None}
                       for robot in robot_ids]}


class C5SessionCleanupTests(unittest.TestCase):
    def run_cleanup(self, sessions):
        with tempfile.TemporaryDirectory() as temp:
            command_calls = []

            def fake_run(args, **kwargs):
                command_calls.append(args)
                if args[:2] == ["docker", "exec"] and "python3 -" in args[-1]:
                    return json.dumps({"result": "SAFE_STOP_CONFIRMED", "canceled_robots": [],
                                       "robots": {"robot_alpha": {"max_abs_velocity": 0.0}}})
                if args[:2] == ["docker", "top"]:
                    return "mock process table"
                if args[:4] == ["docker", "stop", "--time", "35"]:
                    return args[-1]
                raise AssertionError(f"unexpected command: {args}")

            with (patch.object(cleanup, "c5_containers", side_effect=[sessions, []]),
                  patch.object(cleanup, "stopped_c5_gui_sessions", return_value=[]),
                  patch.object(cleanup, "disable_task_ingress",
                               return_value={"unix_socket_absent": True, "task_catalog_enabled": False}) as ingress,
                  patch.object(cleanup, "api_get", side_effect=[snapshot(), {"tasks": []}] * len(sessions)),
                  patch.object(cleanup, "run", side_effect=fake_run),
                  patch.object(cleanup, "docker_json", return_value=[{"State": {"Running": False}}]),
                  patch.object(cleanup, "free_port", return_value=True),
                  patch.object(cleanup, "stop_gui_processes", return_value=[]),
                  patch.object(cleanup, "critical_processes", side_effect=[item["processes"] for item in sessions])):
                report = cleanup.cleanup(ROOT, Path(temp))
            return report, command_calls, ingress

    def test_one_old_session_is_safely_stopped(self):
        report, calls, ingress = self.run_cleanup([session()])
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["sessions"][0]["result"], "CLOSED")
        self.assertTrue(any(call[:4] == ["docker", "stop", "--time", "35"] for call in calls))
        ingress.assert_called_once()

    def test_multiple_old_sessions_are_cleaned(self):
        report, calls, _ = self.run_cleanup([session("a", "id-a"), session("b", "id-b", 21483)])
        self.assertEqual([item["result"] for item in report["sessions"]], ["CLOSED", "CLOSED"])
        self.assertEqual(sum(call[:2] == ["docker", "stop"] for call in calls), 2)

    def test_container_stop_confirms_nav2_and_executor_processes_are_gone(self):
        report, calls, _ = self.run_cleanup([session()])
        self.assertTrue(report["sessions"][0]["container_stopped"])
        self.assertTrue(any(call[:2] == ["docker", "stop"] for call in calls))

    def test_stopped_c5_container_orphan_gui_is_closed(self):
        stale = {"id": "stopped-id", "name": "old-c5", "ui_port": 21481,
                 "started_at": "2026-11-17T00:00:00Z"}
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(cleanup, "stopped_c5_gui_sessions", return_value=[stale]), \
             patch.object(cleanup, "c5_containers", side_effect=[[], []]), \
             patch.object(cleanup, "stop_gui_processes", return_value=[{"pid": 123}]) as stop_gui:
            report = cleanup.cleanup(ROOT, Path(temp))
        self.assertEqual(report["stopped_session_guis"][0]["processes_stopped"], [{"pid": 123}])
        stop_gui.assert_called_once_with(21481, ROOT.resolve())

    def test_other_project_candidate_is_not_owned_by_this_worktree(self):
        item = {"Mounts": [{"Source": "/tmp/another-ros-project", "Destination": "/workspace"}],
                "Config": {"Cmd": ["python3", "docker/simulation-warehouse-grid/stage1_run.py"]}}
        owned, _ = cleanup.c5_candidate(item, ROOT)
        self.assertFalse(owned)

    def test_same_c5_repo_other_worktree_is_owned(self):
        item = {
            "Name": "/demo-from-another-worktree",
            "Mounts": [
                {"Source": "/private/tmp/ros2-fleet-manager-c5-manual", "Destination": "/workspace"},
                {"Source": "/tmp/c5-session-evidence", "Destination": "/evidence"},
            ],
            "Config": {
                "Cmd": ["bash", "-ec", "exec python3 docker/simulation-warehouse-grid/stage1_run.py"],
                "Env": ["IGN_PARTITION=old-c5-session", "ROS_DOMAIN_ID=197"],
            },
        }
        with patch.object(cleanup, "run", return_value="/same/repository/.git"):
            owned, env = cleanup.c5_candidate(item, ROOT)
        self.assertTrue(owned)
        self.assertEqual(env["IGN_PARTITION"], "old-c5-session")

    def test_sqlite_logs_and_volumes_are_preserved(self):
        report, calls, _ = self.run_cleanup([session()])
        self.assertEqual(report["sessions"][0]["preserved_state"],
                         {"sqlite": "untouched", "logs": "untouched", "volumes": "untouched"})
        rendered = " ".join(" ".join(call) for call in calls).lower()
        for forbidden in ("prune", "volume rm", "rm -rf", "sqlite", ".log"):
            self.assertNotIn(forbidden, rendered)

    def test_unconfirmed_motion_blocks_container_stop(self):
        target = session()
        with tempfile.TemporaryDirectory() as temp:
            def fake_run(args, **kwargs):
                if "python3 -" in args[-1]:
                    return json.dumps({"result": "SAFE_STOP_UNCONFIRMED", "error": "odom changed"})
                raise AssertionError(f"container must remain running: {args}")
            with (patch.object(cleanup, "c5_containers", return_value=[target]),
                  patch.object(cleanup, "stopped_c5_gui_sessions", return_value=[]),
                  patch.object(cleanup, "disable_task_ingress",
                               return_value={"unix_socket_absent": True, "task_catalog_enabled": False}),
                  patch.object(cleanup, "api_get", side_effect=[snapshot(), {"tasks": []}]),
                  patch.object(cleanup, "run", side_effect=fake_run)):
                with self.assertRaises(cleanup.CleanupError):
                    cleanup.cleanup(ROOT, Path(temp))

    def test_changed_process_pid_or_start_time_blocks_container_stop(self):
        target = session()
        changed = [dict(item) for item in target["processes"]]
        changed[0] = {**changed[0], "pid": changed[0]["pid"] + 1000}
        with tempfile.TemporaryDirectory() as temp:
            def fake_run(args, **kwargs):
                if args[:2] == ["docker", "exec"]:
                    return json.dumps({"result": "SAFE_STOP_CONFIRMED", "canceled_robots": [], "robots": {}})
                if args[:2] == ["docker", "top"]:
                    return "process table"
                raise AssertionError(f"process identity mismatch must block stop: {args}")
            with (patch.object(cleanup, "c5_containers", return_value=[target]),
                  patch.object(cleanup, "stopped_c5_gui_sessions", return_value=[]),
                  patch.object(cleanup, "disable_task_ingress",
                               return_value={"unix_socket_absent": True, "task_catalog_enabled": False}),
                  patch.object(cleanup, "api_get", side_effect=[snapshot(), {"tasks": []}]),
                  patch.object(cleanup, "run", side_effect=fake_run),
                  patch.object(cleanup, "critical_processes", side_effect=[changed]),
                  patch.object(cleanup, "stop_gui_processes") as stop_gui):
                with self.assertRaises(cleanup.CleanupError):
                    cleanup.cleanup(ROOT, Path(temp))
            stop_gui.assert_not_called()

    def test_cleanup_failure_blocks_compose_start(self):
        repository = c5_launch_guard.git_common_dir(ROOT)
        with patch.object(sys, "argv", ["c5_launch_guard.py", "--workspace", str(ROOT), "--", "docker", "compose", "up"]), \
             patch.object(c5_launch_guard, "git_common_dir", return_value=repository), \
             patch.object(c5_launch_guard.subprocess, "run", return_value=type("R", (), {"returncode": 2, "stdout": "", "stderr": "blocked"})()) as run_mock:
            result = c5_launch_guard.main()
        self.assertEqual(result, 2)
        self.assertEqual(run_mock.call_count, 1)

    def test_clean_environment_starts_with_new_session_and_domain(self):
        repository = c5_launch_guard.git_common_dir(ROOT)
        with patch.object(sys, "argv", ["c5_launch_guard.py", "--workspace", str(ROOT), "--", "docker", "compose", "up"]), \
             patch.object(c5_launch_guard, "git_common_dir", return_value=repository), \
             patch.object(c5_launch_guard.subprocess, "run", side_effect=[
                 type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
                 type("R", (), {"returncode": 0, "stdout": "227\n", "stderr": ""})(),
                 type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
             ]) as run_mock:
            result = c5_launch_guard.main()
        self.assertEqual(result, 0)
        self.assertEqual(run_mock.call_count, 3)
        launched_env = run_mock.call_args.kwargs["env"]
        self.assertEqual(launched_env["ROS_DOMAIN_ID"], "227")
        self.assertEqual(launched_env["IGN_PARTITION"], launched_env["C5_SESSION_ID"])

    def test_concurrent_launcher_is_rejected_by_repository_lock_across_worktrees(self):
        with tempfile.TemporaryDirectory() as temp:
            repository = Path(temp) / "shared-git-common-dir"
            key = hashlib.sha256(str(repository).encode()).hexdigest()[:20]
            lock_path = Path(temp) / f"c5-launch-{key}.lock"
            with lock_path.open("a+") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                with patch.dict(os.environ, {"TMPDIR": temp}), \
                     patch.object(sys, "argv", ["c5_launch_guard.py", "--workspace", str(ROOT), "--", "docker", "compose", "up"]), \
                     patch.object(c5_launch_guard, "git_common_dir", return_value=repository), \
                     patch.object(c5_launch_guard.subprocess, "run") as run_mock:
                    result = c5_launch_guard.main()
                self.assertEqual(result, 2)
                run_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
