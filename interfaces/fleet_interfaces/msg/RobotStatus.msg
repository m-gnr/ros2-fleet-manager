std_msgs/Header header
uint64 status_seq
unique_identifier_msgs/UUID publisher_session_id
string robot_id
uint64 current_epoch
uint8 state
uint8 current_phase
bool is_loaded
# Pose header stamp is the measurement time. Zero means no measured pose yet.
geometry_msgs/PoseStamped pose
float32 battery_soc_percent
float64 battery_energy_wh
# Battery measurement time. Zero means unavailable for assignment.
builtin_interfaces/Time battery_stamp
string current_task_id
string dock_station_id
string charging_station_id
# Stamped Gazebo model pose for physical dock departure. Zero stamp means unavailable.
geometry_msgs/PoseStamped physical_pose

uint8 STATE_IDLE = 1
uint8 STATE_EXECUTING_TASK = 2
uint8 STATE_CHARGING = 3
uint8 STATE_RETURNING_TO_CHARGE = 4
uint8 STATE_RETURNING_TO_PARK = 5
uint8 STATE_ERROR = 6

uint8 PHASE_NONE = 0
uint8 PHASE_MOVING_TO_PICKUP = 1
uint8 PHASE_LOADING = 2
uint8 PHASE_MOVING_TO_DROPOFF = 3
uint8 PHASE_UNLOADING = 4
