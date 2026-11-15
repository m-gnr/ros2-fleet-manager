"""No Gazebo, world, joint driver or nonzero output exists in this harness."""
import json
import os
from pathlib import Path
import secrets
import select
import signal
import subprocess
import sys
import time

import pytest
from authorization import ZeroSink, command, sign

HERE = Path(__file__).resolve().parent
KEY = secrets.token_bytes(32)


def sink():
    return ZeroSink('/tmp/b6b6-lease.so', KEY, 'fixture-gate-session',
                    {'task': 'test-only', 'epoch': 1, 'child': 'fixture-child'}, 'fixture-permit', 1)


@pytest.mark.parametrize('case,reason', [
    ('authorized', 'ACCEPTED_ZERO'), ('old_source', 'SESSION'), ('old_actuator', 'SESSION'),
    ('replay', 'REPLAY'), ('changed', 'CHANGED_PAYLOAD'), ('bad_mac', 'UNAUTHENTICATED'),
    ('permit', 'PERMIT'), ('expired_permit', 'PERMIT'), ('context', 'CONTEXT'),
    ('expired', 'EXPIRED_OR_USED_TICKET'), ('nonzero', 'NONZERO_DISABLED'),
    ('clock', 'CLOCK_SCHEMA'), ('bad_json', 'MALFORMED'),
])
def test_envelope(case, reason):
    s = sink()
    try:
        b = command(s)
        if case in ('replay', 'changed'):
            assert s.receive(sign(b, KEY)) == 'ACCEPTED_ZERO'
        if case == 'changed': b['velocity'][0] = .1
        if case == 'old_source': b['source_session'] = 'old'
        if case == 'old_actuator': b['actuator_session'] = 'old'
        if case == 'permit': b['permit_generation'] = 2
        if case == 'expired_permit': s.permit_until = time.monotonic() - 1
        if case == 'context': b['command_context'] = {}
        if case == 'expired': s.tickets[b['ticket']] = time.monotonic() - 1
        if case == 'nonzero': b['velocity'][5] = .1
        if case == 'clock': b['issued_at']['clock'] = 'ros_sim'
        wire = sign(b, b'wrong' if case == 'bad_mac' else KEY)
        if case == 'bad_json': wire = '{}'
        assert s.receive(wire) == reason
        assert s.target == (0.,)*6 and not s.movement_authorized and not s.ownership_release
    finally:
        s.lease.close()


def test_native_timeout_rearm_and_restart():
    s = sink()
    restarted = sink()
    try:
        assert s.lease.tick() == 'NO_COMMAND'
        old = command(s)
        assert s.receive(sign(old, KEY)) == 'ACCEPTED_ZERO'
        time.sleep(.27)
        assert s.lease.tick() == 'TIMED_OUT'
        assert s.receive(sign(command(s, 2), b'wrong')) == 'UNAUTHENTICATED'
        assert s.lease.tick() == 'TIMED_OUT'
        assert s.receive(sign(command(s, 3), KEY)) == 'BLOCKED_REARM'
        assert restarted.receive(sign(old, KEY)) == 'SESSION'
        # Even a fresh valid instance/session can only accept zero diagnostics.
        assert restarted.receive(sign(command(restarted), KEY)) == 'ACCEPTED_ZERO'
        assert restarted.target == s.target == (0.,)*6
    finally:
        s.lease.close(); restarted.lease.close()


def test_real_ros_ign_transport_and_process_loss():
    import rclpy
    from std_msgs.msg import String
    rclpy.init()
    n = rclpy.create_node('b6b6_fake_actuator')
    s = sink()
    processes = []
    results = []
    received_wires = []
    topic = '/b6b6_' + secrets.token_hex(6)
    observed = topic + '_observed'
    timer = n.create_timer(.01, lambda: s.lease.tick())
    def receive(m):
        received_wires.append(m.data)
        results.append(s.receive(m.data))
    sub = n.create_subscription(String, observed, receive, 1)
    rogue = n.create_publisher(String, topic, 1)

    def start(args, stdin=None, stdout=subprocess.DEVNULL):
        p = subprocess.Popen(args, stdin=stdin, stdout=stdout,
                             stderr=subprocess.DEVNULL, start_new_session=True, text=True)
        processes.append(p)
        return p

    def stop(p):
        os.killpg(p.pid, signal.SIGKILL)
        p.wait(timeout=5)

    def pump(predicate, seconds=8):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            rclpy.spin_once(n, timeout_sec=.01)
            if predicate(): return
        raise AssertionError('transport condition timed out: '+str(results))

    def gate():
        p = start([sys.executable, str(HERE/'producer.py'), topic], subprocess.PIPE, subprocess.PIPE)
        assert select.select([p.stdout], [], [], 8)[0], 'gate discovery timeout'
        assert p.stdout.readline().strip() == 'READY'
        return p

    def bridge():
        return start(['ros2','run','ros_gz_bridge','parameter_bridge',
                      topic+'@std_msgs/msg/String]ignition.msgs.StringMsg'])

    def send(p, body, expected):
        at = len(results)
        p.stdin.write(sign(body, KEY)+'\n'); p.stdin.flush()
        pump(lambda: expected in results[at:])
        assert expected in results[at:]

    try:
        b = bridge()
        readback = start(['ros2','run','ros_gz_bridge','parameter_bridge',
                         topic+'@std_msgs/msg/String[ignition.msgs.StringMsg',
                         '--ros-args','-r',topic+':='+observed])
        g = gate()
        pump(lambda: rogue.get_subscription_count() >= 1 and n.count_publishers(topic) >= 2
             and n.count_publishers(observed) >= 1)
        # Establish IGN discovery without refreshing the native lease.
        rogue.publish(String(data='{}'))
        pump(lambda: bool(results))
        old = command(s)
        send(g, old, 'ACCEPTED_ZERO')
        send(g, old, 'REPLAY')
        changed = dict(old, velocity=[.1,0,0,0,0,0])
        send(g, changed, 'CHANGED_PAYLOAD')
        # ROS access succeeds; MAC rejection is at the receiving adapter.
        at = len(results)
        rogue.publish(String(data=sign(command(s, 2), b'rogue')))
        pump(lambda: len(results) > at)
        assert results[-1] == 'UNAUTHENTICATED'
        # IGN access also succeeds. No claim of transport ACL enforcement.
        at = len(results)
        wire = sign(command(s, 2), b'rogue')
        start(['ign','topic','-t',topic,'-m','ignition.msgs.StringMsg','-p','data: '+json.dumps(wire)])
        pump(lambda: len(results) > at)
        assert results[-1] == 'UNAUTHENTICATED'
        stop(g)
        pump(lambda: s.lease.tick() == 'TIMED_OUT')
        g2 = gate()
        pump(lambda: n.count_publishers(topic) >= 2)
        send(g2, command(s, 3), 'BLOCKED_REARM')
        stop(b)
        # New actuator fixture for independent bridge-loss timeout evidence.
        s.lease.close(); s = sink()
        b = bridge()
        # Discovery probe is invalid and cannot activate the watchdog.
        probe = json.dumps({'probe': secrets.token_hex(8)})
        until = time.monotonic() + 8
        while probe not in received_wires and time.monotonic() < until:
            g2.stdin.write(probe+'\n'); g2.stdin.flush()
            for _ in range(10):
                rclpy.spin_once(n, timeout_sec=.01)
        assert probe in received_wires
        send(g2, command(s), 'ACCEPTED_ZERO')
        stop(b)
        pump(lambda: s.lease.tick() == 'TIMED_OUT')
        b = bridge()
        probe = json.dumps({'probe': secrets.token_hex(8)})
        until = time.monotonic() + 8
        while probe not in received_wires and time.monotonic() < until:
            g2.stdin.write(probe+'\n'); g2.stdin.flush()
            for _ in range(10):
                rclpy.spin_once(n, timeout_sec=.01)
        assert probe in received_wires
        send(g2, command(s, 2), 'BLOCKED_REARM')
        assert s.target == (0.,)*6 and not s.ownership_release
        print('ROS/IGN writes reachable; unauthorized envelopes rejected; gate/bridge SIGKILL native timeout; restart stays blocked; physical_stop=UNVERIFIED')
    finally:
        for p in processes:
            if p.poll() is None: stop(p)
            if p.stdin: p.stdin.close()
            if p.stdout: p.stdout.close()
        s.lease.close()
        n.destroy_node(); rclpy.shutdown()


def test_product_baseline_unchanged():
    import hashlib
    root = HERE.parents[2]
    baseline = json.loads((root/'docs/validation/c5/c5-b6b6-authorization-2026-11-15/product-baseline.json').read_text())
    assert all(hashlib.sha256((root/name).read_bytes()).hexdigest() == digest for name, digest in baseline.items())
    print(f'{len(baseline)} tracked non-document files unchanged; includes C5-A/config/launcher')


def test_sequence_refresh_and_rejections_never_refresh():
    s = sink()
    try:
        first = command(s)
        assert s.receive(sign(first, KEY)) == 'ACCEPTED_ZERO'
        time.sleep(.04)
        second = command(s, 2)
        assert s.receive(sign(second, KEY)) == 'ACCEPTED_ZERO'
        assert len(s.receipts) == 2 and s.receipts[1] > s.receipts[0]
        deadline_start = time.monotonic()
        while time.monotonic() - deadline_start < .27:
            assert s.receive(sign(second, KEY)) in ('REPLAY', 'BLOCKED_REARM')
            assert s.receive(sign(command(s, 3), b'rogue')) == 'UNAUTHENTICATED'
            time.sleep(.02)
        assert s.lease.tick() == 'BLOCKED_REARM'
        assert len(s.receipts) == 2 and s.target == (0.,)*6
    finally:
        s.lease.close()
