"""Add read-only planner/costmap/feedback diagnostics to the timestamped probe."""
import json
from pathlib import Path
import time
import sys
from collections import Counter
import rclpy
from rosidl_runtime_py.convert import message_to_ordereddict as convert
from nav_msgs.msg import OccupancyGrid, Path as NavPath
from geometry_msgs.msg import PolygonStamped
from dwb_msgs.msg import LocalPlanEvaluation
import stage12_probe as base


def main():
    output = Path(sys.argv[2])
    stream = (output/'diagnostics.jsonl').open('w')
    create = rclpy.create_node
    last = {}
    def create_node(*args, **kwargs):
        node = create(*args, **kwargs)
        def emit(kind, msg):
            now = time.monotonic()
            if kind == 'CANDIDATES' and now-last.get(kind, 0) < .5:
                return
            last[kind] = now
            packet = convert(msg)
            if kind == 'CANDIDATES':
                counts = Counter()
                for traj in packet['twists']:
                    if traj['total'] < 0:
                        bad = [s['name'] for s in traj['scores'] if s['raw_score'] < 0]
                        counts.update(bad or ['rejected_unspecified'])
                best = packet['best_index']
                packet = dict(header=packet['header'],count=len(packet['twists']),
                    rejected=sum(t['total'] < 0 for t in packet['twists']), reasons=dict(counts),
                    best=packet['twists'][best] if best < len(packet['twists']) else None,
                    rejected_examples=[t for t in packet['twists'] if t['total'] < 0][:3])
            stream.write(json.dumps(dict(kind=kind,monotonic=now,
                sim_ns=node.get_clock().now().nanoseconds,message=packet))+'\n')
            stream.flush()
        for kind, suffix, typ in (
            ('LOCAL_COSTMAP','local_costmap/costmap',OccupancyGrid),
            ('GLOBAL_COSTMAP','global_costmap/costmap',OccupancyGrid),
            ('GLOBAL_PLAN','plan',NavPath),('LOCAL_PLAN','local_plan',NavPath),
            ('FOOTPRINT','local_costmap/published_footprint',PolygonStamped),
            ('CANDIDATES','evaluation',LocalPlanEvaluation)):
            node.create_subscription(typ,'/robot_beta/'+suffix,
                lambda msg,kind=kind:emit(kind,msg),10)
        node._stage13_emit = emit
        return node
    original_client = base.ActionClient
    class ObservedClient(original_client):
        def __init__(self,node,*args,**kwargs):
            super().__init__(node,*args,**kwargs)
            self.observer_node=node
        def send_goal_async(self,goal,*args,**kwargs):
            kwargs['feedback_callback']=lambda msg:self.observer_node._stage13_emit('NAV_FEEDBACK',msg)
            return super().send_goal_async(goal,*args,**kwargs)
    rclpy.create_node=create_node
    base.ActionClient=ObservedClient
    try:
        base.main()
    finally:
        stream.close()

if __name__ == '__main__':main()
