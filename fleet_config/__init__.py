"""ROS-independent fleet configuration contract."""

from .models import FleetConfig
from .loader import load_config

__all__ = ["FleetConfig", "load_config"]
