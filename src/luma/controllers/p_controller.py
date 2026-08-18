"""Proportional controllers."""

from __future__ import annotations

import time
from typing import Any

from luma.controllers.base import BaseController, as_tracking_error, clamp
from luma.models import MotionCommand, Target, TrackingError


class PController(BaseController):
    """A minimal proportional image-based controller.

    The sign convention is intuitive for a camera mounted on a pan/tilt
    head: a target left of centre (negative ``error.x``) produces positive
    yaw, moving the view to the right.
    """

    def __init__(
        self,
        kp: float = 1.0,
        kp_y: float | None = None,
        *,
        dead_zone: float = 0.0,
        max_output: float | tuple[float | None, float | None] | None = None,
        max_yaw: float | None = None,
        max_pitch: float | None = None,
    ) -> None:
        if kp_y is None:
            kp_y = kp
        if dead_zone < 0:
            raise ValueError("dead_zone must be >= 0")
        self.kp_x = float(kp)
        self.kp_y = float(kp_y)
        self.dead_zone = float(dead_zone)
        self.output_limits = self._limits(max_output, max_yaw, max_pitch)

    @staticmethod
    def _limits(
        max_output: float | tuple[float | None, float | None] | None,
        max_yaw: float | None,
        max_pitch: float | None,
    ) -> tuple[float | None, float | None]:
        if isinstance(max_output, tuple):
            return max_output
        if max_output is not None:
            return max_output, max_output
        return max_yaw, max_pitch

    def compute(
        self,
        error: TrackingError | Target,
        dt: float | None = None,
    ) -> MotionCommand:
        del dt
        value = as_tracking_error(error)
        ex = 0.0 if abs(value.x) <= self.dead_zone else value.x
        ey = 0.0 if abs(value.y) <= self.dead_zone else value.y
        return MotionCommand(
            yaw=clamp(-self.kp_x * ex, self.output_limits[0]),
            pitch=clamp(-self.kp_y * ey, self.output_limits[1]),
            timestamp=time.time(),
        )


class DeadZonePController(PController):
    """Named convenience variant of :class:`PController`."""

    def __init__(self, *args: Any, dead_zone: float = 0.05, **kwargs: Any) -> None:
        super().__init__(*args, dead_zone=dead_zone, **kwargs)


__all__ = ["BaseController", "DeadZonePController", "PController"]
