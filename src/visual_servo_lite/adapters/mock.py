"""Mock Pan-Tilt 适配器.

用于无硬件环境下的测试和演示.
将指令打印到日志，不发送任何真实信号.
"""

from __future__ import annotations

import logging

from visual_servo_lite.adapters.base import BaseAdapter
from visual_servo_lite.models import Command

logger = logging.getLogger(__name__)


class MockPanTiltAdapter(BaseAdapter):
    """模拟二维云台适配器.

    仅记录收到的指令，用于测试和 Demo.
    """

    def __init__(self, name: str = "mock_pantilt") -> None:
        self.name = name
        self._history: list[Command] = []
        logger.info("MockPanTiltAdapter 初始化: name=%s", name)

    def send(self, cmd: Command) -> bool:
        """记录指令并返回成功.

        Args:
            cmd: 控制指令.

        Returns:
            始终返回 True.
        """
        self._history.append(cmd)
        logger.debug("[%s] yaw=%.2f, pitch=%.2f", self.name, cmd.yaw, cmd.pitch)
        return True

    @property
    def command_count(self) -> int:
        return len(self._history)

    def close(self) -> None:
        logger.info("[%s] 共发送 %d 条指令", self.name, self.command_count)
