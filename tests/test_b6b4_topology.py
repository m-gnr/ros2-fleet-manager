"""Targeted source invariance and test-only topology checks; no runtime robot."""
import hashlib
import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'docker/experiments/c5-b6b4'))
from topology import topology, remappings, bridge_arguments


def test_default_sources_unchanged():
    baseline = json.loads((ROOT/'docs/validation/c5/c5-b6b4-topology-2026-11-15/baseline.json').read_text())
    for name, expected in baseline.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected, name
    assert 'motion_envelope: null' in (ROOT/'config/fleet.warehouse-30x18.yaml').read_text()


def test_wiring_is_upstream_only_and_bridge_has_one_velocity_input():
    ns = '/b6b4_test/check'
    t, maps = topology(ns), remappings(ns)
    assert maps['controller'] == [('cmd_vel',t['controller'])]
    assert maps['smoother'] == [('cmd_vel',t['controller']),('cmd_vel_smoothed',t['smoother'])]
    for producer in maps:
        assert all(b != t['actuator'] for _, b in maps[producer])
    args = bridge_arguments(ns)
    assert sum('@geometry_msgs/msg/Twist]' in v for v in args) == 1
    assert t['ignition']+':='+t['actuator'] in args
    assert all(t['legacy'] not in v for v in args)


@pytest.mark.parametrize('namespace',['/robot_alpha','/','/b6b4_test/../robot','/b6b4_test/r/cmd_vel'])
def test_product_namespaces_rejected(namespace):
    with pytest.raises(ValueError):
        topology(namespace)
