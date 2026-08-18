"""Stable interfaces for Luma components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol

from luma.models import MotionCommand, Target, TrackingError


class Camera(Protocol):
    """Minimal camera source protocol understood by :meth:`LumaPipeline.run`."""

    def read(self) -> Any:
        """Return one image frame."""


class Detector(ABC):
    """Detector plugin contract: one frame in, one target out."""

    @abstractmethod
    def detect(self, frame: Any) -> Target:
        """Detect the configured target in ``frame``."""


class Controller(ABC):
    """Controller contract: a normalised tracking error to motion command."""

    @abstractmethod
    def compute(
        self,
        error: TrackingError,
        *,
        dt: float,
    ) -> MotionCommand:
        """Compute a motion command from the current tracking error.

        ``dt`` is keyword-only and always supplied by the pipeline. Legacy
        implementations are supported by a one-time adapter at construction.
        """

    def reset(self) -> None:
        """Reset stateful controller terms (integral, filters, etc.)."""


class RobotAdapter(ABC):
    """Robot output contract."""

    @abstractmethod
    def send(self, command: MotionCommand) -> bool:
        """Send one command; return whether the transport accepted it."""

    def close(self) -> None:
        """Release transport resources."""

    def __enter__(self) -> RobotAdapter:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


# These names make the intent obvious to new code while retaining the base
# Keep the contract names aligned across detectors, controllers and adapters.
BaseDetector = Detector
BaseController = Controller
BaseAdapter = RobotAdapter


__all__ = [
    "BaseAdapter",
    "BaseController",
    "BaseDetector",
    "Camera",
    "Controller",
    "Detector",
    "RobotAdapter",
]
