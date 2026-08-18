"""Detector base class and result coercion helpers."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Mapping
from typing import Any

from luma.core.interfaces import Detector
from luma.models import Target, coerce_mapping


class BaseDetector(Detector):
    """Common functionality for detector plugins."""

    @abstractmethod
    def detect(self, frame: Any) -> Target:
        """Return a :class:`~luma.models.Target` for one frame."""

    @staticmethod
    def normalize_error(
        px: float,
        py: float,
        frame_w: int,
        frame_h: int,
    ) -> tuple[float, float]:
        """Convert pixel coordinates to a clipped image-space error."""

        if frame_w <= 0 or frame_h <= 0:
            raise ValueError("frame dimensions must be positive")
        ex = (float(px) - frame_w / 2.0) / (frame_w / 2.0)
        ey = (float(py) - frame_h / 2.0) / (frame_h / 2.0)
        return max(-1.0, min(1.0, ex)), max(-1.0, min(1.0, ey))


def _value(value: Any, *names: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        for name in names:
            if name in value:
                return value[name]
    for name in names:
        if hasattr(value, name):
            return getattr(value, name)
    return default


def coerce_target(result: Any, frame: Any | None = None) -> Target:
    """Coerce common custom detector return values into ``Target``.

    Supported values are ``Target``, dictionaries, ``(x, y)`` tuples and
    simple objects exposing ``x``/``y`` or ``center`` attributes.
    """

    if isinstance(result, Target):
        return result
    if result is None or result is False:
        return Target.empty()
    if isinstance(result, Mapping):
        return coerce_mapping(result)
    if isinstance(result, (tuple, list)) and len(result) >= 2:
        return Target(x=float(result[0]), y=float(result[1]), confidence=1.0)

    center = _value(result, "center", default=None)
    if center is not None and len(center) >= 2:
        x, y = center[0], center[1]
    else:
        x = _value(result, "x", "target_x", "center_x", default=None)
        y = _value(result, "y", "target_y", "center_y", default=None)
    if x is None or y is None:
        return Target.empty()

    return Target(
        x=float(x),
        y=float(y),
        width=float(_value(result, "width", default=0.0) or 0.0),
        height=float(_value(result, "height", default=0.0) or 0.0),
        confidence=float(_value(result, "confidence", "score", default=1.0) or 0.0),
        label=_value(result, "label", "class_name", default=None),
        visible=bool(_value(result, "visible", default=True)),
        ex=(
            None
            if _value(result, "ex", "error_x", default=None) is None
            else float(_value(result, "ex", "error_x"))
        ),
        ey=(
            None
            if _value(result, "ey", "error_y", default=None) is None
            else float(_value(result, "ey", "error_y"))
        ),
        metadata=dict(_value(result, "metadata", default={}) or {}),
    )


__all__ = ["BaseDetector", "coerce_target"]
