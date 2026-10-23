"""Reject malformed lidar configuration before starting Gazebo."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import check


class ConfigTests(unittest.TestCase):
    def test_valid_and_world(self):
        base, config, _ = check.load_config()
        check.prepare_world(base, config)
        world = check.ET.parse('/tmp/lidar-world.sdf')
        self.assertEqual(world.find('.//sensor').get('type'), 'gpu_lidar')
        self.assertEqual(int(world.find('.//sensor/lidar/scan/horizontal/samples').text), config['sensor']['samples'])
        self.assertIsNotNone(world.find(".//model[@name='lidar_wall']/link/visual"))

    def test_invalid(self):
        original = json.loads(Path('/config/simulation-lidar-check.json').read_text())
        cases = []
        for group, key, value in [('sensor','samples',0), ('sensor','update_rate_hz',float('nan')),
                                  ('sensor','max_range_m',0.01), ('sensor','min_angle_rad',1),
                                  ('wall','size_m',[0,1,1]), ('sensor','pose',[0,0,0,0,0,1])]:
            bad = copy.deepcopy(original)
            bad[group][key] = value
            cases.append(bad)
        missing = copy.deepcopy(original)
        del missing['render']
        cases.append(missing)
        extra = copy.deepcopy(original)
        extra['extra'] = 1
        cases.append(extra)
        read = Path.read_text
        for config in cases:
            with self.subTest(config=config):
                def patched(path, *args, **kwargs):
                    if str(path) == '/config/simulation-lidar-check.json':
                        return json.dumps(config)
                    return read(path, *args, **kwargs)
                with patch.object(Path, 'read_text', patched):
                    with self.assertRaises((ValueError, check.jsonschema.ValidationError)):
                        check.load_config()


if __name__ == '__main__':
    unittest.main()
