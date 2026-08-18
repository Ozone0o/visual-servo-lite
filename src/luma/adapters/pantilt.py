"""Pan/tilt adapter for serial, SDK or function-based transports."""

from __future__ import annotations

from typing import Any

from luma.adapters.base import BaseAdapter
from luma.models import MotionCommand


class PanTiltAdapter(BaseAdapter):
    """Translate a Luma command to a pan/tilt transport.

    ``transport`` may be a callable accepting ``(yaw, pitch)`` or a device
    exposing ``set_angles(yaw, pitch)`` / ``send(command)``.
    """

    def __init__(self, transport: Any, *, clamp: bool = False) -> None:
        self.transport = transport
        self.clamp = clamp

    def send(self, command: MotionCommand) -> bool:
        if callable(self.transport):
            try:
                result = self.transport(command.yaw, command.pitch)
            except TypeError:
                result = self.transport(command)
        elif callable(getattr(self.transport, "set_angles", None)):
            result = self.transport.set_angles(command.yaw, command.pitch)
        elif callable(getattr(self.transport, "send", None)):
            result = self.transport.send(command)
        else:
            raise TypeError("PanTiltAdapter transport must be callable or expose set_angles/send")
        return True if result is None else bool(result)


__all__ = ["PanTiltAdapter"]
