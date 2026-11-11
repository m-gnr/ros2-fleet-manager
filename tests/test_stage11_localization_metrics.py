"""Guard against comparing displacements in different odometry/world frames."""
from math import pi
from pathlib import Path
import pytest


@pytest.mark.parametrize('initial,stopped,expected',[
    ({'physical':[5,7,pi/2],'odom_pose':[0,0,0]},
     {'physical':[5,9,pi/2],'odom_pose':[2,0,0]},0),
    ({'physical':[5,7,pi/2],'odom_pose':[0,0,0]},
     {'physical':[5,8.8,pi/2],'odom_pose':[2,0,0]},.2),
    ({'physical':[5,7,0],'odom_pose':[10,12,0]},
     {'physical':[6,9,0],'odom_pose':[11,14,0]},0),
])
def test_frame_aligned_odometry_displacement(monkeypatch,initial,stopped,expected):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'docker/simulation-warehouse-grid'))
    from stage11_metrics import aligned_displacement_error
    assert aligned_displacement_error(initial,stopped)==pytest.approx(expected,abs=1e-12)
