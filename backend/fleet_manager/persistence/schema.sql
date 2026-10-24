PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS robots (
    robot_id TEXT PRIMARY KEY,
    snapshot TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    robot_id TEXT REFERENCES robots(robot_id),
    assignment_epoch INTEGER,
    goal_uuid TEXT,
    snapshot TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_task_per_robot ON tasks(robot_id)
    WHERE status IN ('ASSIGNED', 'EXECUTING');
CREATE TABLE IF NOT EXISTS reservations (
    station_id TEXT PRIMARY KEY,
    state TEXT NOT NULL CHECK(state IN ('FREE','RESERVED','OCCUPIED','RELEASING','BLOCKED')),
    reserved_by TEXT REFERENCES robots(robot_id),
    occupied_by TEXT REFERENCES robots(robot_id),
    snapshot TEXT NOT NULL,
    CHECK(reserved_by IS NULL OR occupied_by IS NULL OR reserved_by = occupied_by),
    CHECK(state != 'FREE' OR (reserved_by IS NULL AND occupied_by IS NULL))
);
CREATE TABLE IF NOT EXISTS processed_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    outcome TEXT NOT NULL,
    stream TEXT,
    status_seq INTEGER,
    task_id TEXT,
    assignment_epoch INTEGER,
    goal_uuid TEXT
);
CREATE INDEX IF NOT EXISTS event_stream_sequence ON processed_events(stream, status_seq);
CREATE TABLE IF NOT EXISTS outbox_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    command_id TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    task_id TEXT NOT NULL,
    assignment_epoch INTEGER NOT NULL,
    goal_uuid TEXT NOT NULL,
    payload TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'PENDING'
        CHECK(state IN ('PENDING','SENDING','RETRY','SENT','SUPERSEDED')),
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at REAL NOT NULL DEFAULT 0,
    last_error TEXT
);
