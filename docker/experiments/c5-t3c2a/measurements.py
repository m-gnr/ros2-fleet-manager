"""Offline preparation only: inspect existing 1B evidence, never command a robot."""
import argparse
from collections import defaultdict
from dataclasses import asdict
import importlib.util
import hashlib
import json
import math
from pathlib import Path
import sqlite3
from types import SimpleNamespace

from backend.fleet_manager.domain.stop_envelope import StopInputs

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('prior_health_audit', ROOT / 'docker/experiments/c5-t3c1b/audit.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)


def archive_connection(database, *, uri):
    """Closed backups only; mode=ro alone may create WAL/SHM sidecars."""
    if uri is not True or not database.startswith('file:') or not database.endswith('?mode=ro'):
        raise ValueError('Explicit read-only archive URI required')
    path = Path(database[5:-len('?mode=ro')])
    wal = Path(str(path) + '-wal')
    if wal.exists() and wal.stat().st_size:
        raise ValueError('Live/nonempty WAL is not an immutable backup')
    return sqlite3.connect(database + '&immutable=1', uri=True)


# This privately loaded audit instance reuses all 1B checks without modifying
# its source or the sqlite3 module used by the product/other callers.
prior.base.sqlite3 = SimpleNamespace(connect=archive_connection)


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def sample_inventory(samples):
    """Observed post-physics samples, not a continuous trace or a physical bound."""
    if not samples:
        raise ValueError('Missing writer samples')
    identity = {(s['robot_id'], s['writer_boot']) for s in samples}
    if len(identity) != 1:
        raise ValueError('Do not combine robot/writer boots')
    known = []
    for s in samples:
        if s['pre_selected_joint_targets'] != [0., 0.]:
            raise ValueError('This preparation accepts only zero-only evidence')
        if type(s['post_actual_velocity_known']) is not bool:
            raise ValueError('Explicit readback availability required')
        for field in ('writer_steady_ns', 'sim_ns', 'post_completed_physics_updates'):
            if type(s[field]) is not int or s[field] < 0:
                raise ValueError('Invalid frame/time counter')
        if s['post_actual_velocity_known']:
            for key, size in (('post_actual_joint_velocity', 2), ('post_actual_body_velocity', 6),
                              ('post_world_position', 3)):
                if len(s[key]) != size or not all(number(v) for v in s[key]):
                    raise ValueError('Missing or nonfinite post-physics readback')
            known.append(s)
    if not known:
        raise ValueError('Unknown readback is not zero velocity')
    deltas = {}
    for field in ('writer_steady_ns', 'sim_ns', 'post_completed_physics_updates'):
        gaps = [b[field] - a[field] for a, b in zip(samples, samples[1:])]
        if any(v <= 0 for v in gaps):
            raise ValueError('Non-progressing writer samples')
        deltas[field] = max(gaps) if gaps else None
    return dict(robot_id=samples[0]['robot_id'], writer_boot=samples[0]['writer_boot'],
                samples=len(samples), known_readbacks=len(known), unknown_readbacks=len(samples)-len(known),
                observed_max_sample_gap=deltas,
                observed_max_joint_speed_rad_s=max(abs(v) for s in known for v in s['post_actual_joint_velocity']),
                observed_max_world_xy_speed_m_s=max(math.hypot(*s['post_actual_body_velocity'][:2]) for s in known),
                observed_max_world_yaw_rate_rad_s=max(abs(s['post_actual_body_velocity'][5]) for s in known),
                joint_scope='first left and first right joint; names require SDF join',
                sample_scope='whole writer boot, not a single task or permit',
                velocity_frame='WORLD', timestamp_phase='POST_UPDATE',
                pre_joint_write_timestamp_ns=None, body_frame_signed_speed_m_s=None,
                qualified_worst_case_bound=False, braking_calibration=False)


def review(archive):
    """Reuse the complete 1B audit; the resulting measurements remain historical."""
    archive = Path(archive)
    root, matrix = archive / 'live', archive / 'commands/matrix.tsv'
    manifest = json.loads((archive / 'manifest.json').read_text())
    hashes = {str(archive / e['path']): e['archive_sha256'] for e in manifest}
    databases = list(root.glob('*/fleet.sqlite3'))
    for database in databases:
        if hashlib.sha256(database.read_bytes()).hexdigest() != hashes[str(database)]:
            raise ValueError('Immutable backup must match its archive manifest')
    audit = prior.audit(root, matrix)  # No filtering or replacement of failed cases.
    if not audit['acceptance_complete'] or len(audit['cases']) != 14:
        raise ValueError('Complete stationary 1B evidence required')
    load = lambda path: json.loads(prior.base.read(path))
    cases = []
    for entry in audit['cases']:
        path = root / entry['run']
        binding, before = load(path / 'writer-committed-binding.json'), load(path / 'health-before.json')
        body = json.loads(binding['committed_transfer']['body'])
        groups = defaultdict(list)
        for line in prior.base.read(path / 'writer.jsonl').splitlines():
            s = json.loads(line)
            groups[s['robot_id'], s['writer_boot']].append(s)
        cases.append(dict(run=entry['run'], identity=binding['committed_transfer']['identity'],
            native_session=binding['selection']['native_session'], writer_boot=binding['selection']['writer_boot'],
            command_sha256=binding['selection']['command_sha256'],
            raw_command_times=dict(fm_issued_at=body['issued_at'],
                native_verified_steady_ns=binding['native_status']['verified_steady_ns'],
                writer_post_steady_ns=binding['selection']['writer_steady_ns']),
            clock_alignment='UNQUALIFIED; raw stamps are not subtracted across processes',
            command_origin_to_joint_write_delay_sec=None,
            nav2_velocity_source_identity='UNKNOWN; no native Nav2 velocity payload',
            original_source_ages=before['health']['source_ages'],
            original_health_sources=before['packet']['body']['sources'],
            source_measurement_ids_are_not_authenticated_publishers=True,
            writer_groups=[sample_inventory(values) for values in groups.values()],
            historical_fault_physics=dict(before=entry['physics_before'], during=entry['physics_while_fault']),
            physical_applied=False, physical_stop='UNKNOWN', ownership_release=False))
    for database in databases:
        if hashlib.sha256(database.read_bytes()).hexdigest() != hashes[str(database)]:
            raise ValueError('Archive DB changed during review')
    return dict(scope='T3C_2A_OFFLINE_PREPARATION', preparation_status='PASS',
        evidence_kind='HISTORICAL_1B_STATIONARY_REAUDIT', new_live_runs=0,
        historical_cases=len(cases), historical_audit_result=audit['result'],
        t3c2b_motion_transition='BLOCKED', movement_authorized=False, ownership_release=False,
        stop_envelope=dict(status='UNBOUNDED', qualified=False, tube=None,
                           unmeasured_inputs=asdict(StopInputs())),
        gates=dict(stationary_zero_chain='PASS', phase_and_source_inventory='PASS',
            authenticated_nav2_velocity_source='BLOCKED', mapped_clock_error_bound='BLOCKED',
            full_rate_pre_and_post_joint_trace='BLOCKED', measured_braking_and_error_bounds='BLOCKED',
            approved_single_robot_motion_fixture='BLOCKED', physics_writer_fault_scope_approved='BLOCKED'),
        cases=cases)


def save_review(archive, output):
    archive, output = Path(archive).resolve(), Path(output).resolve()
    if output.is_relative_to(archive):
        raise ValueError('Do not write into historical evidence')
    result = review(archive)
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = save_review(args.archive, args.output)
    print('PASS offline preparation; T3C-2B BLOCKED; UNBOUNDED; no new live run')
