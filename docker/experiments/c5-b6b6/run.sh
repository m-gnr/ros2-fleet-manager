#!/usr/bin/env bash
set -euo pipefail
cd /repo
c++ -std=c++17 -fPIC -shared docker/experiments/c5-b6b6/lease.cc -o /tmp/b6b6-lease.so
set +u
source /opt/ros/humble/setup.bash
set -u
export PYTHONPATH=/repo/docker/experiments/c5-b6b6:${PYTHONPATH:-} PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=186 IGN_PARTITION=b6b6_zero_only
/usr/bin/python3 -m pytest -p no:cacheprovider -q -s docker/experiments/c5-b6b6/test_authorization.py
