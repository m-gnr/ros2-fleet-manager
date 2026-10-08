# Architecture

- Fleet Manager owns the task queue, robot allocation, and task states.
- The backend exposes the web API and stores task history.
- The backend communicates with ROS 2 through an rclpy adapter.
- The React dashboard communicates only with the backend.
- Each robot runs Nav2 under its own namespace.
- Station definitions are stored in fleet_manager/config/stations.yaml.