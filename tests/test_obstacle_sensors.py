"""Physical envelope, explicit configuration and common output contract regressions."""
from copy import deepcopy
from pathlib import Path
import math
from xml.etree import ElementTree as ET

import pytest
import yaml
from fleet_config import load_config
from fleet_config.loader import read_yaml
from fleet_config.warehouse_assets import generate
from fleet_config.obstacle_sensors import sensor_contracts, shape_bound, rotation

ROOT=Path(__file__).resolve().parents[1]


def bound_profile(tmp_path,change=None):
    data=read_yaml(ROOT/'config/fleet.warehouse-30x18.yaml')
    for robot in data['robots']:
        robot['obstacle_sensor_model']='compact_dual_obstacle_v1'
        robot['nav2_params_path']=str(ROOT/'config/simulation-c2-3-params.template.yaml')
    if change:change(data)
    path=tmp_path/'fleet.yaml';path.write_text(yaml.safe_dump(data,sort_keys=False));return path


def test_generated_contract_keeps_original_lidar_and_safe_3d_envelope(tmp_path):
    path=bound_profile(tmp_path);folder=tmp_path/'world';cfg=generate(path,folder,'routes')
    tree=ET.parse(folder/'warehouse.sdf')
    for robot in cfg.robots:
        model=tree.find(f'.//model[@name="{robot.id}"]')
        assert model.find('link[@name="base_link"]/collision[@name="body"]/geometry/box/size').text=='0.5 0.3 0.1'
        assert model.find('link[@name="base_link"]/sensor/pose').text=='0.0 0.0 0.15 0.0 0.0 0.0'
        params=yaml.safe_load((folder/f'nav2-{robot.id}.yaml').read_text())
        assert params['amcl']['ros__parameters']['laser_model_type']=='beam'
        assert params['amcl']['ros__parameters']['scan_topic']==robot.namespace+'/scan'
        assert params['local_costmap']['local_costmap']['ros__parameters']['robot_radius']==.3
        for sensor in sensor_contracts(cfg,robot):
            link=model.find(f'link[@name="{sensor["link"]}"]')
            assert link.find('sensor/topic').text==sensor['topic']
            for collision in link.findall('collision'):
                from fleet_config.obstacle_sensors import compose,pose
                center,matrix=compose(pose(link),pose(collision))
                radius,_=shape_bound(collision.find('geometry'),center,matrix)
                assert radius<.3
            obstacle=params['local_costmap']['local_costmap']['ros__parameters']['obstacle_layer']
            assert obstacle['obstacle_'+sensor['id']]['topic']==sensor['topic']


@pytest.mark.parametrize('bad', ['too_big','overlap','self_fov','unknown_model','beam_inside'])
def test_invalid_assembly_is_not_rendered_as_safe(tmp_path,bad):
    def change(data):
        model=data['fleet']['obstacle_sensor_models']['compact_dual_obstacle_v1']
        if bad=='too_big':model['case_size_m'][0]=.2
        elif bad=='overlap':model['mounts'][0]['position_m'][0]=.24
        elif bad=='self_fov':model['horizontal_max_rad']=math.pi
        elif bad=='unknown_model':data['robots'][0]['obstacle_sensor_model']='missing'
        elif bad=='beam_inside':model['beam_origin_m'][2]=0.
    with pytest.raises(ValueError):generate(bound_profile(tmp_path,change),tmp_path/'world','routes')


def test_assembly_is_bound_in_c5a_warehouse_profile():
    cfg=load_config(ROOT/'config/fleet.warehouse-30x18.yaml')
    assert all(robot.obstacle_sensor_model == 'compact_dual_obstacle_v1' for robot in cfg.robots)
    mounts=cfg.fleet.obstacle_sensor_models['compact_dual_obstacle_v1'].mounts
    assert [mount.position_m for mount in mounts] == [[0.15,0.23,0.0125],[-0.15,-0.23,0.0125]]
    assert [mount.yaw_rad for mount in mounts] == pytest.approx([math.pi/2,3*math.pi/2])


def test_analytical_wheel_bound_includes_full_cylinder_not_only_box_corners():
    geometry=ET.fromstring('<geometry><cylinder><radius>0.1</radius><length>0.04</length></cylinder></geometry>')
    bound,_=shape_bound(geometry,[0.,.2,-.1],rotation(math.pi/2,0,0))
    assert bound==pytest.approx(math.hypot(.22,.2))


def test_added_housings_preserve_existing_collision_inertia_drive_and_map(tmp_path):
    path=bound_profile(tmp_path);enabled=tmp_path/'enabled';generate(path,enabled,'routes')
    data=read_yaml(path)
    for robot in data['robots']:robot.pop('obstacle_sensor_model')
    path.write_text(yaml.safe_dump(data,sort_keys=False));disabled=tmp_path/'disabled';generate(path,disabled,'routes')
    a,b=ET.parse(enabled/'warehouse.sdf'),ET.parse(disabled/'warehouse.sdf')
    for robot in data['robots']:
        selector=f'.//model[@name="{robot["id"]}"]'
        left,right=a.find(selector),b.find(selector)
        for name in ['base_link','left_wheel','right_wheel','caster']:
            l,r=left.find(f'link[@name="{name}"]'),right.find(f'link[@name="{name}"]')
            assert [ET.tostring(c) for c in l.findall('collision')]==[ET.tostring(c) for c in r.findall('collision')]
            assert ET.tostring(l.find('inertial'))==ET.tostring(r.find('inertial'))
        assert ET.tostring(left.find('plugin'))==ET.tostring(right.find('plugin'))
    assert (enabled/'map.pgm').read_bytes()==(disabled/'map.pgm').read_bytes()
