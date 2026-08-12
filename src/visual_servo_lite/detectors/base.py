"""检测器基类."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import cv2
import numpy as np

from visual_servo_lite.models import Detection


logger = logging.getLogger(__name__)


class BaseDetector(ABC):
    """检测器抽象基类.

    所有具体检测器继承此类并实现 :meth:`detect`.
    """

    @abstractmethod
    def detect(self, frame: np.ndarray) -> Detection:
        """在单帧图像中检测目标.

        Args:
            frame: BGR 图像 (numpy ndarray, HWC).

        Returns:
            Detection 实例，包含目标位置和置信度.
        """

    @staticmethod
    def normalize_error(
        px: float, py: float,
        frame_w: int, frame_h: int,
    ) -> tuple[float, float]:
        """将像素坐标转换为归一化误差 [-1, 1].

        以图像中心为原点，右/下为正方向.

        Args:
            px: 目标 x 像素坐标.
            py: 目标 y 像素坐标.
            frame_w: 图像宽度.
            frame_h: 图像高度.

        Returns:
            (ex, ey) 归一化误差.
        """
        ex = (px - frame_w / 2.0) / (frame_w / 2.0)
        ey = (py - frame_h / 2.0) / (frame_h / 2.0)
        # 裁剪到 [-1, 1]
        ex = max(-1.0, min(1.0, ex))
        ey = max(-1.0, min(1.0, ey))
        return ex, ey
