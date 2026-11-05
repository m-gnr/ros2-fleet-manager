"""Live HIGH delivery after real Nav2 preemption, with an empty route cache."""
import asyncio
import json
import math
import time

from rclpy.parameter import Parameter

from backend.fleet_manager.adapters.ros2_adapter_node import FleetROS2Adapter
from backend.fleet_manager.builder import build_fleet_manager_from_config
from backend.fleet_manager.domain.constants import RobotState, StationType, TaskPhase, TaskPriority, TaskResultStatus
from backend.fleet_manager.domain.models import Pose2D
from backend.fleet_manager.event_loop import Event, FleetEventLoop, OutboxDispatcher
from backend.fleet_manager.persistence.store import SQLiteStore

TEST = "T04-HIGH-E2E"


async def until(predicate, description, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        await asyncio.sleep(0.05)
    raise AssertionError(f"{TEST}: timed out waiting for {description}")


def standstill(node, odom):
    stamp = odom.header.stamp
    age = node.get_clock().now().nanoseconds / 1e9 - (stamp.sec + stamp.nanosec / 1e9)
    speed = odom.twist.twist
    return age, math.hypot(speed.linear.x, speed.linear.y), abs(speed.angular.z)


async def check_high_preemption(config_path, robot_namespaces, executor, node, odometry, statuses, emit):
    import rclpy

    emit("SCENARIO_START", test=TEST, name="real_high_delivery_after_safe_preemption")
    core, robot_ids = build_fleet_manager_from_config(config_path, _legacy_test_battery=True)
    # Seed a blocked resource in the fresh DB to verify that task preemption cannot free it.
    park = next(iter(core.reservations.list_stations(StationType.PARKING)))
    assert core.reservations.mark_blocked(park.station_id, "robot_1")
    store = SQLiteStore("/tmp/c3_3_3_t04-high-e2e.db")
    fm_node = rclpy.create_node(
        "fm_t04_high_e2e", parameter_overrides=[Parameter("use_sim_time", value=True)],
    )
    executor.add_node(fm_node)
    terminal = {}

    class ObservedConsumer(FleetEventLoop):
        def _process(self, event):
            stop = None
            if event.kind == "ACTION_RESULT" and event.payload["task_id"] == "victim":
                assert store.connection.execute(
                    "SELECT count(*) FROM outbox_events WHERE task_id='urgent' AND kind='EXECUTE_TASK'"
                ).fetchone()[0] == 0, "HIGH assignment appeared before the victim's terminal result"
                stop = standstill(node, odometry[event.payload["robot_id"]][-1])
            outcome = super()._process(event)
            if event.kind == "ACTION_RESULT" and outcome == "APPLIED":
                terminal[event.payload["task_id"]] = (event.payload, stop)
            return outcome

    consumer = ObservedConsumer(store, core)
    await consumer.start()
    try:
        adapter = FleetROS2Adapter(fm_node, consumer, asyncio.get_running_loop(), robot_ids,
                                   robot_namespaces=robot_namespaces)
        dispatcher = OutboxDispatcher(consumer, adapter.outbox_sender, clock=time.monotonic, retry_delay=1.0)
        await until(lambda: all(consumer.core.tracker.get_robot(robot).is_eligible_for_new_assignment(
            time.monotonic()) for robot in robot_ids), "two verified IDLE robots", 15.0)
        assert len(adapter.route_cache) == 0
        assert store.connection.execute("SELECT count(*) FROM outbox_events").fetchone()[0] == 0

        def reservations():
            return [tuple(row) for row in store.connection.execute(
                "SELECT station_id, state, reserved_by, occupied_by FROM reservations ORDER BY station_id"
            )]

        expected_reservations = reservations()
        assert (park.station_id, "BLOCKED", "robot_1", "robot_1") in expected_reservations

        async def submit(task_id, priority, pickup, dropoff):
            created = time.monotonic()
            assert await consumer.submit(Event("SUBMIT_TASK", {
                "task_id": task_id, "priority": priority, "created_at": created,
                "pickup_pose": Pose2D(*pickup), "dropoff_pose": Pose2D(*dropoff),
            })) == "APPLIED"
            return created

        def commands(task_id, kind):
            return [tuple(row) for row in store.connection.execute(
                "SELECT assignment_epoch, goal_uuid, state, attempts FROM outbox_events "
                "WHERE task_id=? AND kind=? ORDER BY sequence", (task_id, kind)
            )]

        def moving(task_id, robot):
            last = statuses[robot][-1]
            _, linear, _ = standstill(node, odometry[robot][-1])
            return (last.current_task_id == task_id and last.state == RobotState.STATE_EXECUTING_TASK
                    and last.current_phase == TaskPhase.PHASE_MOVING_TO_PICKUP
                    and not last.is_loaded and linear > 0.01)

        # Both robots are physically executing. The second robot's HIGH cannot be preempted.
        await submit("parallel", TaskPriority.PRIORITY_HIGH, (-1.5, 2.5, math.pi), (-3.5, 2.5, math.pi))
        parallel = await until(lambda: consumer.core._active_tasks.get("parallel"), "parallel assignment", 15.0)
        assert parallel.assigned_robot_id == "robot_2"
        assert await dispatcher.send_one()

        created = await submit("victim", TaskPriority.PRIORITY_LOW, (1.0, -0.5, 0), (1.5, -0.5, 0))
        victim = await until(lambda: consumer.core._active_tasks.get("victim"), "LOW assignment", 15.0)
        assert victim.assigned_robot_id == "robot_1"
        assert await dispatcher.send_one()
        await until(lambda: moving("victim", "robot_1") and moving("parallel", "robot_2"),
                    "two moving, unloaded robots before pickup", 10.0)

        await submit("urgent", TaskPriority.PRIORITY_HIGH, (-0.8, -0.5, 0), (0.2, -0.5, 0))
        await until(lambda: commands("victim", "CANCEL_TASK"), "normal Scheduler cancellation", 10.0)
        assert commands("victim", "CANCEL_TASK") == [(victim.assignment_epoch, victim.goal_uuid, "PENDING", 0)]
        assert not commands("urgent", "EXECUTE_TASK")
        assert reservations() == expected_reservations
        assert consumer.core._active_tasks_by_robot["robot_2"].goal_uuid == parallel.goal_uuid
        await submit("younger", TaskPriority.PRIORITY_LOW, (1.1, -0.5, 0), (1.6, -0.5, 0))
        assert await dispatcher.send_one()

        result, stop = await until(lambda: terminal.get("victim"), "matched PREEMPTED result", 25.0)
        assert (result["assignment_epoch"], result["completed_epoch"], result["goal_uuid"],
                result["result_status"]) == (victim.assignment_epoch, victim.assignment_epoch,
                                             victim.goal_uuid, TaskResultStatus.STATUS_PREEMPTED)
        age, linear, angular = stop
        assert 0 <= age <= 0.5 and linear <= 0.01 and angular <= 0.01, stop
        emit("LIVE_PREEMPTION_TERMINAL", task_id="victim", goal_uuid=victim.goal_uuid,
             completed_epoch=result["completed_epoch"], odom_age_s=age,
             linear_m_s=linear, angular_rad_s=angular)
        high = await until(lambda: consumer.core._active_tasks.get("urgent"), "HIGH reassignment via Nav2", 15.0)
        assert high.assigned_robot_id == "robot_1"
        assert high.assignment_epoch == victim.assignment_epoch + 1 and high.goal_uuid != victim.goal_uuid
        assert commands("urgent", "EXECUTE_TASK") == [(high.assignment_epoch, high.goal_uuid, "PENDING", 0)]
        assert [task.task_id for task in consumer.core.queue.iter_assignable_tasks()] == ["victim", "younger"]
        assert store.connection.execute(
            "SELECT count(*) FROM processed_events WHERE outcome='ROUTE_APPLIED'"
        ).fetchone()[0] >= 9
        assert reservations() == expected_reservations

        assert await dispatcher.send_one()
        result, _ = await until(lambda: terminal.get("urgent"), "HIGH terminal completion", 120.0)
        assert (result["completed_epoch"], result["goal_uuid"], result["result_status"]) == (
            high.assignment_epoch, high.goal_uuid, TaskResultStatus.STATUS_SUCCEEDED,
        )
        phases = list(dict.fromkeys(
            (msg.current_phase, msg.is_loaded) for msg in statuses["robot_1"]
            if msg.current_task_id == "urgent" and msg.current_epoch == high.assignment_epoch
        ))
        assert phases == [(1, False), (2, False), (3, True), (4, True)], phases

        row = store.connection.execute(
            "SELECT status, robot_id, assignment_epoch, goal_uuid FROM tasks WHERE task_id='urgent'"
        ).fetchone()
        assert tuple(row) == ("COMPLETED", "robot_1", high.assignment_epoch, high.goal_uuid)
        victim_snapshot = json.loads(store.connection.execute(
            "SELECT snapshot FROM tasks WHERE task_id='victim'"
        ).fetchone()[0])
        assert (victim_snapshot["created_at"], victim_snapshot["preemption_count"]) == (created, 1)
        assert commands("urgent", "EXECUTE_TASK") == [(high.assignment_epoch, high.goal_uuid, "SENT", 1)]
        assert not commands("parallel", "CANCEL_TASK")
        assert reservations() == expected_reservations
        assert not any(robot.session_blocked for robot in consumer.core.tracker.list_robots())
        assert store.connection.execute("SELECT count(*) FROM task_review_holds").fetchone()[0] == 0
        parallel_result, _ = await until(lambda: terminal.get("parallel"), "parallel task completion", 120.0)
        assert parallel_result["result_status"] == TaskResultStatus.STATUS_SUCCEEDED
        assert reservations() == expected_reservations
        emit("SCENARIO_PASSED", test=TEST, high_goal_uuid=high.goal_uuid, high_epoch=high.assignment_epoch,
             phases=phases, victim_preemption_count=1, fifo=["victim", "younger"], reservations=reservations())
    finally:
        executor.remove_node(fm_node)
        await consumer.close()
        store.close()
