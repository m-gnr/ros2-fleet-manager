"""Frame-aware comparison helpers shared by pickup recording and analysis."""
from math import cos, hypot, sin


def aligned_displacement_error(initial, stopped):
    yaw=initial['physical'][2]-initial['odom_pose'][2]
    dx=stopped['odom_pose'][0]-initial['odom_pose'][0]
    dy=stopped['odom_pose'][1]-initial['odom_pose'][1]
    return hypot(dx*cos(yaw)-dy*sin(yaw)-(stopped['physical'][0]-initial['physical'][0]),
                 dx*sin(yaw)+dy*cos(yaw)-(stopped['physical'][1]-initial['physical'][1]))
