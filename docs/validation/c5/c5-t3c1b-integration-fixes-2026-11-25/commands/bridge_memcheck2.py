# Standalone memory diagnostic, not FM permit/health or physical safety evidence.
import os,time,json,subprocess,signal
from pathlib import Path
import rclpy
from std_msgs.msg import String
out=Path('/evidence/bridge-memcheck2');out.mkdir(exist_ok=False)
rclpy.init();node=rclpy.create_node('heap_probe');pubs=[node.create_publisher(String,'/c5_heap_probe_'+str(i),10) for i in range(6)];pub=pubs[0]
bridge='/opt/ros/humble/lib/ros_gz_bridge/parameter_bridge'
with (out/'bridge.log').open('w') as log:
 child=subprocess.Popen(['valgrind','--error-exitcode=91','--leak-check=no','--track-origins=yes','--num-callers=30',
  '--log-file='+str(out/'memcheck.log'),bridge,*['/c5_heap_probe_'+str(i)+'@std_msgs/msg/String]ignition.msgs.StringMsg' for i in range(6)]],stdout=log,stderr=subprocess.STDOUT)
try:
 deadline=time.monotonic()+60.
 while pub.get_subscription_count()==0 and time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.01)
 assert pub.get_subscription_count()>0
 for i in range(400):
  for p in pubs:p.publish(String(data='metadata-probe-'+str(i)+'x'*32768))
  rclpy.spin_once(node,timeout_sec=.002)
 child.send_signal(signal.SIGINT)
 deadline=time.monotonic()+20.
 while child.poll() is None and time.monotonic()<deadline:
  pub.publish(String(data='metadata-probe-final'));rclpy.spin_once(node,timeout_sec=.01)
 child.wait(timeout=3.)
finally:
 if child.poll() is None:child.send_signal(signal.SIGINT);child.wait(timeout=5.)
 (out/'result.json').write_text(json.dumps(dict(returncode=child.returncode)))
 node.destroy_node();rclpy.try_shutdown()
