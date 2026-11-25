"""Synthetic telemetry edge cases only; no braking or source qualification."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import pytest
import sqlite3

spec = importlib.util.spec_from_file_location('preparation', Path('docker/experiments/c5-t3c2a/measurements.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def sample(**changes):
    return dict(robot_id='r', writer_boot='boot', writer_steady_ns=100, sim_ns=50,
        post_completed_physics_updates=10, pre_selected_joint_targets=[0., 0.],
        post_actual_velocity_known=True, post_actual_joint_velocity=[.01, -.02],
        post_actual_body_velocity=[.03, .04, 0., 0., 0., -.1], post_world_position=[1., 2., 0.], **changes)


def test_observed_gaps_are_not_upper_bounds_and_world_velocity_is_not_body_velocity():
    a = sample(); b = deepcopy(a)
    b.update(writer_steady_ns=400, sim_ns=150, post_completed_physics_updates=30)
    result = module.sample_inventory([a, b])
    assert result['observed_max_sample_gap']['post_completed_physics_updates'] == 20
    assert result['observed_max_world_xy_speed_m_s'] == pytest.approx(.05)
    assert result['velocity_frame'] == 'WORLD' and result['timestamp_phase'] == 'POST_UPDATE'
    assert result['pre_joint_write_timestamp_ns'] is None and result['body_frame_signed_speed_m_s'] is None
    assert not result['qualified_worst_case_bound'] and not result['braking_calibration']


@pytest.mark.parametrize('change', [dict(robot_id='other'), dict(writer_boot='restart')])
def test_sessions_or_robots_are_never_combined(change):
    a = sample(); b = deepcopy(a); b.update(change)
    with pytest.raises(ValueError, match='combine'): module.sample_inventory([a, b])


@pytest.mark.parametrize('field', ['writer_steady_ns', 'sim_ns', 'post_completed_physics_updates'])
def test_stalled_or_reordered_time_is_not_physics_progress(field):
    a = sample(); b = deepcopy(a)
    b.update(writer_steady_ns=101, sim_ns=51, post_completed_physics_updates=11); b[field] = a[field]
    with pytest.raises(ValueError, match='progressing'): module.sample_inventory([a, b])


@pytest.mark.parametrize('field', ['post_actual_joint_velocity', 'post_actual_body_velocity', 'post_world_position'])
def test_invalid_physical_readbacks_are_not_evidence(field):
    a = sample(); a[field][0] = float('nan')
    with pytest.raises(ValueError, match='readback'): module.sample_inventory([a])


def test_missing_or_unknown_readback_is_not_zero_speed():
    with pytest.raises(ValueError, match='Missing'): module.sample_inventory([])
    a = sample(); a['post_actual_velocity_known'] = False
    with pytest.raises(ValueError, match='Unknown'): module.sample_inventory([a])


def test_nonzero_target_cannot_be_admitted_by_preparation():
    a = sample(); a['pre_selected_joint_targets'] = [.01, 0.]
    with pytest.raises(ValueError, match='zero-only'): module.sample_inventory([a])


def test_output_cannot_modify_historical_archive(tmp_path):
    with pytest.raises(ValueError, match='historical'):
        module.save_review(tmp_path, tmp_path / 'new.json')
    assert not list(tmp_path.iterdir())


def test_closed_wal_backup_is_read_without_sidecars_or_write_access(tmp_path):
    path = tmp_path / 'backup.sqlite3'
    db = sqlite3.connect(path)
    db.execute('pragma journal_mode=wal')
    db.execute('create table evidence (value integer)')
    db.execute('insert into evidence values (7)'); db.commit(); db.close()
    original = path.read_bytes(); files = sorted(tmp_path.iterdir())
    read = module.archive_connection('file:' + str(path) + '?mode=ro', uri=True)
    try:
        assert read.execute('select value from evidence').fetchone() == (7,)
        with pytest.raises(sqlite3.OperationalError): read.execute('insert into evidence values (8)')
    finally: read.close()
    assert path.read_bytes() == original and sorted(tmp_path.iterdir()) == files
    wal = Path(str(path) + '-wal'); wal.write_bytes(b'nonempty synthetic WAL')
    with pytest.raises(ValueError, match='WAL'):
        module.archive_connection('file:' + str(path) + '?mode=ro', uri=True)
