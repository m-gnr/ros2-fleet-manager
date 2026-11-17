"""Track first verified readiness observations for each robot."""


PHASES = ("amcl", "nav2", "tf")


class StartupReadiness:
    def __init__(self, robot_ids, started_monotonic_ns):
        ids = tuple(robot_ids)
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("robot_ids must be a non-empty unique sequence")
        self.started_monotonic_ns = started_monotonic_ns
        self.robot_ids = ids
        self.ready_at = {robot_id: {} for robot_id in ids}
        self.completed_at = None

    def mark(self, robot_id, phase, *, monotonic_ns, observed_at_utc):
        if robot_id not in self.ready_at:
            raise ValueError(f"unknown robot id: {robot_id}")
        if phase not in PHASES:
            raise ValueError(f"unknown readiness phase: {phase}")
        if phase in self.ready_at[robot_id]:
            return None
        if monotonic_ns < self.started_monotonic_ns:
            raise ValueError("readiness observation predates startup")
        result = {
            "ready": True,
            "elapsed_ms": round((monotonic_ns - self.started_monotonic_ns) / 1_000_000, 3),
            "observed_at_utc": observed_at_utc,
        }
        self.ready_at[robot_id][phase] = result
        return result

    @property
    def ready(self):
        return all(all(phase in self.ready_at[robot_id] for phase in PHASES)
                   for robot_id in self.robot_ids)

    def snapshot(self, *, started_at_utc, current_ready=None,
                 observed_monotonic_ns=None, observed_at_utc=None):
        is_currently_ready = self.ready and (current_ready is None or current_ready)
        if (is_currently_ready and self.completed_at is None
                and observed_monotonic_ns is not None and observed_at_utc is not None):
            self.completed_at = {
                "elapsed_ms": round((observed_monotonic_ns - self.started_monotonic_ns) / 1_000_000, 3),
                "observed_at_utc": observed_at_utc,
            }
        robots = {
            robot_id: {
                phase: self.ready_at[robot_id].get(phase, {"ready": False})
                for phase in PHASES
            }
            for robot_id in self.robot_ids
        }
        elapsed_ms = self.completed_at["elapsed_ms"] if self.completed_at else None
        return {
            "schema_version": 1,
            "status": "READY" if self.completed_at else "WAITING",
            "current_status": "READY" if is_currently_ready else "WAITING",
            "started_at_utc": started_at_utc,
            "elapsed_ms": elapsed_ms,
            "ready_at_utc": self.completed_at["observed_at_utc"] if self.completed_at else None,
            "required_phases": list(PHASES),
            "robots": robots,
        }
