"""Process supervision shared by the C2.3 and C3.3.3 live test harnesses."""

import os
import signal
import subprocess
import time


def bridge_executable():
    from ament_index_python.packages import get_package_prefix

    return os.path.join(get_package_prefix("ros_gz_bridge"), "lib", "ros_gz_bridge", "parameter_bridge")


def shutdown_nav2(namespaces, emit):
    import rclpy
    from nav2_msgs.srv import ManageLifecycleNodes
    from rclpy.signals import SignalHandlerOptions

    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = rclpy.create_node("live_test_shutdown")
    clean = True
    try:
        for manager in ("navigation", "localization"):
            deadline = time.monotonic() + 5.0
            pending = {}
            for namespace in namespaces:
                service = f"/{namespace}/lifecycle_manager_{manager}/manage_nodes"
                client = node.create_client(ManageLifecycleNodes, service)
                if client.wait_for_service(timeout_sec=max(0.0, deadline - time.monotonic())):
                    request = ManageLifecycleNodes.Request(command=ManageLifecycleNodes.Request.SHUTDOWN)
                    pending[service] = client.call_async(request)
                else:
                    emit("LIFECYCLE_SHUTDOWN", service=service, success=False, reason="unavailable")
                    clean = False
            while pending and time.monotonic() < deadline:
                rclpy.spin_once(node, timeout_sec=max(0.0, deadline - time.monotonic()))
                for service, future in list(pending.items()):
                    if future.done():
                        success = future.exception() is None and future.result().success
                        emit("LIFECYCLE_SHUTDOWN", service=service, success=success)
                        clean = clean and success
                        del pending[service]
            for service in pending:
                emit("LIFECYCLE_SHUTDOWN", service=service, success=False, reason="timeout")
                clean = False
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
    return clean


def stop_processes(children, timeout, emit):
    # Signal launch itself so it owns shutdown of its Nav2 child processes.
    for _, child in children:
        child.send_signal(signal.SIGINT)
    deadline = time.monotonic() + timeout
    clean = True
    for name, child in children:
        try:
            child.wait(timeout=max(0.0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            clean = False
            emit("FORCED_KILL", process=name)
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait(timeout=1.0)
        emit("PROCESS_EXIT", process=name, code=child.returncode)
        clean = clean and child.returncode == 0
    return clean


def run_simulation(commands, namespaces, emit):
    stopped = False

    def stop(signum, frame):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    children = {}
    clean = True
    try:
        for name, command in commands:
            if stopped:
                break
            emit("PROCESS_START", process=name, command=command)
            children[name] = subprocess.Popen(command, start_new_session=True)
        while not stopped:
            for name, child in children.items():
                if child.poll() is not None:
                    raise RuntimeError(f"{name} exited unexpectedly: {child.returncode}")
            time.sleep(0.2)
    finally:
        def stop_group(names, timeout):
            return stop_processes([(name, children[name]) for name in names if name in children], timeout, emit)

        # Keep the bridge and simulator alive for lifecycle deactivation and zero velocity.
        helpers = [name for name in children if name.startswith("executor") or name == "battery_feeder"]
        clean = stop_group(helpers, 3.0)
        nav2 = [name for name in children if name.startswith("nav2")]
        if nav2:
            try:
                clean = shutdown_nav2(namespaces, emit) and clean
            except Exception as exc:
                emit("LIFECYCLE_SHUTDOWN_ERROR", error=str(exc))
                clean = False
        clean = stop_group(nav2, 11.0) and clean
        clean = stop_group(("tf_helper", "bridge"), 3.0) and clean
        clean = stop_group(("gazebo",), 4.0) and clean
        emit("SIMULATION_SHUTDOWN", clean=clean)
    return 0 if clean else 1
