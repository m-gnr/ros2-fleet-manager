"""Entry point. Own only this process's ROS executor and WebSocket listener."""
import argparse
import asyncio
from math import isfinite
from pathlib import Path
import signal
from threading import Event
from urllib.parse import urlsplit

from yaml import YAMLError

from fleet_config import load_config
from server import Stream, listen
from telemetry import Telemetry

ROOT = Path(__file__).resolve().parents[2]


def options():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fleet", type=Path, default=ROOT / "config/fleet.yaml")
    parser.add_argument("--robot", required=True, help="Robot id in fleet.yaml")
    parser.add_argument("--source", choices=("tf", "diagnostic_odom"), default="tf")
    parser.add_argument("--hz", type=float, default=20)
    parser.add_argument("--stale-seconds", type=float, default=1)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--origin", action="append")
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()
    if not isfinite(args.hz) or not 1 <= args.hz <= 60:
        parser.error("--hz must be finite and in 1..60")
    if not isfinite(args.stale_seconds) or not 2 / args.hz <= args.stale_seconds <= 10:
        parser.error("--stale-seconds must cover two sampling intervals and be at most 10")
    if not 1 <= args.port <= 65535:
        parser.error("--port must be in 1..65535")
    args.origin = args.origin or ["http://127.0.0.1:5173"]
    try:
        for origin in args.origin:
            parsed = urlsplit(origin)
            if (parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username
                    or parsed.path or parsed.query or parsed.fragment or parsed.port == 0):
                raise ValueError(f"Invalid browser origin: {origin}")
        fleet = load_config(args.fleet, schema_path=args.fleet.with_name("fleet.schema.json"))
        robot = next((robot for robot in fleet.robots if robot.id == args.robot), None)
        if robot is None:
            raise ValueError(f"Unknown robot id {args.robot!r}")
    except (ValueError, OSError, YAMLError) as error:
        parser.error(str(error))
    return args, robot


async def run(args, robot):
    import rclpy
    from rclpy.context import Context
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.signals import SignalHandlerOptions

    from ros_reader import RosReader

    frame = "map" if args.source == "tf" else robot.namespace.lstrip("/") + "/odom"
    telemetry = Telemetry(robot.id, frame, args.source, args.stale_seconds)
    def read_clock():
        return telemetry.clock_observation

    stream = Stream(telemetry.identity, stale_ms=1000 * args.stale_seconds,
                    trace_clock=read_clock if args.trace else None)
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    context = Context()
    rclpy.init(args=[], context=context, signal_handler_options=SignalHandlerOptions.NO)
    reader = executor = spin = None
    stop_ros = Event()
    try:
        reader = RosReader(robot.namespace, telemetry, args.hz,
                           lambda sample: loop.call_soon_threadsafe(stream.update, sample),
                           context=context)
        executor = SingleThreadedExecutor(context=context)
        executor.add_node(reader)
        async with listen(stream, args.bind, args.port, args.origin):
            print(f"Listening on {args.bind}:{args.port}/telemetry for {robot.id} ({frame})", flush=True)
            def pump_ros():
                # Fortress can send /clock at physics rate. Keep only its latest sample
                # and cap dispatch work independently of that publishing rate.
                while not stop_ros.is_set() and context.ok():
                    executor.spin_once(timeout_sec=0.025)
                    stop_ros.wait(0.004)

            spin = loop.run_in_executor(None, pump_ros)
            stopped = asyncio.create_task(stop.wait())
            try:
                await asyncio.wait((spin, stopped), return_when=asyncio.FIRST_COMPLETED)
                if spin.done():
                    spin.result()
            finally:
                stopped.cancel()
    finally:
        stop_ros.set()
        if spin is not None:
            await asyncio.gather(spin, return_exceptions=True)
        if executor is not None:
            executor.shutdown()
        if reader is not None:
            reader.destroy_node()
        if context.ok():
            context.shutdown()
        print("VISUALIZER_SHUTDOWN clean=true", flush=True)


if __name__ == "__main__":
    asyncio.run(run(*options()))
