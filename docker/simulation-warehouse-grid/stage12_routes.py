"""Selected route regression, including dock/park access; no station visit sweep."""
import argparse
import json
from math import cos,sin,hypot
from pathlib import Path
import time
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import ComputePathToPose
import rclpy
from rclpy.action import ActionClient
from rclpy.parameter import Parameter
from rclpy.signals import SignalHandlerOptions
from fleet_config import load_config
from inspect_route import closest


def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('profile');cli.add_argument('output',type=Path);args=cli.parse_args()
    cfg=load_config(args.profile);rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node=rclpy.create_node('stage12_route_checks',parameter_overrides=[Parameter('use_sim_time',value=True)])
    points={p.id:p.pose for p in cfg.warehouse.transfer_points}
    dock=cfg.stations.charging_stations[0];park=cfg.stations.parking_stations[0]
    rows=[]
    def wait(future):
        rclpy.spin_until_future_complete(node,future,timeout_sec=20)
        if not future.done():raise TimeoutError('route query')
        return future.result()
    def pose(p):
        msg=PoseStamped();msg.header.frame_id='map';msg.header.stamp=node.get_clock().now().to_msg()
        msg.pose.position.x=p.x;msg.pose.position.y=p.y;msg.pose.orientation.z=sin(p.yaw/2);msg.pose.orientation.w=cos(p.yaw/2)
        return msg
    try:
        for robot in cfg.robots:
            client=ActionClient(node,ComputePathToPose,robot.namespace+'/compute_path_to_pose')
            assert client.wait_for_server(timeout_sec=15)
            pickup='pick_A1' if robot.id=='robot_alpha' else 'pick_A2'
            dropoff='packing_1' if robot.id=='robot_alpha' else 'quality_1'
            legs=[('pickup',robot.initial_pose,points[pickup]),('dropoff',points[pickup],points[dropoff]),
                  ('park',points[dropoff],park.pose),('dock',points[dropoff],dock.pose)]
            for label,a,b in legs:
                begin=time.monotonic();handle=wait(client.send_goal_async(ComputePathToPose.Goal(start=pose(a),goal=pose(b),use_start=True,planner_id='GridBased')))
                row=dict(robot=robot.id,leg=label,accepted=handle.accepted)
                if handle.accepted:
                    result=wait(handle.get_result_async());path=result.result.path.poses
                    xy=[(p.pose.position.x,p.pose.position.y) for p in path]
                    clear=min((closest(a,b,list(cfg.warehouse.obstacles()))['m'] for a,b in zip(xy,xy[1:])),default=None)
                    row.update(status=result.status,planning_time_s=result.result.planning_time.sec+result.result.planning_time.nanosec/1e9,
                        length_m=sum(hypot(a[0]-b[0],a[1]-b[1]) for a,b in zip(xy,xy[1:])),points=xy,
                        minimum_center_obstacle_clearance_m=clear,minimum_circular_envelope_clearance_m=clear-.31 if clear is not None else None)
                row['wall_s']=time.monotonic()-begin;rows.append(row)
                args.output.write_text(json.dumps(rows,indent=2))
    finally:node.destroy_node();rclpy.try_shutdown()

if __name__=='__main__':main()
