unique_identifier_msgs/UUID request_id
fleet_interfaces/TrafficPermitIdentity identity
string movement_kind
string station_id
string geometry_digest
# RESERVED, DENIED or REVOKED. COMMIT is necessary but never sufficient.
string status
string reason
bool committed
bool movement_authorized
