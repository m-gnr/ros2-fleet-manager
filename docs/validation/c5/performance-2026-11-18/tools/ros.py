import sys,time,json,math
from pathlib import Path
import rclpy
from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy,qos_profile_sensor_data
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseStamped,PoseWithCovarianceStamped
from sensor_msgs.msg import LaserScan
from rosgraph_msgs.msg import Clock
from tf2_msgs.msg import TFMessage
rclpy.init();node=rclpy.create_node('c5_readonly_perf_probe');rows=[];end=time.monotonic()+float(sys.argv[2]);clock=[0];next_timer=time.monotonic()+.05
f=Path(sys.argv[1]).open('w')
def stamp(s):return s.sec*10**9+s.nanosec
def emit(kind,**v):
 rows.append(dict(kind=kind,mono=time.monotonic(),utc=time.time(),clock=clock[0],**v))
def ck(m):clock[0]=stamp(m.clock);emit('clock',stamp=clock[0])
node.create_subscription(Clock,'/clock',ck,QoSProfile(depth=1,reliability=ReliabilityPolicy.BEST_EFFORT))
def pose(p):
 q=p.orientation;return [p.position.x,p.position.y,math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))]
for rid in ('robot_alpha','robot_beta','robot_gamma'):
 def od(m,r=rid):emit('odom',robot=r,stamp=stamp(m.header.stamp),pose=pose(m.pose.pose),v=m.twist.twist.linear.x,w=m.twist.twist.angular.z)
 def tf(m,r=rid):
  for x in m.transforms:emit('tf',robot=r,stamp=stamp(x.header.stamp),parent=x.header.frame_id,child=x.child_frame_id)
 def phy(m,r=rid):emit('physical',robot=r,stamp=stamp(m.header.stamp),pose=pose(m.pose))
 def am(m,r=rid):emit('amcl',robot=r,stamp=stamp(m.header.stamp),pose=pose(m.pose.pose),cov=[m.pose.covariance[i] for i in (0,7,35)])
 def scan(m,r=rid):emit('scan',robot=r,stamp=stamp(m.header.stamp),count=len(m.ranges),min=m.angle_min,max=m.angle_max,step=m.angle_increment,range_max=m.range_max)
 for typ,topic,cb,qos in [(Odometry,'odom',od,qos_profile_sensor_data),(TFMessage,'tf',tf,qos_profile_sensor_data),(PoseStamped,'physical_pose',phy,qos_profile_sensor_data),(PoseWithCovarianceStamped,'amcl_pose',am,QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL)),(LaserScan,'scan',scan,qos_profile_sensor_data)]:node.create_subscription(typ,'/'+rid+'/'+topic,cb,qos)
last_flush=time.monotonic()
while time.monotonic()<end:
 rclpy.spin_once(node,timeout_sec=.01);now=time.monotonic()
 if now>=next_timer:emit('probe_loop_lag',lag_s=max(0,now-next_timer));next_timer=now+.05
 if now-last_flush>=1:
  f.writelines(json.dumps(x)+'\n' for x in rows);rows.clear();f.flush();last_flush=now
f.writelines(json.dumps(x)+'\n' for x in rows);f.close();node.destroy_node();rclpy.shutdown()
