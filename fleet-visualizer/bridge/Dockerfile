FROM ros2-fleet-simulation-c3-3-3-backend:humble-fortress

# Install the pinned universal wheel in an isolated import directory.
RUN curl -fsSL --retry 3 --max-time 120 \
      https://files.pythonhosted.org/packages/fa/a8/5b41e0da817d64113292ab1f8247140aac61cbf6cfd085d6a0fa77f4984f/websockets-15.0.1-py3-none-any.whl \
      -o /tmp/websockets.whl \
    && echo 'f7a866fbc1e97b5c617ee4116daaa09b722101d4a3c170c787450ba409f9736f  /tmp/websockets.whl' | sha256sum -c - \
    && python3 -m zipfile -e /tmp/websockets.whl /opt/visualizer-deps \
    && rm /tmp/websockets.whl

WORKDIR /app
COPY fleet_config/*.py /app/fleet_config/
COPY fleet-visualizer/bridge/*.py /app/fleet-visualizer/bridge/
ENV PYTHONPATH=/app:/opt/visualizer-deps PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["/ros_entrypoint.sh", "python3", "/app/fleet-visualizer/bridge/run.py"]
