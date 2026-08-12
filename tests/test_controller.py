"""测试控制器."""

from __future__ import annotations

import numpy as np

from visual_servo_lite.controllers.p_controller import (
    DeadZonePController,
    EMAFilteredPController,
    PController,
)
from visual_servo_lite.detectors.color import ColorDetector
from visual_servo_lite.models import (
    Command,
    ControllerConfig,
    Detection,
    LostConfig,
    PanTiltConfig,
    TargetState,
)
from visual_servo_lite.pipeline import ServoPipeline
from visual_servo_lite.metrics import MetricsRecorder
from visual_servo_lite.adapters.mock import MockPanTiltAdapter


class TestPController:
    def _make_detection(self, ex: float, ey: float, visible: bool = True) -> Detection:
        return Detection(ex=ex, ey=ey, visible=visible)

    def test_target_at_center_no_command(self):
        cfg = ControllerConfig()
        pt = PanTiltConfig()
        ctrl = PController(cfg, pt)
        det = self._make_detection(0.0, 0.0)
        cmd = ctrl.compute(det, None)
        assert cmd.yaw == 0.0
        assert cmd.pitch == 0.0

    def test_target_on_left_positive_yaw(self):
        cfg = ControllerConfig(yaw_gain=10.0)
        pt = PanTiltConfig()
        ctrl = PController(cfg, pt)
        det = self._make_detection(-1.0, 0.0)
        cmd = ctrl.compute(det, None)
        assert cmd.yaw > 0  # 目标在左，需要向右转

    def test_target_on_right_negative_yaw(self):
        cfg = ControllerConfig(yaw_gain=10.0)
        pt = PanTiltConfig()
        ctrl = PController(cfg, pt)
        det = self._make_detection(1.0, 0.0)
        cmd = ctrl.compute(det, None)
        assert cmd.yaw < 0

    def test_command_limit(self):
        cfg = ControllerConfig(yaw_gain=20.0, max_single_cmd_yaw=3.0)
        pt = PanTiltConfig()
        ctrl = PController(cfg, pt)
        det = self._make_detection(-1.0, 0.0)
        cmd = ctrl.compute(det, None)
        assert abs(cmd.yaw) <= 3.0

    def test_target_lost_returns_zero(self):
        cfg = ControllerConfig(yaw_gain=10.0)
        pt = PanTiltConfig()
        ctrl = PController(cfg, pt)
        det = self._make_detection(0.0, 0.0, visible=False)
        cmd = ctrl.compute(det, None)
        assert cmd.yaw == 0.0
        assert cmd.pitch == 0.0


class TestDeadZonePController:
    def _make_detection(self, ex: float, ey: float, visible: bool = True) -> Detection:
        return Detection(ex=ex, ey=ey, visible=visible)

    def test_in_dead_zone_no_command(self):
        cfg = ControllerConfig(dead_zone=0.1, yaw_gain=10.0)
        pt = PanTiltConfig()
        ctrl = DeadZonePController(cfg, pt)
        det = self._make_detection(0.05, 0.0)
        cmd = ctrl.compute(det, None)
        assert cmd.yaw == 0.0

    def test_outside_dead_zone_command(self):
        cfg = ControllerConfig(dead_zone=0.05, yaw_gain=10.0)
        pt = PanTiltConfig()
        ctrl = DeadZonePController(cfg, pt)
        det = self._make_detection(-0.2, 0.0)
        cmd = ctrl.compute(det, None)
        assert cmd.yaw != 0.0


class TestEMAFilteredPController:
    def _make_detection(self, ex: float, ey: float, visible: bool = True) -> Detection:
        return Detection(ex=ex, ey=ey, visible=visible)

    def test_ama_smooths_output(self):
        cfg = ControllerConfig(yaw_gain=10.0, ema_alpha=0.3)
        pt = PanTiltConfig()
        ctrl = EMAFilteredPController(cfg, pt)

        # 连续输入突变值
        det1 = self._make_detection(-1.0, 0.0)
        cmd1 = ctrl.compute(det1, None)

        det2 = self._make_detection(1.0, 0.0)
        cmd2 = ctrl.compute(det2, cmd1)

        # EMA 应该平滑输出，第二次变化幅度小于第一次
        assert abs(cmd2.yaw) < abs(cmd1.yaw) * 2  # 不会突变


class TestServoPipeline:
    def _make_frame_with_target(self, x: int, y: int) -> np.ndarray:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        x1 = max(0, x - 20)
        y1 = max(0, y - 20)
        x2 = min(640, x + 20)
        y2 = min(480, y + 20)
        frame[y1:y2, x1:x2] = [0, 0, 200]
        return frame

    def _make_empty_frame(self) -> np.ndarray:
        return np.zeros((480, 640, 3), dtype=np.uint8)

    def test_tracking_center(self):
        detector = ColorDetector(lower_v=50)
        cfg = ControllerConfig()
        pt = PanTiltConfig()
        ctrl = PController(cfg, pt)
        adapter = MockPanTiltAdapter()
        metrics = MetricsRecorder()
        pipeline = ServoPipeline(detector, ctrl, adapter, metrics)

        frame = self._make_frame_with_target(320, 240)
        cmd = pipeline.step(frame)
        assert abs(cmd.yaw) < 1.0  # 目标在中心，指令应很小

    def test_tracking_left(self):
        detector = ColorDetector(lower_v=50)
        cfg = ControllerConfig(yaw_gain=5.0)
        pt = PanTiltConfig()
        ctrl = PController(cfg, pt)
        adapter = MockPanTiltAdapter()
        metrics = MetricsRecorder()
        pipeline = ServoPipeline(detector, ctrl, adapter, metrics)

        frame = self._make_frame_with_target(100, 240)
        cmd = pipeline.step(frame)
        assert cmd.yaw != 0.0  # 目标偏左，应有非零指令

    def test_target_lost(self):
        detector = ColorDetector(lower_v=50)
        cfg = ControllerConfig()
        pt = PanTiltConfig()
        ctrl = PController(cfg, pt)
        adapter = MockPanTiltAdapter()
        metrics = MetricsRecorder()
        # short=0.5s 表示半秒内仍视为短暂丢失，long=0.0 直接进入 LOST
        pipeline = ServoPipeline(
            detector, ctrl, adapter, metrics,
            LostConfig(short_lost_timeout=0.5, long_lost_timeout=0.0),
        )

        # 先检测目标
        frame = self._make_frame_with_target(100, 240)
        pipeline.step(frame)

        # 目标消失 → 进入 LOST（long_timeout=0.0）
        frame_empty = self._make_empty_frame()
        cmd = pipeline.step(frame_empty)
        assert cmd.yaw == 0.0  # LOST 状态发送零指令
        assert metrics.lost_count >= 1

    def test_command_within_safe_range(self):
        cfg = ControllerConfig(yaw_gain=50.0, max_single_cmd_yaw=2.0)
        pt = PanTiltConfig(max_yaw=30.0)
        ctrl = PController(cfg, pt)
        adapter = MockPanTiltAdapter()
        metrics = MetricsRecorder()
        detector = ColorDetector(lower_v=50)
        pipeline = ServoPipeline(detector, ctrl, adapter, metrics)

        frame = self._make_frame_with_target(0, 240)  # 极端位置
        cmd = pipeline.step(frame)
        assert abs(cmd.yaw) <= 2.0  # 不超过限幅
        assert abs(cmd.yaw) <= pt.max_yaw
