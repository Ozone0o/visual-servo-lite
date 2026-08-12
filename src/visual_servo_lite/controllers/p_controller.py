"""P 控制器系列.

包含:
- PController: 纯比例控制
- DeadZonePController: P + 死区
- EMAFilteredPController: P + EMA 滤波
"""

from __future__ import annotations

import logging
import time

from visual_servo_lite.controllers.base import BaseController
from visual_servo_lite.models import Command, ControllerConfig, Detection, PanTiltConfig

logger = logging.getLogger(__name__)


class PController(BaseController):
    """纯比例控制器.

    指令 = gain * 归一化误差
    """

    def __init__(
        self,
        config: ControllerConfig,
        pan_tilt: PanTiltConfig | None = None,
    ) -> None:
        self.cfg = config
        self.pt = pan_tilt or PanTiltConfig()
        self._last_cmd: Command | None = None

    def compute(self, detection: Detection, last_command: Command | None) -> Command:
        # 目标丢失时不发布新指令
        if not detection.visible:
            return Command()

        # 计算比例输出（负号：目标在左→ex<0→yaw>0→向右转）
        yaw = -self.cfg.yaw_gain * detection.ex
        pitch = -self.cfg.pitch_gain * detection.ey

        # 限制单次变化量
        if self._last_cmd is not None:
            yaw = self._limit_delta(self._last_cmd.yaw, yaw, self.cfg.max_single_cmd_yaw)
            pitch = self._limit_delta(self._last_cmd.pitch, pitch, self.cfg.max_single_cmd_pitch)
        else:
            yaw = max(-self.cfg.max_single_cmd_yaw, min(self.cfg.max_single_cmd_yaw, yaw))
            pitch = max(-self.cfg.max_single_cmd_pitch, min(self.cfg.max_single_cmd_pitch, pitch))

        # 限制云台角度范围
        yaw = max(self.pt.min_yaw, min(self.pt.max_yaw, yaw))
        pitch = max(self.pt.min_pitch, min(self.pt.max_pitch, pitch))

        cmd = Command(timestamp=time.time(), yaw=yaw, pitch=pitch)
        self._last_cmd = cmd
        return cmd

    @staticmethod
    def _limit_delta(current: float, target: float, max_delta: float) -> float:
        """限制目标值相对于当前值的变化幅度."""
        delta = target - current
        delta = max(-max_delta, min(max_delta, delta))
        return current + delta


class DeadZonePController(PController):
    """P 控制器 + 死区.

    当归一化误差在死区范围内时，输出零指令.
    """

    def compute(self, detection: Detection, last_command: Command | None) -> Command:
        if not detection.visible:
            return Command()

        # 死区内不动作
        if abs(detection.ex) < self.cfg.dead_zone:
            detection.ex = 0.0
        if abs(detection.ey) < self.cfg.dead_zone:
            detection.ey = 0.0

        return super().compute(detection, last_command)


class EMAFilteredPController(PController):
    """P 控制器 + EMA 滤波.

    对上一时刻的控制输出做指数移动平均，平滑抖动.
    """

    def __init__(
        self,
        config: ControllerConfig,
        pan_tilt: PanTiltConfig | None = None,
    ) -> None:
        super().__init__(config, pan_tilt)
        self._ema_yaw: float = 0.0
        self._ema_pitch: float = 0.0
        self._ema_initialized = False

    def compute(self, detection: Detection, last_command: Command | None) -> Command:
        if not detection.visible:
            return Command()

        # 先计算原始 P 输出（负号：反向控制）
        raw_yaw = -self.cfg.yaw_gain * detection.ex
        raw_pitch = -self.cfg.pitch_gain * detection.ey

        # EMA 滤波
        if self._ema_initialized:
            raw_yaw = self.cfg.ema_alpha * raw_yaw + (1 - self.cfg.ema_alpha) * self._ema_yaw
            raw_pitch = self.cfg.ema_alpha * raw_pitch + (1 - self.cfg.ema_alpha) * self._ema_pitch
        else:
            self._ema_yaw = raw_yaw
            self._ema_pitch = raw_pitch
            self._ema_initialized = True

        # 构建临时指令用于限幅
        temp_cmd = Command(yaw=raw_yaw, pitch=raw_pitch)
        cmd = super().compute(detection, last_command)

        # 更新 EMA 状态
        self._ema_yaw = cmd.yaw
        self._ema_pitch = cmd.pitch

        return cmd
