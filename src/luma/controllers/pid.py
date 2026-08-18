"""Stateful PID controller with output and integral safety limits."""

from __future__ import annotations

import time
from typing import Any

from luma.controllers.base import BaseController, as_tracking_error, clamp
from luma.models import MotionCommand, Target, TrackingError


class PIDController(BaseController):
    """Independent yaw/pitch PID loops over normalised tracking error."""

    def __init__(
        self,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.0,
        *,
        kp_y: float | None = None,
        ki_y: float | None = None,
        kd_y: float | None = None,
        max_output: float | tuple[float | None, float | None] | None = None,
        integral_limit: float | None = 10.0,
        config: Any | None = None,
        pan_tilt: Any | None = None,
    ) -> None:
        if config is None and not isinstance(kp, (int, float)):
            config = kp
            if pan_tilt is None and kp_y is not None and not isinstance(kp_y, (int, float)):
                pan_tilt = kp_y
            kp = 1.0
            kp_y = None
        if config is not None:
            kp = float(getattr(config, "yaw_gain", kp))
            kp_y = float(getattr(config, "pitch_gain", kp if kp_y is None else kp_y))
            if max_output is None:
                max_output = (
                    getattr(config, "max_single_cmd_yaw", None),
                    getattr(config, "max_single_cmd_pitch", None),
                )
        self.kp_x, self.ki_x, self.kd_x = float(kp), float(ki), float(kd)
        self.kp_y = float(kp if kp_y is None else kp_y)
        self.ki_y = float(ki if ki_y is None else ki_y)
        self.kd_y = float(kd if kd_y is None else kd_y)
        self.integral_limit = integral_limit
        if isinstance(max_output, tuple):
            self.output_limits = max_output
        elif max_output is None:
            self.output_limits = (
                getattr(pan_tilt, "max_yaw", None),
                getattr(pan_tilt, "max_pitch", None),
            )
        else:
            self.output_limits = max_output, max_output
        self.reset()

    def reset(self) -> None:
        self._integral_x = 0.0
        self._integral_y = 0.0
        self._previous_x: float | None = None
        self._previous_y: float | None = None

    def compute(
        self,
        error: TrackingError | Target,
        dt: float | None = None,
    ) -> MotionCommand:
        value = as_tracking_error(error)
        dt = 1.0 / 30.0 if dt is None or dt <= 0 else float(dt)
        derivative_x = 0.0 if self._previous_x is None else (value.x - self._previous_x) / dt
        derivative_y = 0.0 if self._previous_y is None else (value.y - self._previous_y) / dt
        self._previous_x, self._previous_y = value.x, value.y

        self._integral_x = self._integrate(self._integral_x, value.x, dt)
        self._integral_y = self._integrate(self._integral_y, value.y, dt)
        raw_yaw = -(self.kp_x * value.x + self.ki_x * self._integral_x + self.kd_x * derivative_x)
        raw_pitch = -(self.kp_y * value.y + self.ki_y * self._integral_y + self.kd_y * derivative_y)
        yaw = clamp(raw_yaw, self.output_limits[0])
        pitch = clamp(raw_pitch, self.output_limits[1])
        # Basic anti-windup: if an output is saturated, discard the newest
        # integral contribution that pushed it further into saturation.
        if yaw != raw_yaw and self.ki_x:
            self._integral_x -= value.x * dt
        if pitch != raw_pitch and self.ki_y:
            self._integral_y -= value.y * dt
        return MotionCommand(yaw=yaw, pitch=pitch, timestamp=time.time())

    def _integrate(self, current: float, value: float, dt: float) -> float:
        result = current + value * dt
        if self.integral_limit is not None:
            result = clamp(result, self.integral_limit)
        return result


PID = PIDController


__all__ = ["PID", "PIDController"]
