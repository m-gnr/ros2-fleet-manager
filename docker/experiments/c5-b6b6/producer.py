"""Disposable fake gate: receives already signed fixture packets over stdin."""
import sys
import time
import rclpy
from std_msgs.msg import String
rclpy.init()
n = rclpy.create_node('b6b6_fake_gate')
p = n.create_publisher(String, sys.argv[1], 1)
while p.get_subscription_count() == 0:
    time.sleep(.01)
print('READY', flush=True)
for line in sys.stdin:
    p.publish(String(data=line.strip()))
n.destroy_node()
rclpy.shutdown()
