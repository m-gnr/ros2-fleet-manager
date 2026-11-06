FROM ros2-fleet-simulation-c3-3-3-backend:humble-fortress

COPY requirements-c5.txt requirements-c5-test.txt /tmp/
RUN curl -fsSL --retry 3 --max-time 300 \
      https://files.pythonhosted.org/packages/8a/6a/19e9fe04fca059ccf770861c7d5721ab4c2aebc539889e97c7977528a53b/pip-24.0-py3-none-any.whl \
      -o /tmp/c5-pip.whl \
    && echo 'ba0d021a166865d2265246961bec0152ff124de910c5cc39f1156ce3fa7c69dc  /tmp/c5-pip.whl' | sha256sum -c - \
    && PYTHONPATH=/tmp/c5-pip.whl python3 -m pip install --no-cache-dir -r /tmp/requirements-c5-test.txt \
    && rm /tmp/c5-pip.whl /tmp/requirements-c5*.txt
