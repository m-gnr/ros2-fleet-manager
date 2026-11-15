# Reservation identity only. No message in this protocol enables motion.
string robot_id
string task_id
uint64 epoch
unique_identifier_msgs/UUID execute_uuid
unique_identifier_msgs/UUID child_uuid
unique_identifier_msgs/UUID executor_session
unique_identifier_msgs/UUID fm_session
unique_identifier_msgs/UUID permit_id
uint64 generation
string path_hash
string map_revision
string frame
string geometry_revision
