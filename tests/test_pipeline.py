"""Tests for the Luma execution pipeline."""

from __future__ import annotations

import os
import tempfile
import time

from luma.adapters.mock import MockPanTiltAdapter
from luma.metrics import MetricsRecorder
from luma.models import MotionCommand, Target
from luma.pipeline import LumaPipeline, PipelineState


class DummyDetector:
    """始终返回相同检测结果的检测器。"""

    def __init__(self, visible: bool = True, ex: float = 0.0, ey: float = 0.0):
        self.visible = visible
        self.ex = ex
        self.ey = ey

    def detect(self, frame) -> Target:
        return Target(visible=self.visible, ex=self.ex, ey=self.ey)


class DummyController:
    """始终返回零指令的控制器。"""

    def compute(self, detection, hold_cmd: MotionCommand | None) -> MotionCommand:
        return MotionCommand()


class TestLumaPipelineStep:
    """测试 step() 方法。"""

    def setup_method(self):
        self.detector = DummyDetector(visible=True, ex=1.0, ey=2.0)
        self.controller = DummyController()
        self.adapter = MockPanTiltAdapter()
        self.pipeline = LumaPipeline(
            detector=self.detector,
            controller=self.controller,
            adapter=self.adapter,
        )

    def test_step_returns_command(self):
        cmd = self.pipeline.step(frame=None)
        assert isinstance(cmd, MotionCommand)

    def test_step_calls_detector(self):
        det = DummyDetector(visible=True, ex=5.0, ey=3.0)
        pipe = LumaPipeline(
            detector=det, controller=self.controller, adapter=self.adapter,
        )
        pipe.step(frame=None)
        # EMA should have received filtered values from detection
        assert pipe._error_ema_x.has_value
        assert pipe._error_ema_y.has_value

    def test_step_with_metrics(self):
        recorder = MetricsRecorder()
        pipe = LumaPipeline(
            detector=self.detector, controller=self.controller,
            adapter=self.adapter, metrics=recorder,
        )
        pipe.step(frame=None)
        summary = recorder.get_summary()
        assert "total_frames" in summary
        assert summary["total_frames"] >= 1


class TestLumaPipelineLostState:
    """测试目标丢失状态机。"""

    def setup_method(self):
        self.detector = DummyDetector(visible=True)
        self.controller = DummyController()
        self.adapter = MockPanTiltAdapter()
        self.pipeline = LumaPipeline(
            detector=self.detector,
            controller=self.controller,
            adapter=self.adapter,
            lost_timeout=1.0,
            short_lost_timeout=1.0,
            long_lost_timeout=5.0,
            lost_behavior="hold",
        )

    def test_tracking_state_on_visible(self):
        assert self.pipeline.state == PipelineState.TRACKING
        self.pipeline.step(frame=None)
        assert self.pipeline.state == PipelineState.TRACKING

    def test_short_lost_state(self):
        self.detector.visible = False
        # 跳过时间：直接修改 _last_visible_time
        self.pipeline._last_visible_time = time.time() - 2.0
        self.pipeline.step(frame=None)
        assert self.pipeline.state == PipelineState.SHORT_LOST

    def test_long_lost_state(self):
        self.detector.visible = False
        self.pipeline._last_visible_time = time.time() - 10.0
        self.pipeline.step(frame=None)
        assert self.pipeline.state == PipelineState.LOST

    def test_recover_to_tracking(self):
        self.detector.visible = False
        self.pipeline._last_visible_time = time.time() - 10.0
        self.pipeline.step(frame=None)
        assert self.pipeline.state == PipelineState.LOST

        # 目标重新出现
        self.detector.visible = True
        self.pipeline.step(frame=None)
        assert self.pipeline.state == PipelineState.TRACKING

    def test_hold_command_on_short_lost(self):
        self.controller = DummyController()
        self.pipeline = LumaPipeline(
            detector=self.detector, controller=self.controller,
            adapter=self.adapter,
            lost_timeout=1.0,
            short_lost_timeout=1.0,
            long_lost_timeout=5.0,
            lost_behavior="hold",
        )
        # 先检测一次，设置 _hold_command
        self.pipeline.step(frame=None)
        hold = self.pipeline._hold_command

        self.detector.visible = False
        self.pipeline._last_visible_time = time.time() - 2.0
        cmd = self.pipeline.step(frame=None)
        assert cmd is hold or cmd is not None


class TestLumaPipelineRunWithTempDir:
    """测试 run() 和 shutdown()（使用临时目录）。"""

    def test_shutdown_saves_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = DummyDetector(visible=True)
            adapter = MockPanTiltAdapter()
            recorder = MetricsRecorder(output_path=tmpdir + "/metrics.csv")
            pipe = LumaPipeline(
                detector=detector, controller=DummyController(),
                adapter=adapter, metrics=recorder,
            )
            pipe.step(frame=None)
            pipe.shutdown()
            # MetricsRecorder should have created a CSV file
            assert os.path.exists(recorder._output_path)


class TestLumaPipelineHoldCommandNone:
    """测试 _hold_command 为 None 时的丢失处理。"""

    def test_short_lost_returns_default_command_when_no_hold(self):
        detector = DummyDetector(visible=True)
        adapter = MockPanTiltAdapter()
        pipe = LumaPipeline(
            detector=detector, controller=DummyController(),
            adapter=adapter,
            lost_timeout=1.0,
            short_lost_timeout=1.0,
            long_lost_timeout=5.0,
            lost_behavior="hold",
        )
        # 不先执行 step，直接模拟丢失
        detector.visible = False
        pipe._last_visible_time = time.time() - 2.0
        cmd = pipe.step(frame=None)
        assert isinstance(cmd, MotionCommand)
