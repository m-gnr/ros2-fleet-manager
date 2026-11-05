FROM ros2-fleet-simulation-nav2-check:humble-fortress

# The Nav2 base has no pip. Bootstrap from a verified wheel without upgrading ROS packages.
COPY requirements-c1.txt /tmp/requirements-c1.txt
RUN curl -fsSL --retry 3 --max-time 300 \
      https://files.pythonhosted.org/packages/8a/6a/19e9fe04fca059ccf770861c7d5721ab4c2aebc539889e97c7977528a53b/pip-24.0-py3-none-any.whl \
      -o /tmp/c1-pip.whl \
    && echo 'ba0d021a166865d2265246961bec0152ff124de910c5cc39f1156ce3fa7c69dc  /tmp/c1-pip.whl' | sha256sum -c - \
    && PYTHONPATH=/tmp/c1-pip.whl python3 -m pip install --no-cache-dir -r /tmp/requirements-c1.txt \
    && rm /tmp/c1-pip.whl /tmp/requirements-c1.txt
