"""Reject invalid configuration before launching any simulation process."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import jsonschema
from check import load_config


class ConfigValidationTest(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(Path('/config/simulation-check.json').read_text())
        self.schema = Path('/config/simulation-check.schema.json').read_text()

    def validate(self, config):
        with patch.object(Path, 'read_text', side_effect=[json.dumps(config), self.schema]):
            return load_config()

    def test_valid(self):
        self.validate(self.config)

    def test_invalid_config(self):
        cases = []
        for key, value in [('namespace', '../other'), ('initial_pose', [0, 0]), ('name', '')]:
            config = copy.deepcopy(self.config)
            config['robot'][key] = value
            cases.append(config)
        config = copy.deepcopy(self.config)
        config['probe']['drive_seconds'] = -1
        cases.append(config)
        config = copy.deepcopy(self.config)
        config['probe']['maximum_distance_m'] = config['probe']['minimum_distance_m']
        cases.append(config)
        config = copy.deepcopy(self.config)
        config['robot']['initial_pose'][0] = float('nan')
        cases.append(config)
        config = copy.deepcopy(self.config)
        config['unexpected'] = True
        cases.append(config)
        for config in cases:
            with self.subTest(config=config), self.assertRaises((ValueError, jsonschema.ValidationError)):
                self.validate(config)

    def test_invalid_environment(self):
        for key, value in [('ROS_DOMAIN_ID', '233'), ('ROS_LOCALHOST_ONLY', '1'),
                           ('DDS_TEST_TIMEOUT_SECONDS', 'nan'), ('DDS_TEST_PAYLOAD', ''),
                           ('SIM_CHECK_ROLE', 'unknown')]:
            with self.subTest(key=key), patch.dict(os.environ, {key: value}), self.assertRaises(ValueError):
                self.validate(self.config)


if __name__ == '__main__':
    unittest.main()
