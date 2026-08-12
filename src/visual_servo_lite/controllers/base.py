"""控制器基类."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from visual_servo_lite.models import Command, Detection

logger = logging.getLogger(__name__)


class BaseController(ABC):
    """控制器抽象基类.

    继承并实现 :meth:`compute` 以提供自定义控制策略.
    """

    @abstractmethod
    def compute(self, detection: Detection, last_command: Command | None) -> Command:
        """根据当前检测值和上一时刻指令计算新指令.

        Args:
            detection: 当前检测结果（含归一化误差）.
            last_command: 上一时刻发出的指令，可能为 None（首次调用）.

        Returns:
            新控制指令.
        """
