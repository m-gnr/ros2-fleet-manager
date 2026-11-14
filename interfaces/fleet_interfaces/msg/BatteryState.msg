# Energy estimate for one simulated robot at the Gazebo clock stamp.
string robot_id
# Generated once per Battery Simulator process.
unique_identifier_msgs/UUID publisher_session_id
float64 battery_energy_wh
float32 battery_soc_percent
float64 battery_capacity_wh
bool is_charging
string charging_station_id
# Non-empty only for the single sample following an authenticated set_soc control.
string control_request_id
builtin_interfaces/Time battery_stamp
