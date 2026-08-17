"""Demo: 使用假图片运行视觉伺服管线。

演示 ColorDetector + PController + MockPanTiltAdapter 的完整流程。
输出检测到的目标位置和云台控制指令。

用法:
    python examples/demo.py
"""

from __future__ import annotations

import numpy as np

import cv2
from visual_servo_lite.adapters.mock import MockPanTiltAdapter
from visual_servo_lite.controllers.base import BaseController
from visual_servo_lite.detectors.color import ColorDetector
from visual_servo_lite.models import Command, Detection
from visual_servo_lite.pipeline import ServoPipeline


class SimplePController(BaseController):
    """简易 P 控制器。"""

    def __init__(self, kp: float = 1.0) -> None:
        self.kp = kp

    def compute(self, detection: Detection, last_command: Command | None) -> Command:
        return Command(yaw=detection.ex * self.kp, pitch=detection.ey * self.kp)


def create_demo_image(width: int = 640, height: int = 480) -> np.ndarray:
    """创建一张包含红色目标点的假图片。"""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    # 在中心偏右上方画一个红色圆点
    cx, cy = 380, 200
    cv2.circle(frame, (cx, cy), 30, (0, 0, 255), -1)  # BGR 红色
    return frame


def main() -> None:
    # 创建假图片
    frame = create_demo_image()

    # 初始化组件
    detector = ColorDetector(
        lower_h=0, lower_s=100, lower_v=100,
        upper_h=20, upper_s=255, upper_v=255,
        min_area=100,
    )
    controller = SimplePController(kp=1.0)
    adapter = MockPanTiltAdapter()

    # 创建管线
    pipeline = ServoPipeline(detector=detector, controller=controller, adapter=adapter)

    # 运行 3 步
    print("目标位置: x=320, y=240")
    print("-" * 40)
    for i in range(3):
        cmd = pipeline.step(frame)
        print(f"step {i+1}: detection visible={detector.detect(frame).visible}, "
              f"cmd=yaw={cmd.yaw:.4f}, pitch={cmd.pitch:.4f}")

    pipeline.shutdown()


if __name__ == "__main__":
    main()
