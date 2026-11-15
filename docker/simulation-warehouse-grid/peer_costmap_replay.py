"""Recompute stationary peer body hits from recorded ROS messages; no ROS nodes."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from geometry_msgs.msg import TransformStamped
from rclpy.duration import Duration
from rclpy.time import Time
from rosidl_runtime_py.set_message import set_message_fields
from tf2_ros import Buffer, TransformException


def ns(stamp):
    return stamp['sec']*1_000_000_000+stamp['nanosec']


def rotate(q, p):
    x, y, z, w = (q[k] for k in ('x', 'y', 'z', 'w'))
    # Quaternion rotation, preserving the real roll/pitch as well as yaw.
    uv = [y*p[2]-z*p[1], z*p[0]-x*p[2], x*p[1]-y*p[0]]
    uuv = [y*uv[2]-z*uv[1], z*uv[0]-x*uv[2], x*uv[1]-y*uv[0]]
    return [a+2*(w*b+c) for a,b,c in zip(p,uv,uuv)]


def apply(transform, point):
    return [a+transform['translation'][k] for a,k in zip(rotate(transform['rotation'],point),('x','y','z'))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw', type=Path)
    parser.add_argument('world', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.raw.open()]
    tree = ET.parse(args.world)
    poses, grids, health = defaultdict(list), defaultdict(list), defaultdict(list)
    scans = []
    buffer = Buffer(cache_time=Duration(seconds=3600))
    for row in rows:
        kind, msg = row['kind'], row['message']
        if kind in ('TF', 'TF_STATIC'):
            for item in msg['transforms']:
                transform = TransformStamped()
                set_message_fields(transform, item)
                if kind == 'TF_STATIC':
                    buffer.set_transform_static(transform, 'recorded_ros')
                else:
                    buffer.set_transform(transform, 'recorded_ros')
        elif kind == 'SCAN':
            scans.append(row)
        elif kind == 'POSE':
            poses[row['key']].append(msg)
        elif kind == 'GRID':
            grids[row['key']].append(msg)
        elif kind == 'HEALTH':
            health[row['key']].append(msg)
    robot_ids = sorted(poses)
    if len(robot_ids) != 2:
        raise ValueError('Exactly two physical pose streams required')
    counts = {rid: Counter() for rid in robot_ids}
    errors, matches = [], []
    half = {}
    for rid in robot_ids:
        size = tree.find(f'.//model[@name="{rid}"]/link[@name="base_link"]/collision[@name="body"]/geometry/box/size')
        half[rid] = [float(v)/2 for v in size.text.split()]
        poses[rid].sort(key=lambda p: ns(p['header']['stamp']))
        grids[rid].sort(key=lambda p: ns(p['header']['stamp']))
    for row in scans:
        rid, topic = row['key']
        peer = next(r for r in robot_ids if r != rid)
        scan = row['message']; stamp = ns(scan['header']['stamp']); c = counts[rid]
        c['scan_messages'] += 1
        physical = min(poses[peer], key=lambda p: abs(ns(p['header']['stamp'])-stamp))
        if abs(ns(physical['header']['stamp'])-stamp) > 100_000_000:
            c['physical_pose_unavailable'] += 1
            continue
        frame = rid+'/odom'
        transforms = []
        for stage, source in [('scan',scan['header']['frame_id']), ('peer',physical['header']['frame_id'])]:
            try:
                tf = buffer.lookup_transform(frame,source,Time(nanoseconds=stamp))
                transforms.append(dict(translation={k:getattr(tf.transform.translation,k) for k in ('x','y','z')},
                                       rotation={k:getattr(tf.transform.rotation,k) for k in ('x','y','z','w')}))
                c[stage+'_tf_success'] += 1
            except TransformException as exc:
                c[stage+'_tf_error'] += 1
                errors.append(dict(robot=rid,topic=topic,stamp_ns=stamp,stage=stage,error=str(exc)))
                transforms.append(None)
        if transforms[0] is None:
            continue
        own = min(poses[rid], key=lambda p: abs(ns(p['header']['stamp'])-stamp))
        if abs(ns(own['header']['stamp'])-stamp) > 100_000_000:
            c['physical_pose_unavailable'] += 1
            continue
        extrinsic = buffer.lookup_transform(rid+'/base_link',scan['header']['frame_id'],Time(nanoseconds=stamp))
        sensor_to_base = dict(translation={k:getattr(extrinsic.transform.translation,k) for k in ('x','y','z')},
                             rotation={k:getattr(extrinsic.transform.rotation,k) for k in ('x','y','z','w')})
        own_to_world = dict(translation=own['pose']['position'],rotation=own['pose']['orientation'])
        used = [h for h in health[rid] if any(t == topic and u and ns(s) == stamp
                for t,u,s in zip(h['topics'],h['used'],h['measurement_stamps']))]
        processed = min((ns(h['processed_at']) for h in used), default=None)
        grid = next((g for g in grids[rid] if processed is not None and
                     processed <= ns(g['header']['stamp']) <= stamp+1_000_000_000),None)
        peer_pose = physical['pose']
        center = [peer_pose['position'][k] for k in ('x','y','z')]
        body_hits = marked = 0
        for i,distance in enumerate(scan['ranges']):
            if not math.isfinite(distance) or not scan['range_min'] <= distance <= scan['range_max']:
                continue
            angle = scan['angle_min']+i*scan['angle_increment']
            endpoint = apply(transforms[0],[distance*math.cos(angle),distance*math.sin(angle),0.])
            # Physical body attribution uses measured Gazebo poses and the real
            # sensor extrinsic. AMCL's planar map<-odom is not a 3-D truth frame.
            world_endpoint = apply(own_to_world,apply(sensor_to_base,
                                   [distance*math.cos(angle),distance*math.sin(angle),0.]))
            delta_world = [v-w for v,w in zip(world_endpoint,center)]
            q = peer_pose['orientation']; inverse = {k:(v if k == 'w' else -v) for k,v in q.items()}
            local = rotate(inverse,delta_world)
            # Require a real 3-D box surface hit (2 cm sensor tolerance).
            if not (all(abs(v)<=h+0.02 for v,h in zip(local,half[peer])) and
                    min(abs(abs(v)-h) for v,h in zip(local,half[peer]))<=0.02):
                continue
            body_hits += 1
            if grid is None:
                continue
            origin = grid['info']['origin']; q = origin['orientation']
            inverse = {k:(v if k == 'w' else -v) for k,v in q.items()}
            point = rotate(inverse,[v-origin['position'][k] for v,k in zip(endpoint,('x','y','z'))])
            col, rr = [math.floor(v/grid['info']['resolution']) for v in point[:2]]
            inside = 0 <= col < grid['info']['width'] and 0 <= rr < grid['info']['height']
            cost = grid['data'][rr*grid['info']['width']+col] if inside else None
            marked += int(cost == 100)
            matches.append(dict(robot=rid,topic=topic,scan_stamp_ns=stamp,beam=i,range_m=distance,
                physical_stamp_ns=ns(physical['header']['stamp']),body_local_xyz=local,
                buffer_processed_ns=processed,grid_stamp_ns=ns(grid['header']['stamp']),
                endpoint_world_xyz=world_endpoint,endpoint_odom_xyz=endpoint,cell=[col,rr],cost=cost))
        c['peer_hit_points'] += body_hits
        c['peer_hit_scans'] += int(body_hits>0)
        c['buffer_used_peer_scans'] += int(body_hits>0 and bool(used))
        c['grid_matched_peer_scans'] += int(body_hits>0 and grid is not None)
        c['lethal_matched_points'] += marked
        c['marked_peer_scans'] += int(marked>0)
    result = dict(counters=counts,tf_errors=errors,
                  per_robot={r:'PASS' if counts[r]['marked_peer_scans'] else 'FAIL' for r in robot_ids},
                  clearing='NOT TESTED')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    args.output.with_suffix('.matches.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in matches))
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
