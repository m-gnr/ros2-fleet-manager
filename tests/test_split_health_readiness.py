"""Synthetic scene-readiness predicates, not actual robot health evidence."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('fixture_readiness',Path('docker/experiments/c5-t3c1b/fixture_readiness.py'))
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


def ready():
    return dict(source_ages={k:dict(current=True,source_stamp_ns=20) for k in fixture.REQUIRED},
        reasons=list(fixture.PRE_TASK_UNKNOWN),movement_eligible=False,ownership_release=False)


def test_pre_task_unknown_is_not_an_authority_or_a_reused_ready_flag():
    result=ready();assert fixture.scene_ready(result,20)
    assert not fixture.scene_ready(result,21)
    assert not fixture.scene_ready({},20)
    result['reasons'].append('INVALID_HEALTH:Symmetric PSD planar covariance required')
    assert not fixture.scene_ready(result,20)


@pytest.mark.parametrize('stream',fixture.REQUIRED)
def test_each_real_source_must_be_current_after_initialization(stream):
    result=ready();result['source_ages'][stream]['current']=False
    assert not fixture.scene_ready(result,20)


@pytest.mark.parametrize('reason',['CLOCK_REWOUND','SOURCE_ORDER:odometry','LIFECYCLE_NOT_ACTIVE:controller_server',
    'OBSERVATION_UNUSED_OR_OLD:local','SOURCE_CHANGED:tf'])
def test_scene_readiness_cannot_filter_invalid_or_conflicting_evidence(reason):
    result=ready();result['reasons'].append(reason)
    assert not fixture.scene_ready(result,20)
