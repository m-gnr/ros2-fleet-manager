"""Normalize physical evidence through stamped TF without renewing its measurement time."""
from copy import deepcopy
import math
from xml.etree import ElementTree

PHYSICAL_EVIDENCE_MAX_AGE_NS = 300_000_000


def map_physical_pose(message, buffer, now_ns):
    stamp=message.header.stamp
    sample_ns=stamp.sec*10**9+stamp.nanosec
    frame=message.header.frame_id
    p,q=message.pose.position,message.pose.orientation
    if (not frame or not 0<=stamp.nanosec<10**9 or sample_ns<=0
            or not 0<=now_ns-sample_ns<=PHYSICAL_EVIDENCE_MAX_AGE_NS
            or not all(math.isfinite(v) for v in (p.x,p.y,p.z,q.x,q.y,q.z,q.w))):
        return None
    if frame=='map':
        return deepcopy(message)
    if buffer is None:
        return None
    from rclpy.time import Time
    from tf2_ros import TransformException
    from tf2_geometry_msgs import do_transform_pose
    try:
        transform=buffer.lookup_transform('map',frame,Time.from_msg(stamp))
    except TransformException:
        return None
    measured=transform.header.stamp
    transform_ns=measured.sec*10**9+measured.nanosec
    t,r=transform.transform.translation,transform.transform.rotation
    if (transform.header.frame_id!='map' or transform.child_frame_id!=frame
            or not 0<=measured.nanosec<10**9 or transform_ns<0
            or (transform_ns and not 0<=sample_ns-transform_ns<=PHYSICAL_EVIDENCE_MAX_AGE_NS)
            or not all(math.isfinite(v) for v in (t.x,t.y,t.z,r.x,r.y,r.z,r.w))
            or sum(v*v for v in (r.x,r.y,r.z,r.w))<=0):
        return None
    result=deepcopy(message)
    result.pose=do_transform_pose(message.pose,transform)
    result.header.frame_id='map'
    # Static TF has stamp zero. It must never replace the pose's real sample stamp.
    position,orientation=result.pose.position,result.pose.orientation
    if not all(math.isfinite(v) for v in (position.x,position.y,position.z,orientation.x,orientation.y,orientation.z,orientation.w)):
        return None
    # Humble tf2_geometry_msgs leaves numpy scalars in message fields. The domain
    # deliberately accepts native finite numbers only; do not weaken that gate.
    for field,axes in ((position,'xyz'),(orientation,'xyzw')):
        for axis in axes:setattr(field,axis,float(getattr(field,axis)))
    return result


def generated_world_transform(world_path):
    """World/map generators use the same origin and axes; publish that explicit static edge."""
    world=ElementTree.parse(world_path).getroot().find('world')
    frame=world.get('name') if world is not None else None
    if not frame or frame=='map':
        raise ValueError('Generated SDF must have a distinct physical world frame')
    from geometry_msgs.msg import TransformStamped
    transform=TransformStamped()
    transform.header.frame_id='map'
    transform.child_frame_id=frame
    transform.transform.rotation.w=1.
    return transform
