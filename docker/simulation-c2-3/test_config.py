"""Unit tests for Stage C2.3 configuration, world generator, and Nav2 params."""
import json
import os
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from check import load_config, prepare_world, generate_params_for_robot


class StageC23ConfigTest(unittest.TestCase):
    def setUp(self):
        os.environ['DDS_TEST_TIMEOUT_SECONDS'] = '60'
        os.environ['ROS_DOMAIN_ID'] = '46'
        os.environ['ROS_LOCALHOST_ONLY'] = '0'
        os.environ['DDS_TEST_PAYLOAD'] = 'unit-test-c2-3'
        os.environ['SIM_CHECK_ROLE'] = 'simulation'

    def test_load_config_and_schema(self):
        config, timeout = load_config()
        self.assertEqual(config['robot']['name'], 'robot_1')
        self.assertEqual(config['robot']['namespace'], 'robot_1')
        self.assertTrue(Path(config['map_path']).exists())
        self.assertTrue(Path(config['nav2_template_path']).exists())
        self.assertEqual(timeout, 60.0)

    def test_prepare_world(self):
        config, _ = load_config()
        prepare_world(config)
        world_path = Path('/tmp/c2-world.sdf')
        self.assertTrue(world_path.exists())
        root = ET.fromstring(world_path.read_text())
        world = root.find('world')
        self.assertIsNotNone(world)
        self.assertEqual(world.attrib['name'], 'c2_validation_world')
        self.assertIsNotNone(world.find("model[@name='robot_1']"))
        r1_lidar = world.find(".//model[@name='robot_1']//sensor[@name='lidar']")
        self.assertIsNotNone(r1_lidar)
        self.assertEqual(r1_lidar.find('topic').text, '/robot_1/scan')

    def test_generate_params(self):
        config, _ = load_config()
        p_path = generate_params_for_robot(config)
        self.assertTrue(Path(p_path).exists())
        content = Path(p_path).read_text()
        self.assertIn(config['robot']['odom_frame'], content)
        self.assertIn(config['robot']['base_frame'], content)
        self.assertIn(f'/{config["robot"]["namespace"]}/scan', content)
        self.assertIn(f'/{config["robot"]["namespace"]}/odom', content)


if __name__ == '__main__':
    unittest.main()
