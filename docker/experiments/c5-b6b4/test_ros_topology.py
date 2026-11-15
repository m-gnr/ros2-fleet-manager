"""Real DDS and Ignition transport; fake producers/actuator, no Gazebo server."""
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String

from gate_adapter import QOS, axes
from topology import topology, remappings, bridge_arguments

HERE = Path(__file__).resolve().parent


def test_zero_only_topology_and_bypass_inventory():
    rclpy.init(args=[])
    ns = '/b6b4_test/r' + uuid4().hex
    t = topology(ns)
    nodes, processes = [], []
    executor = SingleThreadedExecutor()
    report = {}

    def node(name, mappings=()):
        n = Node(name, namespace=ns, cli_args=['--ros-args', *[v for a, b in mappings for v in ('-r', a+':='+b)]])
        nodes.append(n); executor.add_node(n)
        return n

    def start(command):
        p = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        processes.append(p)
        return p

    def stop(p):
        os.killpg(p.pid, signal.SIGKILL); p.wait(timeout=5)

    def until(predicate, timeout=8.):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            executor.spin_once(timeout_sec=.02)
            if predicate():
                return
        raise AssertionError('DDS/transport condition timed out')

    def pump(seconds=.3):
        end = time.monotonic()+seconds
        while time.monotonic() < end:
            executor.spin_once(timeout_sec=.02)

    try:
        maps = remappings(ns)
        observer = node('fake_actuator_observer')
        final, downstream, diagnostics = [], [], []
        observer.create_subscription(Twist, t['actuator'], lambda m: final.append(axes(m)), QOS)
        observer.create_subscription(Twist, t['observed'], lambda m: downstream.append(axes(m)), QOS)
        observer.create_subscription(String, t['diagnostics'], lambda m: diagnostics.append(json.loads(m.data)), QOS)
        controller = node('fake_controller', maps['controller'])
        smoother = node('fake_smoother', maps['smoother'])
        behavior = node('fake_behavior', maps['behavior'])
        direct = node('fake_executor', maps['executor'])
        alternate = node('fake_alternative')
        cp = controller.create_publisher(Twist, 'cmd_vel', QOS)
        sp = smoother.create_publisher(Twist, 'cmd_vel_smoothed', QOS)
        smoother.create_subscription(Twist, 'cmd_vel', lambda m: sp.publish(m), QOS)
        bp = behavior.create_publisher(Twist, 'cmd_vel', QOS)
        ep = direct.create_publisher(Twist, 'cmd_vel', QOS)
        ap = alternate.create_publisher(Twist, t['alternative'], QOS)
        legacy = alternate.create_publisher(Twist, t['legacy'], QOS)
        root_legacy = alternate.create_publisher(Twist, '/cmd_vel', QOS)
        envelopes = alternate.create_publisher(String, t['envelope'], QOS)
        gate_cmd = [sys.executable, str(HERE/'gate_adapter.py'), '--namespace', ns]
        gate = start(gate_cmd)
        bridge = start(bridge_arguments(ns))
        # Independent fake actuator readback. Only transport is running, no physics.
        readback = start(['ros2','run','ros_gz_bridge','parameter_bridge',
                         t['ignition']+'@geometry_msgs/msg/Twist[ignition.msgs.Twist',
                         '--ros-args','-r',t['ignition']+':='+t['observed'],
                         '-r','__node:=b6b4_fake_actuator_readback'])
        until(lambda: diagnostics and downstream and cp.get_subscription_count() == 1
              and all(p.get_subscription_count() == 1 for p in (sp,bp,ep,ap,envelopes)))
        assert all(v == (0.,)*6 for v in final+downstream)
        assert 'STARTUP_DENY_ALL' in diagnostics[0]['reasons']
        pubs = observer.get_publishers_info_by_topic(t['actuator'])
        assert len(pubs) == 1 and pubs[0].node_name == 'traffic_motion_gate'
        subs = observer.get_subscriptions_info_by_topic(t['actuator'])
        assert any(s.node_name == 'b6b4_velocity_bridge' for s in subs)
        assert not observer.get_subscriptions_info_by_topic(t['legacy'])
        assert not observer.get_subscriptions_info_by_topic('/cmd_vel')
        for source, expected in [('controller','fake_controller'),('smoother','fake_smoother'),
                                  ('behavior','fake_behavior'),('executor','fake_executor')]:
            assert [p.node_name for p in observer.get_publishers_info_by_topic(t[source])] == [expected]
        report['graph'] = {key: dict(
            publishers=[p.node_name for p in observer.get_publishers_info_by_topic(t[key])],
            subscribers=[p.node_name for p in observer.get_subscriptions_info_by_topic(t[key])])
            for key in ('controller','smoother','behavior','executor','alternative','actuator','legacy')}
        report['single_final_publisher_and_upstream_graph'] = 'PASS (observed graph, not authorization)'

        nonzero = Twist(); nonzero.linear.x = .7; nonzero.angular.z = .3
        for name, publisher, msg in [('controller_smoother',cp,nonzero),('behavior',bp,nonzero),
                                      ('executor_zero',ep,Twist()),('alternative',ap,nonzero)]:
            at = len(diagnostics)
            publisher.publish(msg)
            source = 'smoother' if name == 'controller_smoother' else ('executor' if name == 'executor_zero' else name)
            until(lambda: any(source in d['reasons'] and 'UNBOUND_TWIST' in d['reasons'] for d in diagnostics[at:]))
            assert all(v == (0.,)*6 for v in final+downstream)
            report[name] = 'PASS: gate output zero'

        def envelope(sequence, **changes):
            data = dict(gate_session=diagnostics[-1]['session'], source='smoother', sequence=sequence,
                        context=None, velocity=[.7,0.,0.,0.,0.,.3])
            data.update(changes)
            at = len(diagnostics)
            envelopes.publish(String(data=json.dumps(data)))
            until(lambda: len(diagnostics) > at and 'STARTUP_DENY_ALL' not in diagnostics[-1]['reasons'])
            pump(.1)

        envelope(1)
        assert 'NO_LIVE_PERMIT' in diagnostics[-1]['reasons']
        envelope(1)
        until(lambda: 'OLD_OR_DUPLICATE_COMMAND' in diagnostics[-1]['reasons'])
        envelope(0)
        until(lambda: 'MALFORMED_ENVELOPE' in diagnostics[-1]['reasons'])
        envelope(2,gate_session=str(uuid4()))
        until(lambda: 'OLD_GATE_SESSION' in diagnostics[-1]['reasons'])
        report['missing_context_duplicate_old_session'] = 'PASS: rejected, all outputs zero'
        assert all(v == (0.,)*6 for v in final+downstream)

        legacy.publish(nonzero); root_legacy.publish(nonzero); pump()
        assert all(v == (0.,)*6 for v in final+downstream)
        report['legacy_ros_cmd_vel'] = 'PASS: no bridge subscription, isolated'

        # Deliberate negative authorization test against a FAKE actuator only.
        rogue = alternate.create_publisher(Twist, t['actuator'], QOS)
        until(lambda: rogue.get_subscription_count() >= 2)
        rogue.publish(nonzero)
        until(lambda: axes(nonzero) in downstream)
        assert len(observer.get_publishers_info_by_topic(t['actuator'])) == 2
        report['direct_ros_actuator_bypass'] = 'BLOCKER: unauthenticated publisher reached fake actuator'
        alternate.destroy_publisher(rogue)
        until(lambda: len(observer.get_publishers_info_by_topic(t['actuator'])) == 1)

        # Kill gate before transport injection so periodic gate zero cannot mask it.
        old_session = diagnostics[-1]['session']
        stop(gate); pump(.3)
        assert gate.poll() is not None
        report['post_kill_graph_publishers'] = len(observer.get_publishers_info_by_topic(t['actuator']))
        stopped_count = len(final); pump(.2)
        assert len(final) == stopped_count
        downstream.clear()
        injection = subprocess.run(['ign','topic','-t',t['ignition'],'-m','ignition.msgs.Twist',
                                    '-p','linear: {x: 0.9}'], capture_output=True, timeout=8)
        assert injection.returncode == 0, injection.stderr.decode()
        until(lambda: any(v[0] == .9 for v in downstream))
        report['direct_ignition_bypass'] = 'BLOCKER: direct IGN write reached fake actuator with gate absent'
        report['gate_process_loss'] = 'UNKNOWN physical stop; zero publisher absent'

        # One volatile queued envelope from the old instance cannot revive a new gate.
        envelopes.publish(String(data=json.dumps(dict(gate_session=old_session,source='smoother',sequence=99,
                                                       velocity=[.7,0.,0.,0.,0.,0.]))))
        for _ in range(8): bp.publish(nonzero)
        gate = start(gate_cmd)
        until(lambda: diagnostics[-1]['session'] != old_session)
        assert 'STARTUP_DENY_ALL' in diagnostics[-1]['reasons']
        pump(.2)
        envelope(99,gate_session=old_session)
        until(lambda: 'OLD_GATE_SESSION' in diagnostics[-1]['reasons'])
        before = len(final); cp.publish(nonzero); bp.publish(nonzero); pump(.3)
        assert final[before:] and all(v == (0.,)*6 for v in final[before:])
        report['queued_twist_and_restart'] = 'PASS: new session deny-all; old envelope rejected; raw Twist unbound'

        stop(bridge); pump(.3)
        # Fake last-command latch models the missing physical guarantee.
        seed = subprocess.run(['ign','topic','-t',t['ignition'],'-m','ignition.msgs.Twist',
                               '-p','linear: {x: 0.4}'], capture_output=True, timeout=8)
        assert seed.returncode == 0
        until(lambda: downstream[-1][0] == .4)
        before = len(downstream); before_final = len(final)
        cp.publish(nonzero); pump(.4)
        assert len(final) > before_final and all(v == (0.,)*6 for v in final[before_final:])
        assert len(downstream) == before
        assert downstream[-1][0] == .4  # fake actuator's last received target remains nonzero
        report['bridge_process_loss'] = 'BLOCKER: gate zero not delivered; fake retained target .4; physical stop UNKNOWN'
        assert gate.poll() is None and readback.poll() is None
        print('\nB6B4_REPORT='+json.dumps(report,sort_keys=True))
    finally:
        for p in reversed(processes):
            if p.poll() is None:
                os.killpg(p.pid, signal.SIGTERM)
                try: p.wait(timeout=3)
                except subprocess.TimeoutExpired: os.killpg(p.pid, signal.SIGKILL); p.wait(timeout=3)
        for n in reversed(nodes):
            executor.remove_node(n); n.destroy_node()
        executor.shutdown(); rclpy.shutdown()


def test_ros_context_fences_revoke_timeout_and_error_stay_zero():
    """Apply a synthetic B6B.3 fixture locally; no ROS health assertions are trusted."""
    from copy import deepcopy
    from types import SimpleNamespace
    from gate_adapter import TrafficGateNode
    sys.path.insert(0, str(HERE.parents[2]/'tests'))
    from test_traffic_motion_gate import fixture
    rclpy.init(args=[])
    ns = '/b6b4_test/r' + uuid4().hex
    gate = TrafficGateNode(ns)
    observer = Node('context_fixture_observer', namespace=ns)
    executor = SingleThreadedExecutor()
    executor.add_node(gate); executor.add_node(observer)
    diagnostics, outputs = [], []
    observer.create_subscription(String, gate.topics['diagnostics'], lambda m: diagnostics.append(json.loads(m.data)), QOS)
    observer.create_subscription(Twist, gate.topics['actuator'], lambda m: outputs.append(axes(m)), QOS)
    publisher = observer.create_publisher(String, gate.topics['envelope'], QOS)

    def wait(predicate):
        end = time.monotonic()+5
        while time.monotonic() < end:
            executor.spin_once(timeout_sec=.01)
            if predicate(): return
        raise AssertionError('context adapter check timed out')

    try:
        wait(lambda: publisher.get_subscription_count() == 1 and outputs)
        for field, value in [('epoch',0), ('executor_session',str(uuid4())),
                             ('fm_session',str(uuid4())), ('generation',0)]:
            g, context, _, now, _ = fixture()
            g.producer = 'b6b4_ros'; gate.model = g
            changed = deepcopy(context); changed['identity'][field] = value
            at = len(diagnostics)
            publisher.publish(String(data=json.dumps(dict(gate_session=g.local_session, source='smoother',
                sequence=1, context=changed, velocity=[.5,0.,0.,0.,0.,.2]))))
            # Fresh local gate session gives the sequence fence a fresh lifetime.
            gate.sequences.clear()
            wait(lambda: any('MOVEMENT_CONTEXT_MISMATCH' in d['reasons'] for d in diagnostics[at:]))
            assert g.binding is None
        for mode in ('health_unknown','revoke','timeout'):
            g, context, _, now, _ = fixture()
            g.producer = 'b6b4_ros'; gate.model = g; gate.sequences.clear()
            if mode == 'revoke': g.revoke()
            if mode == 'timeout': now[0] += 3.
            reason = 'STALE_OR_UNKNOWN_OBSERVATION' if mode == 'health_unknown' else 'NO_LIVE_PERMIT'
            at = len(diagnostics)
            publisher.publish(String(data=json.dumps(dict(gate_session=g.local_session, source='smoother',
                sequence=1, context=context, velocity=[.5,0.,0.,0.,0.,.2]))))
            wait(lambda: any(reason in d['reasons'] for d in diagnostics[at:]))
        at = len(outputs)
        # A model regression cannot make the ROS serializer emit nonzero.
        gate.model.filter_velocity = lambda *a, **kw: SimpleNamespace(velocity=(1.,)*6, reasons=('FAULT_INJECTION',))
        gate.raw(Twist(), 'smoother')
        wait(lambda: len(outputs) > at)
        assert all(v == (0.,)*6 for v in outputs)
        def broken(*a, **kw): raise RuntimeError('fake callback failure')
        gate.model.filter_velocity = broken
        at = len(diagnostics); gate.raw(Twist(), 'smoother')
        wait(lambda: any('ADAPTER_ERROR' in d['reasons'] for d in diagnostics[at:]))
        assert all(v == (0.,)*6 for v in outputs)
    finally:
        executor.remove_node(gate); executor.remove_node(observer)
        gate.destroy_node(); observer.destroy_node(); executor.shutdown(); rclpy.shutdown()
