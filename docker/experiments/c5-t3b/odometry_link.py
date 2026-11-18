"""Test-only downstream link. Forward real odometry unchanged, never restamp."""
import signal
import sys
from fleet_config import load_config


class OdometryLink:
    def __init__(self,node,config):
        from nav_msgs.msg import Odometry
        from rclpy.qos import qos_profile_sensor_data
        self.publishers,self.subscriptions=[],[]
        for robot in config.robots:
            publisher=node.create_publisher(Odometry,robot.namespace+'/odom',1)
            self.publishers.append(publisher)
            self.subscriptions.append(node.create_subscription(Odometry,robot.namespace+'/t3b_raw_odom',
                lambda message,publisher=publisher:publisher.publish(message),qos_profile_sensor_data))


def main():
    import rclpy
    from rclpy.signals import SignalHandlerOptions
    config=load_config(sys.argv[1]);rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node=rclpy.create_node('t3b_odometry_link');link=OdometryLink(node,config)
    stopping=False
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    try:
        while not stopping:rclpy.spin_once(node,timeout_sec=.05)
    finally:node.destroy_node();rclpy.try_shutdown()


if __name__=='__main__':main()
