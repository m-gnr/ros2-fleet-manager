"""Unit tests for Stage C3.3.3 configuration, world generator, and fleet.yaml alignment."""
import json
import os
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from check import load_config, prepare_world, generate_params_for_robots


class StageC333ConfigTest(unittest.TestCase):
    def setUp(self):
        os.environ['DDS_TEST_TIMEOUT_SECONDS'] = '60'
        os.environ['ROS_DOMAIN_ID'] = '47'
        os.environ['ROS_LOCALHOST_ONLY'] = '0'
        os.environ['DDS_TEST_PAYLOAD'] = 'unit-test-c3-3-3'
        os.environ['SIM_CHECK_ROLE'] = 'simulation'

    def test_load_config_and_schema(self):
        config, fleet_data, timeout = load_config()
        self.assertEqual(len(fleet_data['robots']), 2)
        r_ids = [r['id'] for r in fleet_data['robots']]
        self.assertIn('robot_1', r_ids)
        self.assertIn('robot_2', r_ids)
        self.assertTrue(Path(config['map_path']).exists())
        self.assertTrue(Path(config['nav2_template_path']).exists())
        self.assertEqual(timeout, 60.0)

    def test_prepare_world(self):
        config, fleet_data, _ = load_config()
        prepare_world(config, fleet_data)
        world_path = Path('/tmp/c3-3-3-world.sdf')
        self.assertTrue(world_path.exists())
        root = ET.fromstring(world_path.read_text())
        world = root.find('world')
        self.assertIsNotNone(world)
        self.assertEqual(world.attrib['name'], 'c3_3_3_validation_world')
        self.assertIsNotNone(world.find("model[@name='robot_1']"))
        self.assertIsNotNone(world.find("model[@name='robot_2']"))
        
        # Verify initial poses from fleet.yaml (with z=0.21 for wheel contact)
        r1 = world.find("model[@name='robot_1']")
        self.assertEqual(r1.find('pose').text, '-2.0 -0.5 0.21 0 0 0.0')
        r2 = world.find("model[@name='robot_2']")
        self.assertEqual(r2.find('pose').text, '1.0 2.5 0.21 0 0 3.1415')

    def test_generate_params(self):
        config, fleet_data, _ = load_config()
        params = generate_params_for_robots(config, fleet_data)
        self.assertIn('robot_1', params)
        self.assertIn('robot_2', params)
        for r_id in ('robot_1', 'robot_2'):
            self.assertTrue(Path(params[r_id]).exists())
            content = Path(params[r_id]).read_text()
            self.assertIn(f'{r_id}/odom', content)
            self.assertIn(f'{r_id}/base_link', content)
            self.assertIn(f'/{r_id}/scan', content)
            self.assertIn(f'/{r_id}/odom', content)
