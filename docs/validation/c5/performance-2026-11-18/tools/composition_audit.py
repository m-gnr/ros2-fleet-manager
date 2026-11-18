import time,json
from pathlib import Path
import rclpy
from rcl_interfaces.srv import GetParameters
from composition_interfaces.srv import ListNodes
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
rclpy.init();node=rclpy.create_node('c5_readonly_composition_audit');requests=[];actions={};report={}
for rid in ('robot_alpha','robot_beta','robot_gamma'):
 actions[rid]=ActionClient(node,NavigateToPose,'/'+rid+'/navigate_to_pose')
 report[rid]={}
 for service,typ,req,key in [('/'+rid+'/nav2_container/_container/list_nodes',ListNodes,ListNodes.Request(),'components'),('/'+rid+'/amcl/get_parameters',GetParameters,GetParameters.Request(names=['use_sim_time','base_frame_id','odom_frame_id','scan_topic']),'amcl'),('/'+rid+'/controller_server/get_parameters',GetParameters,GetParameters.Request(names=['use_sim_time','controller_frequency']),'controller')]:
  client=node.create_client(typ,service);requests.append((rid,key,client,req,None))
end=time.monotonic()+10
while time.monotonic()<end and requests:
 rclpy.spin_once(node,timeout_sec=.02)
 for item in requests[:]:
  rid,key,client,req,future=item
  if future is None and client.service_is_ready():
   requests.remove(item);requests.append((rid,key,client,req,client.call_async(req)))
  elif future and future.done():
   value=future.result()
   if key=='components':report[rid][key]=list(value.full_node_names)
   else:report[rid][key]=[dict(type=v.type,bool=v.bool_value,double=v.double_value,string=v.string_value) for v in value.values]
   requests.remove(item)
for rid,action in actions.items():
 report[rid]['navigate_to_pose_ready']=action.server_is_ready()
 report[rid]['tf_publishers']=[dict(name=p.node_name,namespace=p.node_namespace) for p in node.get_publishers_info_by_topic('/'+rid+'/tf')]
report['unresolved']=[dict(robot=i[0],key=i[1]) for i in requests]
Path('/evidence/composition-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));node.destroy_node();rclpy.shutdown()
