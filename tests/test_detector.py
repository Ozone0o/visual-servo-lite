"""测试检测器."""

from __future__ import annotations

import numpy as np

from visual_servo_lite.detectors.color import ColorDetector


class TestColorDetector:
    @staticmethod
    def _make_frame(center_x: int, center_y: int, color_h: int = 10) -> np.ndarray:
        """创建空白帧，在指定位置绘制一个蓝色矩形作为目标."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # 绘制一个红色矩形（HSV H≈0）
        x1 = max(0, center_x - 20)
        y1 = max(0, center_y - 20)
        x2 = min(640, center_x + 20)
        y2 = min(480, center_y + 20)
        frame[y1:y2, x1:x2] = [0, 0, 200]  # BGR 红色
        return frame

    def test_target_at_center(self):
        detector = ColorDetector(lower_v=50)
        frame = self._make_frame(320, 240)
        det = detector.detect(frame)
        assert det.visible is True
        assert abs(det.ex) < 0.1
        assert abs(det.ey) < 0.1

    def test_target_at_left(self):
        detector = ColorDetector(lower_v=50)
        frame = self._make_frame(50, 240)
        det = detector.detect(frame)
        assert det.visible is True
        assert det.ex < -0.5  # 左侧应为负

    def test_target_at_right(self):
        detector = ColorDetector(lower_v=50)
        frame = self._make_frame(590, 240)
        det = detector.detect(frame)
        assert det.visible is True
        assert det.ex > 0.5  # 右侧应为正

    def test_target_at_top(self):
        detector = ColorDetector(lower_v=50)
        frame = self._make_frame(320, 50)
        det = detector.detect(frame)
        assert det.visible is True
        assert det.ey < -0.5  # 上方应为负

    def test_target_at_bottom(self):
        detector = ColorDetector(lower_v=50)
        frame = self._make_frame(320, 430)
        det = detector.detect(frame)
        assert det.visible is True
        assert det.ey > 0.5  # 下方应为正

    def test_no_target(self):
        """全黑帧，无目标."""
        detector = ColorDetector(lower_v=50)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        det = detector.detect(frame)
        assert det.visible is False
        assert det.confidence == 0.0
