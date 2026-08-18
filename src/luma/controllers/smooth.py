"""Smoothed controller wrapper."""

from __future__ import annotations

import time

from luma.controllers.base import BaseController, adapt_controller, as_tracking_error
from luma.controllers.p_controller import PController
from luma.models import MotionCommand, Target, TrackingError


class SmoothController(BaseController):
    """Exponential smoothing around any Luma controller.

    ``alpha=1`` is transparent; lower values damp abrupt detector changes.
    """

    def __init__(
        self,
        controller: BaseController | object | None = None,
        *,
        alpha: float = 0.25,
        kp: float = 1.0,
        max_output: float | tuple[float | None, float | None] | None = None,
    ) -> None:
        if not 0 < alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")
        self.controller = adapt_controller(controller or PController(kp=kp, max_output=max_output))
        self.alpha = float(alpha)
        self.reset()

    def reset(self) -> None:
        self._previous: MotionCommand | None = None
        reset = getattr(self.controller, "reset", None)
        if callable(reset):
            reset()

    def compute(
        self,
        error: TrackingError | Target,
        dt: float | None = None,
    ) -> MotionCommand:
        value = as_tracking_error(error)
        if isinstance(dt, MotionCommand):
            # Preserve the pre-0.2 ``compute(error, previous_command)`` API
            # for direct callers; the pipeline uses the canonical keyword dt.
            if self._previous is None:
                self._previous = dt
            dt = None
        raw = self.controller.compute(
            value,
            dt=1.0 / 30.0 if dt is None else float(dt),
            previous=self._previous,
        )
        if self._previous is None:
            result = raw
        else:
            result = MotionCommand(
                yaw=self.alpha * raw.yaw + (1 - self.alpha) * self._previous.yaw,
                pitch=self.alpha * raw.pitch + (1 - self.alpha) * self._previous.pitch,
                linear_x=self.alpha * raw.linear_x + (1 - self.alpha) * self._previous.linear_x,
                linear_y=self.alpha * raw.linear_y + (1 - self.alpha) * self._previous.linear_y,
                linear_z=self.alpha * raw.linear_z + (1 - self.alpha) * self._previous.linear_z,
                angular_x=self.alpha * raw.angular_x + (1 - self.alpha) * self._previous.angular_x,
                angular_y=self.alpha * raw.angular_y + (1 - self.alpha) * self._previous.angular_y,
                angular_z=self.alpha * raw.angular_z + (1 - self.alpha) * self._previous.angular_z,
                timestamp=time.time(),
                frame_id=raw.frame_id,
                metadata=dict(raw.metadata),
            )
        self._previous = result
        return result


__all__ = ["SmoothController"]
