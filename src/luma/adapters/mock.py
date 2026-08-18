"""In-memory robot adapter for tests, demos and development."""

from __future__ import annotations

import logging

from luma.adapters.base import BaseAdapter
from luma.models import MotionCommand

logger = logging.getLogger(__name__)


class MockAdapter(BaseAdapter):
    """Record every command without touching hardware."""

    def __init__(self, name: str = "mock") -> None:
        self.name = name
        self.commands: list[MotionCommand] = []
        self.closed = False

    def send(self, command: MotionCommand) -> bool:
        self.commands.append(command)
        logger.debug(
            "[%s] yaw=%.3f pitch=%.3f",
            self.name,
            command.yaw,
            command.pitch,
        )
        return True

    @property
    def history(self) -> list[MotionCommand]:
        return self.commands

    @property
    def last_command(self) -> MotionCommand | None:
        return self.commands[-1] if self.commands else None

    @property
    def command_count(self) -> int:
        return len(self.commands)

    def close(self) -> None:
        self.closed = True


MockRobotAdapter = MockAdapter
MockPanTiltAdapter = MockAdapter


__all__ = ["MockAdapter", "MockPanTiltAdapter", "MockRobotAdapter"]
