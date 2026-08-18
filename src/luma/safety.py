"""Safety checks for commands leaving the visual-servo pipeline.

The safety gate is deliberately transport-neutral.  It catches malformed
controller output before it reaches a robot adapter and turns violations into
an explicit zero command.  Applications with a stricter hardware envelope
should configure the limits for that device rather than relying on defaults.
"""

from __future__ import annotations

import math
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from luma.models import MotionCommand

_COMMAND_CHANNELS = (
    "yaw",
    "pitch",
    "linear_x",
    "linear_y",
    "linear_z",
    "angular_x",
    "angular_y",
    "angular_z",
)


@dataclass(frozen=True)
class ChannelLimit:
    """Magnitude, slew, and acceleration limits for one command channel."""

    max_value: float | None = None
    max_delta: float | None = None
    max_acceleration: float | None = None

    def __post_init__(self) -> None:
        for name in ("max_value", "max_delta", "max_acceleration"):
            value = getattr(self, name)
            if value is not None and (not math.isfinite(float(value)) or float(value) < 0):
                raise ValueError(f"{name} must be finite and >= 0, or None")


@dataclass(frozen=True)
class SafetyLimits:
    """Limits enforced by :class:`SafetyGate`.

    ``None`` disables an individual optional limit.  Finite-value checking is
    always enabled because NaN and infinity are not meaningful actuator
    commands. ``channel_limits`` provides independent magnitude, delta, and
    acceleration limits for every channel that an adapter may send. The
    linear/angular defaults are deliberately separate from pan/tilt units.
    """

    max_yaw: float | None = 90.0
    max_pitch: float | None = 45.0
    max_yaw_delta: float | None = None
    max_pitch_delta: float | None = None
    max_command_rate_hz: float | None = 30.0
    max_frame_age: float | None = 1.0
    channel_limits: Mapping[str, ChannelLimit | Mapping[str, Any]] | None = None

    def __post_init__(self) -> None:
        for name in (
            "max_yaw",
            "max_pitch",
            "max_yaw_delta",
            "max_pitch_delta",
            "max_frame_age",
        ):
            value = getattr(self, name)
            if value is not None and (not math.isfinite(float(value)) or float(value) < 0):
                raise ValueError(f"{name} must be finite and >= 0, or None")
        if self.max_command_rate_hz is not None and (
            not math.isfinite(float(self.max_command_rate_hz))
            or float(self.max_command_rate_hz) <= 0
        ):
            raise ValueError("max_command_rate_hz must be finite and > 0, or None")

        defaults = {
            "yaw": ChannelLimit(self.max_yaw, self.max_yaw_delta),
            "pitch": ChannelLimit(self.max_pitch, self.max_pitch_delta),
            # Twist channels have different units from pan/tilt, so they get
            # their own conservative defaults instead of inheriting yaw/pitch.
            "linear_x": ChannelLimit(1.0, 1.0),
            "linear_y": ChannelLimit(1.0, 1.0),
            "linear_z": ChannelLimit(1.0, 1.0),
            "angular_x": ChannelLimit(1.0, 1.0),
            "angular_y": ChannelLimit(1.0, 1.0),
            "angular_z": ChannelLimit(1.0, 1.0),
        }
        for channel, configured in (self.channel_limits or {}).items():
            if channel not in _COMMAND_CHANNELS:
                raise ValueError(f"unknown command channel limit: {channel}")
            if isinstance(configured, ChannelLimit):
                defaults[channel] = configured
            elif isinstance(configured, Mapping):
                defaults[channel] = ChannelLimit(
                    configured.get("max_value", configured.get("max")),
                    configured.get("max_delta"),
                    configured.get("max_acceleration"),
                )
            else:
                raise ValueError(f"channel limit for {channel} must be a mapping")
        object.__setattr__(self, "channel_limits", defaults)


@dataclass(frozen=True)
class SafetyDecision:
    """Result of checking one command."""

    allowed: bool
    reasons: tuple[str, ...] = ()


class SafetyGate:
    """Validate and, when necessary, replace a command with a stop command."""

    def __init__(self, limits: SafetyLimits | None = None) -> None:
        self.limits = limits or SafetyLimits()
        self._last_accepted_at: float | None = None
        self._last_accepted_command: MotionCommand | None = None

    def check(
        self,
        command: MotionCommand,
        previous: MotionCommand | None = None,
        *,
        now: float | None = None,
        frame_timestamp: float | None = None,
        frame_age: float | None = None,
    ) -> SafetyDecision:
        """Return whether *command* is safe to send.

        The rate limit is measured with a monotonic clock.  Stop commands are
        always allowed so an emergency stop can never be rate-limited.
        """

        reasons: list[str] = []
        for channel in _COMMAND_CHANNELS:
            try:
                value = float(getattr(command, channel))
            except (TypeError, ValueError):
                reasons.append(f"non_numeric_{channel}")
                continue
            if not math.isfinite(value):
                reasons.append(f"non_finite_{channel}")

        current = time.monotonic() if now is None else now
        limits = self.limits
        previous_command = previous or self._last_accepted_command
        for channel, channel_limit in limits.channel_limits.items():
            value = float(getattr(command, channel))
            if channel_limit.max_value is not None and math.isfinite(value):
                if abs(value) > channel_limit.max_value:
                    reasons.append(f"{channel}_limit")
            if previous_command is None:
                continue
            previous_value = float(getattr(previous_command, channel))
            delta = abs(value - previous_value)
            if channel_limit.max_delta is not None and math.isfinite(delta):
                if delta > channel_limit.max_delta:
                    reasons.append(f"{channel}_delta_limit")
            if channel_limit.max_acceleration is not None and self._last_accepted_at is not None:
                elapsed = max(current - self._last_accepted_at, 1e-9)
                acceleration = delta / elapsed
                if math.isfinite(acceleration) and acceleration > channel_limit.max_acceleration:
                    reasons.append(f"{channel}_acceleration_limit")

        if (
            limits.max_command_rate_hz is not None
            and command.magnitude > 0
            and self._last_accepted_at is not None
            and current - self._last_accepted_at < 1.0 / limits.max_command_rate_hz
        ):
            reasons.append("command_rate_limit")

        if limits.max_frame_age is not None and frame_age is not None:
            try:
                age = float(frame_age)
            except (TypeError, ValueError):
                age = math.inf
            if not math.isfinite(age) or age < 0 or age > limits.max_frame_age:
                reasons.append("stale_frame")
        elif limits.max_frame_age is not None and frame_timestamp is not None:
            age = abs(time.time() - float(frame_timestamp))
            if age > limits.max_frame_age:
                reasons.append("stale_frame")

        return SafetyDecision(not reasons, tuple(reasons))

    def enforce(
        self,
        command: MotionCommand,
        previous: MotionCommand | None = None,
        *,
        now: float | None = None,
        frame_timestamp: float | None = None,
        frame_age: float | None = None,
    ) -> tuple[MotionCommand, SafetyDecision]:
        """Return a safe command and the corresponding decision."""

        decision = self.check(
            command,
            previous,
            now=now,
            frame_timestamp=frame_timestamp,
            frame_age=frame_age,
        )
        if not decision.allowed:
            return MotionCommand.stop(
                metadata={"safety_violation": list(decision.reasons)}
            ), decision
        current = time.monotonic() if now is None else now
        if command.magnitude > 0:
            self._last_accepted_at = current
            self._last_accepted_command = command
        return command, decision


__all__ = ["ChannelLimit", "SafetyDecision", "SafetyGate", "SafetyLimits"]
