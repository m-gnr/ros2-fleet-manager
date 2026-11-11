"""Independent timing/frame regression cases for the physical experiment analysis."""
import importlib.util
from math import pi
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('stage12_analyze',Path(__file__).resolve().parents[1]/'docker/simulation-warehouse-grid/stage12_analyze.py')
metrics=importlib.util.module_from_spec(spec);spec.loader.exec_module(metrics)


def test_interpolation_uses_short_yaw_arc():
    actual,bracket=metrics.at([(0,[0,0,pi-.1]),(20_000_000,[2,4,-pi+.1])],10_000_000)
    assert actual==pytest.approx([1,2,pi]);assert bracket==20_000_000


def test_large_time_gap_has_no_fabricated_pose():
    assert metrics.at([(0,[0,0,0]),(200_000_000,[2,0,0])],100_000_000)==(None,None)


def test_no_extrapolation():
    assert metrics.at([(20,[0,0,0]),(40,[2,0,0])],10)==(None,None)


def test_exact_stamp_is_preserved():
    assert metrics.at([(20,[1,2,3])],20)==([1,2,3],0)


def test_generated_costmaps_cover_physical_collision_envelope(tmp_path):
    """Use physical primitives, rather than nominal Burger visual dimensions."""
    from math import hypot
    from xml.etree import ElementTree as ET
    import yaml
    from fleet_config.warehouse_assets import generate
    profile=Path(__file__).resolve().parents[1]/'config/fleet.warehouse-30x18.yaml'
    cfg=generate(profile,tmp_path,'routes')
    world=ET.parse(tmp_path/'warehouse.sdf').getroot()
    for robot in cfg.robots:
        model=world.find(f".//model[@name='{robot.id}']")
        body=list(map(float,model.find("link[@name='base_link']/collision/geometry/box/size").text.split()))
        envelope=hypot(body[0]/2,body[1]/2)
        for name in ('left_wheel','right_wheel'):
            link=model.find(f"link[@name='{name}']")
            center=list(map(float,link.find('pose').text.split()))
            radius=float(link.find('collision/geometry/cylinder/radius').text)
            width=float(link.find('collision/geometry/cylinder/length').text)
            envelope=max(envelope,hypot(abs(center[0])+radius,abs(center[1])+width/2))
        caster=model.find("link[@name='caster']")
        origin=list(map(float,caster.find('pose').text.split()))
        for collision in caster.findall('collision'):
            offset=list(map(float,collision.findtext('pose',default='0 0 0 0 0 0').split()))
            radius=float(collision.find('geometry/sphere/radius').text)
            envelope=max(envelope,hypot(origin[0]+offset[0],origin[1]+offset[1])+radius)
        for layer in ('local_costmap','global_costmap'):
            params=yaml.safe_load((tmp_path/f'nav2-{robot.id}.yaml').read_text())[layer][layer]['ros__parameters']
            assert params['robot_radius']>=envelope


def test_raycast_measures_surface_not_occupied_volume(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'docker/simulation-warehouse-grid'))
    from stage12_scan_analysis import raycast
    box=[[(2,3),(-1,1),(0,2)]]
    assert raycast([0,0,1],[1,0,0],box)==pytest.approx(2)
    assert raycast([0,0,1],[-1,0,0],box)==float('inf')
    assert raycast([0,2,1],[1,0,0],box)==float('inf')


def test_sensor_offset_rotation_includes_physical_tilt(monkeypatch):
    from math import sqrt
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'docker/simulation-warehouse-grid'))
    from stage12_scan_analysis import rotate
    assert rotate(dict(x=0,y=sqrt(.5),z=0,w=sqrt(.5)),[0,0,.15])==pytest.approx([.15,0,0],abs=1e-12)
