"""Unit tests for Stage B AMCL verification configuration and world generator."""
import json
import os
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from check import load_config, prepare_world


class StageBAMCLConfigTest(unittest.TestCase):
    def setUp(self):
        os.environ['DDS_TEST_TIMEOUT_SECONDS'] = '30'
        os.environ['ROS_DOMAIN_ID'] = '42'
        os.environ['ROS_LOCALHOST_ONLY'] = '0'
        os.environ['DDS_TEST_PAYLOAD'] = 'unit-test'
        os.environ['SIM_CHECK_ROLE'] = 'simulation'

    def test_load_config_and_schema(self):
        config, timeout = load_config()
        self.assertEqual(config['robot']['name'], 'validation_robot')
        self.assertTrue(Path(config['map_path']).exists())
        self.assertTrue(Path(config['nav2_parameters']).exists())
        self.assertEqual(timeout, 30.0)
        self.assertEqual(config['initial_offset']['x_offset_m'], 0.5)
        self.assertEqual(config['initial_offset']['y_offset_m'], 0.3)
        self.assertEqual(config['check']['amcl_tolerance_m'], 0.4)

    def test_prepare_world(self):
        config, _ = load_config()
        prepare_world(config)
        world_path = Path('/tmp/amcl-world.sdf')
        self.assertTrue(world_path.exists())
        root = ET.fromstring(world_path.read_text())
        world = root.find('world')
        self.assertIsNotNone(world)
        self.assertEqual(world.attrib['name'], 'amcl_validation_world')
        self.assertIsNotNone(world.find("model[@name='north_wall']"))
        self.assertIsNotNone(world.find("model[@name='validation_robot']"))
        lidar = world.find(".//sensor[@name='lidar']")
        self.assertIsNotNone(lidar)
        self.assertEqual(lidar.find('update_rate').text, str(config['sensor']['update_rate_hz']))


if __name__ == '__main__':
    unittest.main()
