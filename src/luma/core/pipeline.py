"""The camera -> detector -> controller -> adapter execution pipeline."""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Iterable, Iterator
from enum import Enum
from typing import Any

from luma.controllers.base import adapt_controller
from luma.core.interfaces import Controller, Detector, RobotAdapter
from luma.filters import EMAFilter
from luma.models import (
    MotionCommand,
    PipelineResult,
    Target,
    TrackingError,
)
from luma.safety import SafetyDecision, SafetyGate, SafetyLimits

logger = logging.getLogger(__name__)


class PipelineState(str, Enum):
    """High-level target visibility state."""

    TRACKING = "tracking"
    SHORT_LOST = "short_lost"
    LOST = "lost"


class LumaPipeline:
    """Connect a detector, controller and robot adapter.

    ``step`` is intentionally side-effect free with respect to the robot: it
    computes and returns a command.  ``step_and_send`` and ``run`` are the
    convenient execution APIs when the command should be sent immediately.
    This makes simulation and offline replay straightforward.
    """

    def __init__(
        self,
        detector: Detector,
        controller: Controller,
        adapter: RobotAdapter,
        metrics: Any | None = None,
        *,
        lost_timeout: float = 1.0,
        lost_behavior: str = "stop",
        short_lost_timeout: float | None = None,
        long_lost_timeout: float | None = None,
        error_smoothing: float | None = None,
        safety_limits: SafetyLimits | dict[str, Any] | None = None,
        safety_gate: SafetyGate | None = None,
    ) -> None:
        if lost_timeout < 0:
            raise ValueError("lost_timeout must be >= 0")
        if lost_behavior not in {"stop", "hold"}:
            raise ValueError("lost_behavior must be 'stop' or 'hold'")
        if error_smoothing is not None and not 0 < error_smoothing <= 1:
            raise ValueError("error_smoothing must be in (0, 1]")

        self.detector = detector
        self.controller = controller
        self._controller = adapt_controller(controller)
        self.adapter = adapter
        if metrics is None:
            from luma.metrics import MetricsRecorder

            metrics = MetricsRecorder()
        self.metrics = metrics
        self.lost_timeout = float(lost_timeout)
        self.lost_behavior = lost_behavior
        self.error_smoothing = error_smoothing
        self._short_lost_timeout = (
            float(lost_timeout) if short_lost_timeout is None else float(short_lost_timeout)
        )
        self._long_lost_timeout = (
            float(lost_timeout) if long_lost_timeout is None else float(long_lost_timeout)
        )
        if self._short_lost_timeout < 0 or self._long_lost_timeout < 0:
            raise ValueError("lost timeouts must be >= 0")
        if self._long_lost_timeout < self._short_lost_timeout:
            raise ValueError("long_lost_timeout must be >= short_lost_timeout")

        if safety_gate is not None and safety_limits is not None:
            raise ValueError("pass safety_gate or safety_limits, not both")
        if safety_gate is not None:
            self.safety_gate = safety_gate
        elif isinstance(safety_limits, dict):
            self.safety_gate = SafetyGate(SafetyLimits(**safety_limits))
        else:
            self.safety_gate = SafetyGate(safety_limits)

        self.state = PipelineState.TRACKING
        self.last_result: PipelineResult | None = None
        self._last_visible_at = time.monotonic()
        self._last_visible_time = time.time()
        self._last_step_at: float | None = None
        self._last_command: MotionCommand | None = None
        self._hold_command: MotionCommand | None = None
        self._filtered_error: TrackingError | None = None
        self._error_ema_x = EMAFilter(alpha=0.5, initial=0.0)
        self._error_ema_y = EMAFilter(alpha=0.5, initial=0.0)
        self.last_safety_decision = SafetyDecision(True)
        self.last_adapter_error: str | None = None

    @property
    def last_command(self) -> MotionCommand | None:
        return self._last_command

    def process(
        self,
        frame: Any,
        *,
        timestamp: float | None = None,
        frame_age: float | None = None,
    ) -> PipelineResult:
        """Process one frame and return target, error, state and command."""

        now = time.monotonic()
        stamp = time.time() if timestamp is None else timestamp
        fault_reason: str | None = None
        try:
            target = self._detect(frame)
        except Exception as exc:  # a detector fault must never keep motion alive
            logger.exception("detector failed; issuing a stop command")
            target = Target.empty(timestamp=stamp)
            fault_reason = f"detector_error:{type(exc).__name__}"
        target.timestamp = stamp
        try:
            error = self._resolve_error(target, frame)
        except Exception as exc:
            logger.exception("could not resolve tracking error; issuing a stop command")
            target = Target.empty(timestamp=stamp)
            error = TrackingError(timestamp=stamp)
            fault_reason = fault_reason or f"error_resolution:{type(exc).__name__}"

        if target.visible:
            if not self._finite_error(error):
                fault_reason = fault_reason or "non_finite_tracking_error"
                target = Target.empty(timestamp=stamp)
                error = TrackingError(timestamp=stamp)
            else:
                self._mark_tracking(now)
                self._error_ema_x.update(error.x)
                self._error_ema_y.update(error.y)
                try:
                    error = self._smooth_error(error)
                    target.set_error(error)
                    command = self._compute(error, self._dt(now))
                except Exception as exc:  # controller/plugin fault => safe stop
                    logger.exception("controller failed; issuing a stop command")
                    fault_reason = f"controller_error:{type(exc).__name__}"
                    command = MotionCommand.stop()
                else:
                    self._hold_command = command
        else:
            self._mark_lost(now)
            error = TrackingError(timestamp=stamp)
            target.set_error(error)
            if self.state == PipelineState.SHORT_LOST and self.lost_behavior == "hold":
                command = self._hold_command or MotionCommand.stop()
            else:
                command = MotionCommand.stop()

        if fault_reason is not None:
            target.visible = False
            target.metadata["safety_fault"] = fault_reason
            self.state = PipelineState.LOST
            command = MotionCommand.stop(metadata={"safety_fault": fault_reason})

        command.timestamp = stamp
        command, decision = self.safety_gate.enforce(
            command,
            self._last_command,
            frame_timestamp=stamp,
            frame_age=frame_age,
        )
        command.timestamp = stamp
        self.last_safety_decision = decision
        if decision.allowed:
            self._last_command = command
        elif "safety_violation" not in command.metadata:
            command.metadata["safety_violation"] = list(decision.reasons)
        result = PipelineResult(
            target=target,
            error=error,
            command=command,
            state=self.state.value,
            timestamp=stamp,
        )
        self.last_result = result
        if hasattr(self.metrics, "record"):
            try:
                self.metrics.record(target, command, state=self.state.value)
            except TypeError:
                # Minimal recorders may only accept target and command.
                self.metrics.record(target, command)
        return result

    def step(
        self,
        frame: Any,
        *,
        timestamp: float | None = None,
        frame_age: float | None = None,
    ) -> MotionCommand:
        """Process one frame and return its command without sending it."""

        return self.process(frame, timestamp=timestamp, frame_age=frame_age).command

    def step_and_send(
        self,
        frame: Any,
        *,
        timestamp: float | None = None,
        frame_age: float | None = None,
    ) -> PipelineResult:
        """Process and immediately send one command to the adapter."""

        result = self.process(frame, timestamp=timestamp, frame_age=frame_age)
        self.last_adapter_error = None
        try:
            accepted = self.adapter.send(result.command)
        except Exception as exc:
            accepted = False
            self.last_adapter_error = f"adapter_error:{type(exc).__name__}"
            logger.exception("adapter failed; attempting a stop command")
        if not accepted:
            if self.last_adapter_error is None:
                self.last_adapter_error = "adapter_rejected_command"
            stop = MotionCommand.stop(metadata={"adapter_failure": self.last_adapter_error})
            try:
                self.adapter.send(stop)
            except Exception:
                logger.exception("adapter also failed to accept the stop command")
            result.command = stop
            self.last_result = result
        return result

    def run(
        self,
        frames: Iterable[Any],
        *,
        max_steps: int | None = None,
    ) -> Iterator[PipelineResult]:
        """Run over an iterable camera source and send every command."""

        for index, frame in enumerate(frames):
            if max_steps is not None and index >= max_steps:
                break
            yield self.step_and_send(frame)

    def shutdown(self) -> None:
        """Flush metrics and close the robot adapter."""

        if hasattr(self.metrics, "save_csv"):
            self.metrics.save_csv()
        self.adapter.close()

    def __enter__(self) -> LumaPipeline:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.shutdown()

    def _detect(self, frame: Any) -> Target:
        result = self.detector.detect(frame)
        if isinstance(result, Target):
            return result
        # Custom plugins are allowed to return a dictionary or a simple
        # (x, y) tuple.  Importing here keeps the core interface lightweight.
        from luma.detectors.base import coerce_target

        return coerce_target(result, frame)

    @staticmethod
    def _finite_error(error: TrackingError) -> bool:
        return math.isfinite(float(error.x)) and math.isfinite(float(error.y))

    def _mark_tracking(self, now: float) -> None:
        self.state = PipelineState.TRACKING
        self._last_visible_at = now
        self._last_visible_time = time.time()

    def _mark_lost(self, now: float) -> None:
        # Keep both clocks so replay tests can control elapsed time precisely.
        elapsed = max(now - self._last_visible_at, time.time() - self._last_visible_time)
        if elapsed > self._long_lost_timeout:
            self.state = PipelineState.LOST
        elif elapsed > self._short_lost_timeout:
            self.state = PipelineState.SHORT_LOST
        else:
            self.state = PipelineState.TRACKING

    @staticmethod
    def _frame_size(frame: Any) -> tuple[int, int] | None:
        shape = getattr(frame, "shape", None)
        if shape is None or len(shape) < 2:
            return None
        return int(shape[1]), int(shape[0])

    def _resolve_error(self, target: Target, frame: Any) -> TrackingError:
        if not target.visible:
            return TrackingError(timestamp=target.timestamp)
        if target.ex is not None and target.ey is not None:
            return TrackingError(target.ex, target.ey, target.timestamp)

        size = self._frame_size(frame)
        if size is None or target.x is None or target.y is None:
            return TrackingError(timestamp=target.timestamp)
        width, height = size
        if width <= 0 or height <= 0:
            return TrackingError(timestamp=target.timestamp)
        return TrackingError(
            x=max(-1.0, min(1.0, (target.x - width / 2) / (width / 2))),
            y=max(-1.0, min(1.0, (target.y - height / 2) / (height / 2))),
            timestamp=target.timestamp,
        )

    def _smooth_error(self, error: TrackingError) -> TrackingError:
        if self.error_smoothing is None:
            return error
        alpha = self.error_smoothing
        if self._filtered_error is None:
            self._filtered_error = error
        else:
            self._filtered_error = TrackingError(
                x=alpha * error.x + (1 - alpha) * self._filtered_error.x,
                y=alpha * error.y + (1 - alpha) * self._filtered_error.y,
                timestamp=error.timestamp,
            )
        return self._filtered_error

    def _dt(self, now: float) -> float:
        if self._last_step_at is None:
            self._last_step_at = now
            return 1.0 / 30.0
        dt = max(1e-6, now - self._last_step_at)
        self._last_step_at = now
        return dt

    def _compute(self, error: TrackingError, dt: float) -> MotionCommand:
        raw = self._controller.compute(error, dt=dt, previous=self._last_command)
        if isinstance(raw, MotionCommand):
            return raw
        return MotionCommand(
            yaw=float(getattr(raw, "yaw", 0.0)),
            pitch=float(getattr(raw, "pitch", 0.0)),
            timestamp=time.time(),
        )


__all__ = ["LumaPipeline", "PipelineState"]
