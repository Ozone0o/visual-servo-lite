"""Optional ROS2 ``Twist`` adapter.

Importing :mod:`luma.adapters` does not require ROS2.  A ROS2 installation is
needed only when this adapter is instantiated.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from luma.adapters.base import BaseAdapter
from luma.models import MotionCommand


class ROS2Adapter(BaseAdapter):
    """Publish explicit Twist commands on a ROS2 node.

    ``MotionCommand.yaw`` and ``pitch`` are pan/tilt channels, while Twist
    angular fields are transport-specific velocity channels. The adapter does
    not silently add those units together. Callers using pan/tilt must supply
    an explicit ``command_to_message`` conversion with the device's units.
    """

    def __init__(
        self,
        node: Any,
        topic: str = "/luma/cmd_vel",
        *,
        qos: int = 10,
        publisher: Any | None = None,
        command_to_message: Callable[[MotionCommand], Any] | None = None,
    ) -> None:
        self.node = node
        if publisher is None:
            try:
                from geometry_msgs.msg import Twist
            except ImportError as exc:
                raise ImportError(
                    "ROS2Adapter requires a sourced ROS2 environment with geometry_msgs available"
                ) from exc
            publisher = node.create_publisher(Twist, topic, qos)
        self.publisher = publisher
        self.command_to_message = command_to_message
        self.topic = topic

    def send(self, command: MotionCommand) -> bool:
        if self.command_to_message is not None:
            message = self.command_to_message(command)
        else:
            message = self._default_message(command)
        self.publisher.publish(message)
        return True

    @staticmethod
    def _default_message(command: MotionCommand) -> Any:
        from geometry_msgs.msg import Twist

        if command.yaw or command.pitch:
            raise ValueError(
                "ROS2Adapter requires command_to_message for yaw/pitch pan-tilt commands"
            )
        message = Twist()
        message.linear.x = command.linear_x
        message.linear.y = command.linear_y
        message.linear.z = command.linear_z
        message.angular.x = command.angular_x
        message.angular.y = command.angular_y
        message.angular.z = command.angular_z
        return message


Ros2Adapter = ROS2Adapter


__all__ = ["ROS2Adapter", "Ros2Adapter"]
