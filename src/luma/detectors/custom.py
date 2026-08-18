"""Adapter for application-defined detector callables."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from luma.detectors.base import BaseDetector, coerce_target
from luma.models import Target


class CustomDetector(BaseDetector):
    """Wrap a function or object implementing ``detect(frame)``.

    The wrapped function may return a ``Target``, a mapping, a ``(x, y)``
    tuple, or an object with matching attributes.
    """

    def __init__(self, detector: Callable[[Any], Any] | Any) -> None:
        if not callable(detector) and not callable(getattr(detector, "detect", None)):
            raise TypeError("detector must be callable or expose detect(frame)")
        self.detector = detector

    def detect(self, frame: Any) -> Target:
        raw = self.detector(frame) if callable(self.detector) else self.detector.detect(frame)
        return coerce_target(raw, frame)


CallableDetector = CustomDetector


__all__ = ["CallableDetector", "CustomDetector"]
