"""Run the existing ROS Fleet Manager consumer with catalog tasks and dashboard publication."""
import argparse
import asyncio
from contextlib import closing
from pathlib import Path
import signal
import threading
import time

from backend.fleet_manager.builder import build_fleet_manager_from_config
from backend.fleet_manager.event_loop import Event, FleetEventLoop, OutboxDispatcher
from backend.fleet_manager.persistence.store import SQLiteStore
from fleet_config import load_config

from .publisher import publish_fleet


async def run(args, node):
    from backend.fleet_manager.adapters.ros2_adapter_node import FleetROS2Adapter

    config = load_config(args.fleet)
    core, robots = build_fleet_manager_from_config(args.fleet)
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    with closing(SQLiteStore(args.database)) as store:
        consumer = FleetEventLoop(store, core)
        await consumer.start()
        try:
            adapter = FleetROS2Adapter(node, consumer, loop, robots,
                robot_namespaces={robot.id: robot.namespace for robot in config.robots})
            dispatcher = OutboxDispatcher(consumer, adapter.outbox_sender, clock=time.monotonic, retry_delay=1.0)

            async def drive():
                while not stop.is_set():
                    await consumer.submit(Event('TICK', dict(current_time=time.monotonic())))
                    await dispatcher.send_one()
                    await asyncio.sleep(.05)

            async with publish_fleet(consumer, args.snapshot, fleet_config=config):
                worker = asyncio.create_task(drive())
                stopped = asyncio.create_task(stop.wait())
                try:
                    done, _ = await asyncio.wait((worker, stopped), return_when=asyncio.FIRST_COMPLETED)
                    for future in done:
                        future.result()
                finally:
                    worker.cancel()
                    stopped.cancel()
                    await asyncio.gather(worker, stopped, return_exceptions=True)
        finally:
            await consumer.close()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(sig)


def main():
    import rclpy
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.parameter import Parameter
    from rclpy.signals import SignalHandlerOptions

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fleet', type=Path, required=True)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path, required=True)
    args = parser.parse_args()
    # Existing nonempty databases are rejected by FleetEventLoop, preserving scenario reset semantics.
    args.snapshot.parent.mkdir(parents=True, exist_ok=True)
    args.database.parent.mkdir(parents=True, exist_ok=True)
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = rclpy.create_node('fleet_manager', parameter_overrides=[Parameter('use_sim_time', value=True)])
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    try:
        asyncio.run(run(args, node))
    finally:
        executor.shutdown()
        thread.join(timeout=5)
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
