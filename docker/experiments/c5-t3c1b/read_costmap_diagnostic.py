"""Read-only cleanup-race diagnostic. No costmap clear or actuator operation."""
import json
from pathlib import Path
import signal
import sys
import time

import rclpy
from nav2_msgs.srv import GetCostmap
from rclpy.signals import SignalHandlerOptions
from fleet_config import load_config


def main():
    cfg=load_config(sys.argv[1]);output=Path(sys.argv[2]);stopped=False
    def stop(*_):
        nonlocal stopped
        stopped=True
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node=rclpy.create_node('readonly_cleanup_diagnostic');pending=[];sent=completed=0
    clients=[node.create_client(GetCostmap,r.namespace+'/'+role+'/get_costmap')
        for r in cfg.robots for role in ('local_costmap','global_costmap')]
    try:
        while not stopped:
            rclpy.spin_once(node,timeout_sec=.001)
            done=[future for future in pending if future.done()];completed+=len(done)
            pending=[future for future in pending if not future.done()]
            if (output/'health-validation.json').exists() and len(pending)<64:
                for client in clients:
                    if client.service_is_ready():pending.append(client.call_async(GetCostmap.Request()));sent+=1
    finally:
        (output/'readonly-cleanup-diagnostic.json').write_text(json.dumps(dict(sent=sent,completed=completed,
            costmap_modified=False,physical_safety_evidence=False),indent=2)+'\n')
        node.destroy_node();rclpy.try_shutdown()


if __name__=='__main__':main()
