FROM ros:humble-ros-base-jammy@sha256:566b87e6dfc48392189a9c32e594e84060fa9948de93b04e536f39475a1f6963

RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-humble-rmw-cyclonedds-cpp \
    libignition-gazebo6 \
    ignition-tools \
    && rm -rf /var/lib/apt/lists/*

COPY probe.py /opt/dds-check/probe.py
ENV PYTHONUNBUFFERED=1
CMD ["python3", "/opt/dds-check/probe.py"]
