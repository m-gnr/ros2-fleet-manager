# Separate B2 dependency image; preserve the successful B1 image.
FROM ros2-fleet-simulation-lidar-check:humble-fortress
RUN apt-get update -o APT::Update::Error-Mode=any && apt-get install -y --no-install-recommends \
    ros-humble-navigation2=1.1.20-1jammy.20260916.170645 \
    ros-humble-nav2-bringup=1.1.20-1jammy.20260916.171610 \
    && dpkg --audit \
    && rm -rf /var/lib/apt/lists/*
