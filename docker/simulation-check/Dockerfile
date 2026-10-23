FROM ros2-fleet-dds-check:humble-fortress
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-humble-ros-gz-bridge python3-jsonschema \
    libignition-gazebo6-plugins libignition-physics5-dartsim \
    && rm -rf /var/lib/apt/lists/*
COPY docker/simulation-check /opt/simulation-check
CMD ["python3", "/opt/simulation-check/check.py"]
