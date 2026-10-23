"""Unit tests for Stage B3 multi-robot configuration, world generator, and params."""
import json
import os
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from check import load_config, prepare_world, generate_params_for_robot


class StageB3ConfigTest(unittest.TestCase):
    def setUp(self):
        os.environ['DDS_TEST_TIMEOUT_SECONDS'] = '60'
        os.environ['ROS_DOMAIN_ID'] = '45'
        os.environ['ROS_LOCALHOST_ONLY'] = '0'
        os.environ['DDS_TEST_PAYLOAD'] = 'unit-test-b3'
        os.environ['SIM_CHECK_ROLE'] = 'simulation'

    def test_load_config_and_schema(self):
        config, timeout = load_config()
        self.assertEqual(len(config['robots']), 2)
        self.assertEqual(config['robots'][0]['name'], 'robot_1')
        self.assertEqual(config['robots'][1]['name'], 'robot_2')
        self.assertTrue(Path(config['map_path']).exists())
        self.assertTrue(Path(config['nav2_template_path']).exists())
        self.assertEqual(timeout, 60.0)

    def test_prepare_world(self):
        config, _ = load_config()
        prepare_world(config)
        world_path = Path('/tmp/b3-world.sdf')
        self.assertTrue(world_path.exists())
        root = ET.fromstring(world_path.read_text())
        world = root.find('world')
        self.assertIsNotNone(world)
        self.assertEqual(world.attrib['name'], 'b3_validation_world')
        self.assertIsNotNone(world.find("model[@name='robot_1']"))
        self.assertIsNotNone(world.find("model[@name='robot_2']"))
        r1_lidar = world.find(".//model[@name='robot_1']//sensor[@name='lidar']")
        r2_lidar = world.find(".//model[@name='robot_2']//sensor[@name='lidar']")
        self.assertIsNotNone(r1_lidar)
        self.assertIsNotNone(r2_lidar)
        self.assertEqual(r1_lidar.find('topic').text, '/robot_1/scan')
        self.assertEqual(r2_lidar.find('topic').text, '/robot_2/scan')

    def test_generate_params(self):
        config, _ = load_config()
        for r in config['robots']:
            p_path = generate_params_for_robot(config, r)
            self.assertTrue(Path(p_path).exists())
            content = Path(p_path).read_text()
            self.assertIn(r['odom_frame'], content)
            self.assertIn(r['base_frame'], content)
            self.assertIn(f'/{r["namespace"]}/scan', content)
            self.assertIn(f'/{r["namespace"]}/odom', content)


if __name__ == '__main__':
    unittest.main()
