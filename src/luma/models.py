"""Small, dependency-free data models used by Luma.

The models deliberately describe *what* was observed and *what* should be
sent to a robot.  Detectors and robot adapters are therefore free to use
their own image and transport libraries without leaking those details into
the core pipeline.
"""

from __future__ import annotations

import math
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrackingError:
    """Normalised image-space error.

    ``x`` and ``y`` are in ``[-1, 1]``.  The image centre is zero, left/up are
    negative and right/down are positive.  Controllers consume this model,
    which keeps them independent from camera resolution.
    """

    x: float = 0.0
    y: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def magnitude(self) -> float:
        """Euclidean tracking error magnitude."""

        return math.hypot(self.x, self.y)

    def as_tuple(self) -> tuple[float, float]:
        return self.x, self.y


@dataclass
class Target:
    """A detector result.

    ``x``/``y`` are pixel coordinates when present.  A detector may instead
    provide ``ex``/``ey`` directly when it already works in normalised
    coordinates.  The pipeline fills in missing error values from the frame
    shape.
    """

    x: float | None = None
    y: float | None = None
    width: float = 0.0
    height: float = 0.0
    confidence: float = 0.0
    label: str | None = None
    visible: bool = True
    ex: float | None = None
    ey: float | None = None
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def empty(cls, *, timestamp: float | None = None) -> Target:
        """Return a standard no-target result."""

        return cls(
            visible=False,
            confidence=0.0,
            timestamp=time.time() if timestamp is None else timestamp,
        )

    @property
    def target_x(self) -> float:
        """Compatibility alias for the original project API."""

        return 0.0 if self.x is None else self.x

    @property
    def target_y(self) -> float:
        """Compatibility alias for the original project API."""

        return 0.0 if self.y is None else self.y

    @property
    def center(self) -> tuple[float, float]:
        """Pixel centre as an ``(x, y)`` tuple."""

        return self.target_x, self.target_y

    @property
    def error(self) -> TrackingError:
        """Return the normalised error represented by this target."""

        return TrackingError(
            x=0.0 if self.ex is None else self.ex,
            y=0.0 if self.ey is None else self.ey,
            timestamp=self.timestamp,
        )

    def set_error(self, error: TrackingError) -> Target:
        """Store a normalised error and return ``self`` for fluent use."""

        self.ex = error.x
        self.ey = error.y
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "x": self.x,
            "y": self.y,
            "target_x": self.target_x,
            "target_y": self.target_y,
            "width": self.width,
            "height": self.height,
            "confidence": self.confidence,
            "label": self.label,
            "visible": self.visible,
            "ex": self.ex,
            "ey": self.ey,
            "metadata": dict(self.metadata),
        }


@dataclass
class MotionCommand:
    """A transport-neutral robot motion command.

    Pan/tilt robots use ``yaw`` and ``pitch``.  Mobile or custom robots can
    use the optional Cartesian/angular fields without changing the pipeline.
    """

    yaw: float = 0.0
    pitch: float = 0.0
    linear_x: float = 0.0
    linear_y: float = 0.0
    linear_z: float = 0.0
    angular_x: float = 0.0
    angular_y: float = 0.0
    angular_z: float = 0.0
    timestamp: float = field(default_factory=time.time)
    frame_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def stop(cls, *, metadata: dict[str, Any] | None = None) -> MotionCommand:
        """Return an explicit stop command."""

        return cls(metadata={} if metadata is None else dict(metadata))

    @property
    def magnitude(self) -> float:
        """L1 magnitude of all command channels."""

        return sum(
            abs(value)
            for value in (
                self.yaw,
                self.pitch,
                self.linear_x,
                self.linear_y,
                self.linear_z,
                self.angular_x,
                self.angular_y,
                self.angular_z,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "yaw": self.yaw,
            "pitch": self.pitch,
            "linear_x": self.linear_x,
            "linear_y": self.linear_y,
            "linear_z": self.linear_z,
            "angular_x": self.angular_x,
            "angular_y": self.angular_y,
            "angular_z": self.angular_z,
            "frame_id": self.frame_id,
            "metadata": dict(self.metadata),
        }

@dataclass
class PipelineResult:
    """The complete result of one camera-to-command cycle."""

    target: Target
    error: TrackingError
    command: MotionCommand
    state: str
    timestamp: float = field(default_factory=time.time)


def coerce_mapping(value: Mapping[str, Any]) -> Target:
    """Convert a detector dictionary into a :class:`Target`.

    This helper is public so custom detectors can return a plain dictionary
    while still benefiting from the common contract.
    """

    x = value.get("x", value.get("target_x", value.get("center_x")))
    y = value.get("y", value.get("target_y", value.get("center_y")))
    return Target(
        x=None if x is None else float(x),
        y=None if y is None else float(y),
        width=float(value.get("width", 0.0) or 0.0),
        height=float(value.get("height", 0.0) or 0.0),
        confidence=float(value.get("confidence", value.get("score", 0.0)) or 0.0),
        label=value.get("label", value.get("class_name")),
        visible=bool(
            value.get(
                "visible",
                (x is not None and y is not None)
                or (value.get("ex") is not None and value.get("ey") is not None),
            )
        ),
        ex=None if value.get("ex") is None else float(value["ex"]),
        ey=None if value.get("ey") is None else float(value["ey"]),
        timestamp=float(value.get("timestamp", time.time())),
        metadata=dict(value.get("metadata", {})),
    )


__all__ = [
    "MotionCommand",
    "PipelineResult",
    "Target",
    "TrackingError",
    "coerce_mapping",
]
