"""ROS2 adapter contract tests that do not require a ROS installation."""

from __future__ import annotations

import sys
import types

import pytest

from luma.adapters.ros2 import ROS2Adapter
from luma.models import MotionCommand


class _Vector:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class _Twist:
    def __init__(self) -> None:
        self.linear = _Vector()
        self.angular = _Vector()


def test_default_twist_mapping_does_not_mix_pan_tilt_channels(monkeypatch) -> None:
    message_module = types.ModuleType("geometry_msgs.msg")
    message_module.Twist = _Twist
    package_module = types.ModuleType("geometry_msgs")
    package_module.msg = message_module
    monkeypatch.setitem(sys.modules, "geometry_msgs", package_module)
    monkeypatch.setitem(sys.modules, "geometry_msgs.msg", message_module)

    message = ROS2Adapter._default_message(MotionCommand(angular_z=0.25))

    assert message.angular.z == 0.25
    with pytest.raises(ValueError, match="command_to_message"):
        ROS2Adapter._default_message(MotionCommand(yaw=1.0))
