"""Durable snapshots and transactional outbox; no live restart recovery."""
from contextlib import contextmanager
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
from uuid import uuid4


def encode(value):
    return json.dumps(value, sort_keys=True, allow_nan=False)


class ScenarioResetRequired(RuntimeError):
    """Existing scenario evidence must not be replayed into physical robots."""


class SQLiteStore:
    def __init__(self, path):
        self.connection = sqlite3.connect(path, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA synchronous = FULL")
        self.connection.executescript(Path(__file__).with_name("schema.sql").read_text())

    def close(self):
        self.connection.close()

    @contextmanager
    def transaction(self):
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.connection.execute("COMMIT")
        except BaseException:
            if self.connection.in_transaction:
                self.connection.execute("ROLLBACK")
            raise

    def require_empty(self):
        for table in ("tasks", "robots", "reservations", "outbox_events", "processed_events", "task_review_holds"):
            if self.connection.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone():
                raise ScenarioResetRequired(
                    "Scenario reset required; preserve this database and use a new database after reset"
                )

    def persist_core(self, core):
        for robot in core.tracker.list_robots():
            self.connection.execute(
                "INSERT INTO robots VALUES (?,?) ON CONFLICT(robot_id) DO UPDATE SET snapshot=excluded.snapshot",
                (robot.robot_id, encode(asdict(robot))),
            )
        tasks = {t.task_id: t for t in core.queue.iter_assignable_tasks()}
        for collection in (core._active_tasks, core._completed_tasks, core._failed_tasks):
            tasks.update(collection)
        tasks.update({t.task_id: t for t in core._pending_preemption_assignments.values()})
        for task in sorted(tasks.values(), key=lambda t: t.status in ("ASSIGNED", "EXECUTING")):
            self.connection.execute(
                "INSERT INTO tasks VALUES (?,?,?,?,?,?) ON CONFLICT(task_id) DO UPDATE SET "
                "status=excluded.status,robot_id=excluded.robot_id,assignment_epoch=excluded.assignment_epoch,"
                "goal_uuid=excluded.goal_uuid,snapshot=excluded.snapshot",
                (task.task_id, task.status, task.assigned_robot_id, task.assignment_epoch,
                 task.goal_uuid, encode(asdict(task))),
            )
        for station in core.reservations.list_stations():
            self.connection.execute(
                "INSERT INTO reservations VALUES (?,?,?,?,?) ON CONFLICT(station_id) DO UPDATE SET "
                "state=excluded.state,reserved_by=excluded.reserved_by,occupied_by=excluded.occupied_by,snapshot=excluded.snapshot",
                (station.station_id, station.state, station.reserved_by_robot_id,
                 station.occupied_by_robot_id, encode(asdict(station))),
            )
        for hold in core.list_review_holds():
            self.connection.execute(
                "INSERT INTO task_review_holds VALUES (?,?,?,?,?,?) ON CONFLICT(task_id) DO UPDATE SET "
                "robot_id=excluded.robot_id,assignment_epoch=excluded.assignment_epoch,goal_uuid=excluded.goal_uuid,"
                "reason=excluded.reason,held_at=excluded.held_at",
                (hold["task_id"], hold["robot_id"], hold["assignment_epoch"], hold["goal_uuid"],
                 hold["reason"], hold["held_at"]),
            )

    def add_command(self, kind, task):
        command_id = f"{kind}:{task.goal_uuid}"
        if kind == "CANCEL_TASK":
            command_id += f":{uuid4()}"
        self.connection.execute(
            "INSERT OR IGNORE INTO outbox_events "
            "(command_id,kind,task_id,assignment_epoch,goal_uuid,payload) VALUES (?,?,?,?,?,?)",
            (command_id, kind, task.task_id, task.assignment_epoch, task.goal_uuid, encode(asdict(task))),
        )

    def claim(self, now):
        # A retry blocks later commands to preserve dispatch order.
        row = self.connection.execute(
            "SELECT * FROM outbox_events WHERE state IN ('PENDING','SENDING','RETRY') ORDER BY sequence LIMIT 1"
        ).fetchone()
        if row is None or row["state"] == "SENDING" or row["next_attempt_at"] > now:
            return None
        self.connection.execute(
            "UPDATE outbox_events SET state='SENDING', attempts=attempts+1 WHERE sequence=?", (row["sequence"],)
        )
        return dict(self.connection.execute(
            "SELECT * FROM outbox_events WHERE sequence=?", (row["sequence"],)
        ).fetchone())

    def finish(self, command_id, attempt, error, retry_at, held_for_review=False):
        state = "HELD_FOR_REVIEW" if held_for_review else ("SENT" if error is None else "RETRY")
        cursor = self.connection.execute(
            "UPDATE outbox_events SET state=?,last_error=?,next_attempt_at=? "
            "WHERE command_id=? AND attempts=? AND state='SENDING'",
            (state, error, retry_at, command_id, attempt),
        )
        return cursor.rowcount == 1

    def put_review_hold(self, task_id, robot_id, assignment_epoch, goal_uuid, reason, held_at):
        self.connection.execute(
            "INSERT INTO task_review_holds VALUES (?,?,?,?,?,?) ON CONFLICT(task_id) DO UPDATE SET "
            "robot_id=excluded.robot_id,assignment_epoch=excluded.assignment_epoch,goal_uuid=excluded.goal_uuid,"
            "reason=excluded.reason,held_at=excluded.held_at",
            (task_id, robot_id, assignment_epoch, goal_uuid, reason, held_at),
        )

    def clear_review_hold(self, task_id):
        return self.connection.execute("DELETE FROM task_review_holds WHERE task_id=?", (task_id,)).rowcount > 0
