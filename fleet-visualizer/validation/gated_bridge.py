"""Test-only bridge wrapper that drops incoming TF for IDs with a local gate file."""
import asyncio
from pathlib import Path

from ros_reader import RobotReader
from run import options, run

GATES = Path("/validation-gates")
read_tf = RobotReader.on_tf


def gated_tf(self, message):
    if not (GATES / self.robot_id).exists():
        read_tf(self, message)


RobotReader.on_tf = gated_tf
asyncio.run(run(*options()))
