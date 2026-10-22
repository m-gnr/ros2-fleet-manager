# Architecture

> Current interpretation: [v2.3 transition record](architecture-v2.3-transition.md) and [project context](project-context.md). Transport execution uses Fleet Manager → ExecuteTask → robot executor → Nav2. Older direct Fleet Manager → NavigateToPose descriptions are superseded for transport execution. Docker placement remains an unvalidated proposal.

- Fleet Manager owns the task queue, robot allocation, and task states.
- The backend exposes the web API and stores task history.
- The backend communicates with ROS 2 through an rclpy adapter.
- The React dashboard communicates only with the backend.
- Each robot runs Nav2 under its own namespace.
- Station definitions are stored in fleet_manager/config/stations.yaml.
