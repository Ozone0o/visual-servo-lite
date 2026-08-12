"""基于颜色的 OpenCV 检测器.

使用 HSV 色彩空间中的颜色阈值定位目标.
第一版默认检测器，不依赖任何深度学习库.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np

from visual_servo_lite.detectors.base import BaseDetector
from visual_servo_lite.models import Detection

logger = logging.getLogger(__name__)


class ColorDetector(BaseDetector):
    """颜色阈值检测器.

    用户在 HSV 范围中指定一个色区，检测区域内颜色像素的重心作为目标位置.
    """

    def __init__(
        self,
        lower_h: int = 0,
        lower_s: int = 100,
        lower_v: int = 100,
        upper_h: int = 20,
        upper_s: int = 255,
        upper_v: int = 255,
        min_area: int = 100,
    ) -> None:
        """初始化颜色检测器.

        Args:
            lower_h: HSV 最小 hue (0-180).
            lower_s: HSV 最小 saturation (0-255).
            lower_v: HSV 最小 value (0-255).
            upper_h: HSV 最大 hue (0-180).
            upper_s: HSV 最大 saturation (0-255).
            upper_v: HSV 最大 value (0-255).
            min_area: 最小有效像素数，低于此值视为未检测到.
        """
        self.lower_color = np.array([lower_h, lower_s, lower_v], dtype=np.uint8)
        self.upper_color = np.array([upper_h, upper_s, upper_v], dtype=np.uint8)
        self.min_area = min_area
        logger.info(
            "ColorDetector 初始化: HSV=[%s, %s], min_area=%d",
            self.lower_color, self.upper_color, self.min_area,
        )

    def detect(self, frame: np.ndarray) -> Detection:
        """检测图像中颜色目标.

        Args:
            frame: BGR 图像.

        Returns:
            Detection 实例.
        """
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 生成掩码
        mask = cv2.inRange(hsv, self.lower_color, self.upper_color)

        # 统计有效像素
        coords = cv2.findNonZero(mask)
        if coords is None:
            logger.debug("未检测到有效颜色像素")
            return Detection(visible=False, confidence=0.0)

        # 计算重心
        coords = coords.squeeze()
        cx = float(np.mean(coords[:, 0]))
        cy = float(np.mean(coords[:, 1]))
        area = len(coords)

        confidence = min(1.0, area / max(self.min_area, 1))

        # 归一化误差
        ex, ey = self.normalize_error(cx, cy, w, h)

        logger.debug("检测: cx=%.1f, cy=%.1f, area=%d, conf=%.2f", cx, cy, area, confidence)
        return Detection(
            target_x=cx,
            target_y=cy,
            confidence=confidence,
            visible=True,
            ex=ex,
            ey=ey,
            width=float(np.max(coords[:, 0]) - np.min(coords[:, 0])),
            height=float(np.max(coords[:, 1]) - np.min(coords[:, 1])),
        )
