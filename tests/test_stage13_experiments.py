"""Guard experiment isolation and timestamp/frame diagnostic correctness."""
import importlib.util
from pathlib import Path
import sys
from math import pi
import pytest

ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/'docker/simulation-warehouse-grid'

@pytest.fixture
def analysis(monkeypatch):
    monkeypatch.syspath_prepend(str(TOOLS))
    import stage13_analyze
    return stage13_analyze


def test_transform_roundtrip_and_wrapped_heading(analysis):
    a=[3,-4,pi-.01];b=[2,1,.04]
    assert analysis.inverse(a,analysis.compose(a,b))==pytest.approx(b)


def test_sparse_map_correction_is_bracketed_not_extrapolated(analysis):
    rows=[(1,[0,0,pi-.1]),(2_000_000_001,[2,4,-pi+.1])]
    assert analysis.interpolate(rows,1_000_000_001) is None
    assert analysis.interpolate(rows,1_000_000_001,True)==pytest.approx([1,2,pi])
    assert analysis.interpolate(rows,0,True) is None
    assert analysis.interpolate(rows,3_000_000_000,True) is None


def test_grid_sampling_respects_rotated_origin_and_outside(analysis):
    msg=dict(info=dict(origin=dict(position=dict(x=2,y=3,z=0),orientation=dict(x=0,y=0,z=2**-.5,w=2**-.5)),
        resolution=1.,width=2,height=2),data=[10,20,30,40])
    assert analysis.cell(msg,[1.5,3.5,0])==10
    assert analysis.cell(msg,[1.5,4.5,0])==20
    assert analysis.cell(msg,[2.5,3.5,0]) is None


def test_subtractive_landmark_cannot_narrow_aisles_or_open_rack_passage(monkeypatch):
    monkeypatch.syspath_prepend(str(TOOLS))
    import stage13_server as server
    from fleet_config import load_config
    layout=load_config(ROOT/'config/fleet.warehouse-30x18.yaml').warehouse
    original=next(b for n,b,h in server.original_obstacles(layout) if n=='rack_A2')
    parts=[b for n,b,h in server.landmark_obstacles(layout) if n.startswith('rack_A2_')]
    assert len(parts)==2
    for b in parts:
        assert original.contains(b.x_min,b.y_min) and original.contains(b.x_max,b.y_max)
    # An uninterrupted south strip preserves the service face and blocks through travel.
    assert parts[0].x_min==original.x_min and parts[0].x_max==original.x_max
    assert parts[0].y_min==original.y_min and parts[0].y_max-parts[0].y_min>=.5


def test_landmark_changes_lidar_visible_surface_and_shared_map(monkeypatch,tmp_path):
    monkeypatch.syspath_prepend(str(TOOLS))
    import stage13_server as server
    from stage12_scan_analysis import raycast
    from fleet_config import load_config
    from fleet_config.occupancy import raster
    from fleet_config.warehouse import WarehouseLayout
    layout=load_config(ROOT/'config/fleet.warehouse-30x18.yaml').warehouse
    original=list(server.original_obstacles(layout))
    revised=list(server.landmark_obstacles(layout))
    boxes=lambda solids:[[(b.x_min,b.x_max),(b.y_min,b.y_max),(0,h)] for _,b,h in solids]
    assert raycast([5.25,7.75,.35],[-1.5,-.5,0],boxes(revised))>raycast([5.25,7.75,.35],[-1.5,-.5,0],boxes(original))
    _,before=raster(layout)
    monkeypatch.setattr(WarehouseLayout,'obstacles',server.landmark_obstacles)
    _,after=raster(layout)
    assert before!=after
    # The shared map generator removes occupied cells only; it adds no obstacles.
    assert all(a<=b for a,b in zip(after,before,strict=True))


def test_amcl_variant_preserves_controller_and_footprints(monkeypatch,tmp_path):
    monkeypatch.syspath_prepend(str(TOOLS))
    import stage13_server as server
    import yaml
    profile=ROOT/'config/fleet.warehouse-30x18.yaml'
    monkeypatch.setenv('STAGE13_OVERRIDE','{}')
    server.generate(profile,tmp_path/'a','routes')
    monkeypatch.setenv('STAGE13_OVERRIDE','{"amcl":{"alpha4":0.002}}')
    server.generate(profile,tmp_path/'b','routes')
    for robot in ('robot_alpha','robot_beta'):
        a=yaml.safe_load((tmp_path/'a'/f'nav2-{robot}.yaml').read_text())
        b=yaml.safe_load((tmp_path/'b'/f'nav2-{robot}.yaml').read_text())
        b['amcl']['ros__parameters']['alpha4']=a['amcl']['ros__parameters']['alpha4']
        # map path is output-directory-specific, not an experimental variable.
        b['map_server']['ros__parameters']['yaml_filename']=a['map_server']['ros__parameters']['yaml_filename']
        assert a==b
    assert (tmp_path/'a/warehouse.sdf').read_bytes()==(tmp_path/'b/warehouse.sdf').read_bytes()
    assert (tmp_path/'a/map.pgm').read_bytes()==(tmp_path/'b/map.pgm').read_bytes()
