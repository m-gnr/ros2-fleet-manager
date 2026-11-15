"""Validate the recorded stationary peer evidence without starting ROS/Gazebo."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

root = Path(sys.argv[1])
output = Path(__file__).parent
proof = json.loads((root/'replay.json').read_text())
matches = [json.loads(line) for line in (root/'replay.matches.jsonl').open()]
raw = [json.loads(line) for line in (root/'peer.raw.jsonl').open()]
assert proof['per_robot'] == {'robot_alpha':'PASS','robot_beta':'PASS'}
assert len(matches) == 3276
assert all(m['cost'] == 100 and m['scan_stamp_ns'] <= m['buffer_processed_ns'] <=
           m['grid_stamp_ns'] <= m['scan_stamp_ns']+10**9 for m in matches)
assert all(abs(m['scan_stamp_ns']-m['physical_stamp_ns']) <= 100_000_000 for m in matches)
# The actual recorded static edge explicitly gives the generated map/world axes.
assert any(t['header']['frame_id'] == 'map' and t['child_frame_id'] == 'warehouse_grid'
           and t['transform'] == dict(translation=dict(x=0.,y=0.,z=0.),rotation=dict(x=0.,y=0.,z=0.,w=1.))
           for r in raw if r['kind']=='TF_STATIC' for t in r['message']['transforms'])
occupancy = json.loads((root/'live/generated/occupancy.json').read_text())
cells = [value for value,n in occupancy['runs'] for _ in range(n)]
static = Counter()
for m in matches:
    x,y = m['endpoint_world_xyz'][:2]
    col = math.floor((x-occupancy['origin'][0])/occupancy['resolution'])
    row = math.floor((y-occupancy['origin'][1])/occupancy['resolution'])
    static[cells[row*occupancy['width']+col]] += 1
assert set(static) == {0}
rows = [json.loads(line) for line in (root/'live/ros.jsonl').open()]
assert not any(r['kind']=='UNSAFE_CONTACT' for r in rows)
physical = {}
for rid in proof['per_robot']:
    ps = [r['message']['pose']['position'] for r in rows if r['kind']=='PHYSICAL_POSE' and r['robot']==rid]
    od = [r['message']['twist']['twist'] for r in rows if r['kind']=='ODOMETRY' and r['robot']==rid]
    physical[rid] = dict(max_xy_displacement_m=max(math.hypot(p['x']-ps[0]['x'],p['y']-ps[0]['y']) for p in ps),
        max_linear_speed_m_s=max(math.sqrt(sum(v*v for v in m['linear'].values())) for m in od),
        max_angular_speed_rad_s=max(abs(m['angular']['z']) for m in od))
    assert physical[rid]['max_xy_displacement_m'] < 1e-5
(output/'physical-evidence.json').write_text(json.dumps(dict(robots=physical,unsafe_contact_events=0,
    static_occupancy_at_peer_points=dict(static)),indent=2)+'\n')
manifest = []
for src in ('peer.raw.jsonl','replay.matches.jsonl','live/ros.jsonl','live/generated/warehouse.sdf','live/generated/occupancy.json'):
    p = root/src
    manifest.append(dict(path=str(p),size=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(output/'raw-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(output/'sample-matches.jsonl').write_text(''.join(json.dumps(next(m for m in matches if m['robot']==r))+'\n' for r in proof['per_robot']))
(output/'replay.json').write_text(json.dumps(proof,indent=2)+'\n')
message = ('PASS: 3276 lethal matches, original scan <= used buffer processed <= grid <= scan+1s; '
           'physical pose delta <=100ms; recorded map/world static edge; free static map; '
           'stationary robots; 0 unsafe contact events.\n')
(output/'evidence-checks.txt').write_text(message)
print(message,end='')
