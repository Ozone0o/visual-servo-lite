"""Generic custom robot adapter."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from luma.adapters.base import BaseAdapter
from luma.models import MotionCommand


class CustomRobotAdapter(BaseAdapter):
    """Wrap a command callback and optional close callback."""

    def __init__(
        self,
        send_command: Callable[[MotionCommand], Any],
        *,
        close: Callable[[], Any] | None = None,
    ) -> None:
        if not callable(send_command):
            raise TypeError("send_command must be callable")
        self._send_command = send_command
        self._close = close

    def send(self, command: MotionCommand) -> bool:
        result = self._send_command(command)
        return True if result is None else bool(result)

    def close(self) -> None:
        if self._close is not None:
            self._close()


CustomAdapter = CustomRobotAdapter


__all__ = ["CustomAdapter", "CustomRobotAdapter"]
