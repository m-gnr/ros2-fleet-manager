"""Add physical, instrumented charging pads to the Fortress test world."""

from xml.etree import ElementTree as ET


def install_docks(world_path, docks, robots):
    tree = ET.parse(world_path)
    world = tree.getroot().find("world")
    ET.SubElement(world, "plugin", {
        "filename": "ignition-gazebo-contact-system",
        "name": "ignition::gazebo::systems::Contact",
    })
    for robot in robots:
        model = world.find(f"model[@name='{robot.id}']")
        model.append(ET.fromstring("""
<plugin filename="ignition-gazebo-pose-publisher-system" name="ignition::gazebo::systems::PosePublisher">
  <publish_model_pose>true</publish_model_pose>
  <publish_nested_model_pose>true</publish_nested_model_pose>
  <publish_link_pose>false</publish_link_pose>
  <use_pose_vector_msg>false</use_pose_vector_msg>
  <update_frequency>30</update_frequency>
</plugin>
"""))
    for dock in docks:
        width = 2 * dock.tolerance_radius
        p = dock.pose
        # A 1 mm raised, passive pad. The product charge radius is checked independently.
        world.append(ET.fromstring(f"""
<model name="{dock.id}">
  <pose>{p.x} {p.y} 0 0 0 {p.yaw}</pose>
  <static>true</static>
  <link name="pad">
    <collision name="surface">
      <pose>0 0 -0.004 0 0 0</pose>
      <geometry><box><size>{width} {width} 0.01</size></box></geometry>
    </collision>
    <sensor name="contact" type="contact">
      <always_on>true</always_on>
      <contact><collision>surface</collision><topic>/dock/{dock.id}/contacts</topic></contact>
    </sensor>
  </link>
</model>
"""))
    tree.write(world_path)


def dock_bridge_arguments(docks, robots):
    contacts = [f"/dock/{dock.id}/contacts@ros_gz_interfaces/msg/Contacts[ignition.msgs.Contacts"
                for dock in docks]
    poses = [f"/model/{robot.id}/pose@geometry_msgs/msg/PoseStamped[ignition.msgs.Pose" for robot in robots]
    remaps = [arg for robot in robots for arg in ("-r", f"/model/{robot.id}/pose:={robot.namespace}/physical_pose")]
    return [*contacts, *poses, "--ros-args", *remaps]
