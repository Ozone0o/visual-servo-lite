"""适配器基类."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from visual_servo_lite.models import Command

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """机器人/云台输出适配器基类.

    所有具体适配器继承此类，将 ControlCommand 转换为真实硬件指令.
    """

    @abstractmethod
    def send(self, cmd: Command) -> bool:
        """发送控制指令到硬件.

        Args:
            cmd: 控制指令.

        Returns:
            发送成功返回 True.
        """

    def close(self) -> None:
        """清理资源，子类可覆盖."""
