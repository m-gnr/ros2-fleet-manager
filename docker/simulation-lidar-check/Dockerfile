FROM ros2-fleet-simulation-check:humble-fortress
RUN apt-get update && apt-get install -y --no-install-recommends \
    libignition-rendering6-ogre2 \
    && rm -rf /var/lib/apt/lists/*
COPY docker/simulation-lidar-check/*.py /opt/simulation-lidar-check/
CMD ["python3", "/opt/simulation-lidar-check/check.py"]
