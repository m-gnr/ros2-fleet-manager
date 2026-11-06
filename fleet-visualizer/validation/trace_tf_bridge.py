"""Test-only probe for which localization anchors the existing reader accepted."""
import asyncio
import json

from ros_reader import RobotReader, stamp_ns
from run import options, run

read_tf = RobotReader.on_tf
sample_tf = RobotReader.sample


def record_anchor(self, message):
    prior = self.localization_ns
    read_tf(self, message)
    if self.localization_ns == prior:
        return
    for transform in message.transforms:
        if (transform.header.frame_id == self.frame and transform.child_frame_id == self.odom_frame
                and stamp_ns(transform.header.stamp) == self.localization_ns):
            print(json.dumps(dict(event="anchor", robot=self.robot_id, stamp_ns=self.localization_ns)), flush=True)
            break


def record_pose(self, now):
    prior = self.telemetry.pose
    snapshot = sample_tf(self, now)
    pose = snapshot.pose
    if pose is not None and prior is not pose and snapshot.status == "LIVE":
        print(json.dumps(dict(event="pose", robot=self.robot_id, stamp_ns=pose.stamp_ns,
                              x=pose.x, y=pose.y, localization_ns=self.localization_ns)), flush=True)
    return snapshot


RobotReader.on_tf = record_anchor
RobotReader.sample = record_pose
asyncio.run(run(*options()))
