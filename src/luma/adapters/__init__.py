"""Built-in robot adapters."""

from luma.adapters.base import BaseAdapter, RobotAdapter
from luma.adapters.custom import CustomAdapter, CustomRobotAdapter
from luma.adapters.mock import MockAdapter, MockPanTiltAdapter, MockRobotAdapter
from luma.adapters.pantilt import PanTiltAdapter
from luma.adapters.ros2 import ROS2Adapter, Ros2Adapter
from luma.registry import adapter_registry, register_adapter

adapter_registry.register("mock", MockAdapter)
adapter_registry.register("pantilt", PanTiltAdapter)
adapter_registry.register("ros2", ROS2Adapter)
adapter_registry.register("custom", CustomRobotAdapter)

__all__ = [
    "BaseAdapter",
    "CustomAdapter",
    "CustomRobotAdapter",
    "MockAdapter",
    "MockPanTiltAdapter",
    "MockRobotAdapter",
    "PanTiltAdapter",
    "ROS2Adapter",
    "RobotAdapter",
    "Ros2Adapter",
    "adapter_registry",
    "register_adapter",
]
