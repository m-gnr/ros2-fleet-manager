"""Actual Gazebo/native receiver, real ROS/IGN negatives, zero motion only."""
import argparse
from collections import defaultdict
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import rclpy
from geometry_msgs.msg import PoseStamped, Twist
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, qos_profile_sensor_data
from std_msgs.msg import String

from fleet_config import load_config
from producer import body, wire


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    config = load_config(args.profile)
    assert len(config.robots) >= 3
    args.output.mkdir(exist_ok=False)
    raw = (args.output/"native.jsonl").open("w")
    rclpy.init()
    node = rclpy.create_node("native_zero_receiver_acceptance")
    qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.VOLATILE)
    states, positions, children = {}, defaultdict(list), []
    counts = defaultdict(int)
    invalid_joint_commands = []
    report = {"movement_authorized": False, "ownership_release": False, "cases": {}}

    def state(rid, message):
        value = json.loads(message.data)
        value["observed_monotonic"] = time.monotonic()
        states[rid] = value
        counts[rid] += 1
        if (value["target_linear"] != 0 or value["target_angular"] != 0 or
            any(joint != [0.] for joint in value["joint_commands"] if joint is not None)):
            invalid_joint_commands.append((rid, value))
        raw.write(json.dumps(dict(robot=rid, **value)) + "\n")

    publishers = {}
    for robot in config.robots:
        node.create_subscription(String, robot.namespace+"/native_actuator",
            lambda m, rid=robot.id: state(rid, m), qos)
        node.create_subscription(PoseStamped, robot.namespace+"/physical_pose",
            lambda m, rid=robot.id: positions[rid].append((m.pose.position.x, m.pose.position.y)),
            qos_profile_sensor_data)
        publishers[robot.id] = node.create_publisher(String, robot.namespace+"/authorized_zero", qos)

    def until(predicate, timeout=6.):
        deadline = time.monotonic()+timeout
        while time.monotonic()<deadline:
            rclpy.spin_once(node, timeout_sec=.01)
            if predicate(): return
        raise AssertionError("Native/transport evidence unavailable: "+str(states))

    def pump(seconds):
        end = time.monotonic()+seconds
        while time.monotonic()<end: rclpy.spin_once(node, timeout_sec=.01)

    def start(name, command):
        log = (args.output/(name+".log")).open("w")
        p = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        log.close(); children.append(p); return p

    def stop(p):
        if p.poll() is None: os.killpg(p.pid, signal.SIGKILL)
        p.wait(timeout=5)

    try:
        until(lambda: len(states)==len(config.robots) and all(len(v["joint_commands"]) == 2 for v in states.values()))
        assert all(v["sequence"]==0 for v in states.values())
        # The only native subscriber uses StringMsg; legacy Twist has no drive.
        inventory = {}
        for robot in config.robots:
            for topic in (robot.namespace+"/cmd_vel", robot.namespace+"/authorized_zero"):
                inventory[topic] = subprocess.check_output(["ign", "topic", "-i", "-t", topic], text=True, timeout=5)
            p = node.create_publisher(Twist, robot.namespace+"/cmd_vel", qos)
            command = Twist(); command.linear.x=.4
            for _ in range(3):p.publish(command); pump(.03)
            subprocess.run(["ign", "topic", "-t", robot.namespace+"/cmd_vel", "-m", "ignition.msgs.Twist",
                            "-p", "linear: {x: 0.4}"], check=True, capture_output=True, timeout=5)
        pump(.1)
        assert all(v["sequence"]==0 for v in states.values())
        report["cases"]["raw_ros_and_ign_twist"] = "NO_AUTHENTICATED_RECEIPT; no raw driver subscriber"
        report["transport_inventory"] = inventory
        forward = ["ros2", "run", "ros_gz_bridge", "parameter_bridge"] + [
            r.namespace+"/authorized_zero@std_msgs/msg/String]ignition.msgs.StringMsg" for r in config.robots]
        bridge = start("command-bridge", forward)
        until(lambda: all(p.get_subscription_count() for p in publishers.values()))
        producers = {}
        for robot in config.robots:
            producers[robot.id] = start("producer-"+robot.id, [sys.executable, str(Path(__file__).with_name("producer.py")),
                "--namespace", robot.namespace, "--provision", "/run/c5-b6b7/"+robot.id+".json"])
        until(lambda: all(s["accepted"]>=8 for s in states.values()))
        assert all(s["state"]=="ACTIVE" for s in states.values())
        report["cases"]["authorized_zero"] = {rid:s["accepted"] for rid,s in states.items()}
        alpha, beta, gamma = [r.id for r in config.robots[:3]]
        stop(producers[alpha]); pump(.05)
        original = states[alpha]["receipt_steady_ns"]
        provision = json.loads(Path("/run/c5-b6b7/"+alpha+".json").read_text())
        rejected_before = states[alpha]["rejected"]
        b = body(provision, states[alpha], states[alpha]["sequence"]+1)
        direct = wire(b, b"wrong-key")
        namespace = next(r.namespace for r in config.robots if r.id == alpha)
        subprocess.run(["ign", "topic", "-t", namespace+"/authorized_zero", "-m", "ignition.msgs.StringMsg",
                        "-p", "data: "+json.dumps(direct)], check=True, capture_output=True, timeout=5)
        until(lambda: states[alpha]["rejected"]>rejected_before)
        assert states[alpha]["receipt_steady_ns"]==original
        report["cases"]["direct_ign_signed_topic_wrong_mac"] = "DELIVERED_AND_REJECTED; receipt unchanged; not transport ACL"
        # A real rogue ROS publisher sends well-formed wrong-MAC messages while
        # the accepted source has died. Traffic cannot extend the native lease.
        end = time.monotonic()+.6
        while time.monotonic()<end:
            b = body(provision, states[alpha], states[alpha]["sequence"]+1)
            publishers[alpha].publish(String(data=wire(b, b"wrong-key"))); pump(.03)
        assert states[alpha]["receipt_steady_ns"]==original
        assert states[alpha]["state"]=="TIMED_OUT"
        b = body(provision, states[alpha], states[alpha]["sequence"]+1)
        publishers[alpha].publish(String(data=wire(b, bytes.fromhex(provision["key_hex"]))));
        until(lambda: states[alpha]["reason"]=="BLOCKED_REARM")
        report["cases"]["source_loss_wrong_mac_and_no_rearm"] = dict(receipt_unchanged=True, state=states[alpha])
        stop(producers[beta]); pump(.03)
        provision = json.loads(Path("/run/c5-b6b7/"+beta+".json").read_text())
        b = body(provision, states[beta], states[beta]["sequence"]+1)
        b["velocity"][0] = .1
        publishers[beta].publish(String(data=wire(b, bytes.fromhex(provision["key_hex"]))));
        until(lambda: states[beta]["reason"]=="NONZERO_DISABLED")
        report["cases"]["authenticated_nonzero"] = dict(state=states[beta])
        stop(bridge); pump(.5)
        assert states[gamma]["state"]=="TIMED_OUT"
        before = states[gamma]["receipt_steady_ns"]
        bridge = start("command-bridge-restarted", forward)
        until(lambda: all(p.get_subscription_count() for p in publishers.values()))
        provision = json.loads(Path("/run/c5-b6b7/"+gamma+".json").read_text())
        b = body(provision, states[gamma], states[gamma]["sequence"]+1)
        retry = String(data=wire(b, bytes.fromhex(provision["key_hex"])))
        # DDS can retain the killed subscriber's discovery entry. Its count
        # is not an acknowledgement from the restarted bridge/native receiver.
        deadline = time.monotonic()+6.
        while states[gamma]["reason"] != "BLOCKED_REARM" and time.monotonic()<deadline:
            publishers[gamma].publish(retry); pump(.05)
        assert states[gamma]["reason"]=="BLOCKED_REARM"
        assert states[gamma]["receipt_steady_ns"]==before
        report["cases"]["bridge_loss_and_restart"] = dict(state=states[gamma], receipt_unchanged=True)
        # Locate the actual server mapping without trusting the SDF filename.
        maps = []
        for p in Path("/proc").glob("[0-9]*/maps"):
            try:
                entries=p.read_text()
            except (OSError, PermissionError):continue
            if "libc5-authorized-zero-drive.so" in entries:
                assert "libignition-gazebo-diff-drive-system.so" not in entries
                maps.append(dict(pid=int(p.parent.name), mappings=[s for s in entries.splitlines() if "libc5-authorized-zero-drive.so" in s]))
        assert maps
        report["native_loaded_mappings"] = maps
        assert not invalid_joint_commands
        report["physical_max_displacement_m"] = {rid:max(math.dist(p,rows[0]) for p in rows) for rid,rows in positions.items()}
        assert len(positions)==len(config.robots) and all(v<.001 for v in report["physical_max_displacement_m"].values())
        assert not (args.output.parent/"unsafe-contact").exists()
        report.update(result="PASS_ZERO_ONLY", native_samples=dict(counts), invalid_joint_commands=invalid_joint_commands,
                      limits="No moving-stop, release, traffic motion authority, or transport ACL qualification")
    finally:
        for child in children:
            if child.poll() is None: stop(child)
        raw.close()
        report.setdefault("result", "FAIL")
        (args.output/"summary.json").write_text(json.dumps(report,indent=2)+"\n")
        node.destroy_node(); rclpy.try_shutdown()


if __name__ == "__main__":
    main()
