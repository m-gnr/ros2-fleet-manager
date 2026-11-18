# Experimental BT action-client transaction evidence; never motion/stop/release authority.
uint8 ACCEPTED=1
uint8 INVALIDATED=2
uint8 TERMINAL=3
unique_identifier_msgs/UUID context_id
unique_identifier_msgs/UUID nav_goal_uuid
unique_identifier_msgs/UUID executor_session_id
unique_identifier_msgs/UUID observer_session_id
unique_identifier_msgs/UUID child_goal_uuid
uint64 observation_seq
builtin_interfaces/Time stamp
uint8 kind
int8 terminal_status
string reason
nav_msgs/Path path
