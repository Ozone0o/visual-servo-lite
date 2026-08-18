"""Optional AprilTag detector plugin.

The dependency is loaded only when the detector is used, so installing Luma
for colour tracking does not pull in a native AprilTag stack.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover - depends on the installation extra
    cv2 = None

from luma.detectors.base import BaseDetector
from luma.models import Target


class AprilTagDetector(BaseDetector):
    """Detect one AprilTag using ``pupil-apriltags`` or an injected backend."""

    def __init__(
        self,
        *,
        families: str = "tag36h11",
        tag_id: int | None = None,
        min_confidence: float = 0.0,
        detector: Any | None = None,
        camera_params: Iterable[float] | None = None,
        tag_size: float | None = None,
    ) -> None:
        self.families = families
        self.tag_id = tag_id
        self.min_confidence = min_confidence
        self._detector = detector
        self.camera_params = tuple(camera_params) if camera_params is not None else None
        self.tag_size = tag_size

    def _backend(self) -> Any:
        if self._detector is not None:
            return self._detector
        try:
            from pupil_apriltags import Detector as PupilDetector
        except ImportError as exc:
            raise ImportError(
                "AprilTagDetector requires 'pupil-apriltags'. "
                "Install with: pip install luma[apriltag]"
            ) from exc
        self._detector = PupilDetector(families=self.families)
        return self._detector

    def detect(self, frame: np.ndarray) -> Target:
        if cv2 is None:
            raise ImportError(
                "AprilTagDetector requires OpenCV; install with: pip install luma[vision]"
            )
        height, width = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        backend = self._backend()
        kwargs: dict[str, Any] = {}
        if self.camera_params is not None and self.tag_size is not None:
            kwargs.update(
                estimate_tag_pose=True,
                camera_params=self.camera_params,
                tag_size=self.tag_size,
            )
        try:
            detections = backend.detect(gray, **kwargs)
        except TypeError:
            # A small injected test backend often accepts only the image.
            detections = backend.detect(gray)
        candidates = [item for item in (detections or []) if self._matches(item)]
        if not candidates:
            return Target.empty()
        detection = max(candidates, key=self._confidence)
        center = self._center(detection)
        corners = np.asarray(getattr(detection, "corners", []), dtype=float)
        if corners.size:
            corners = corners.reshape(-1, 2)
            x, y = corners.min(axis=0)
            max_x, max_y = corners.max(axis=0)
            box_width, box_height = max_x - x, max_y - y
        else:
            box_width = box_height = 0.0
        ex, ey = self.normalize_error(center[0], center[1], width, height)
        return Target(
            x=float(center[0]),
            y=float(center[1]),
            width=float(box_width),
            height=float(box_height),
            confidence=self._confidence(detection),
            label=f"apriltag:{getattr(detection, 'tag_id', 'unknown')}",
            ex=ex,
            ey=ey,
            metadata={"tag_id": getattr(detection, "tag_id", None)},
        )

    def _matches(self, detection: Any) -> bool:
        if self.tag_id is not None and getattr(detection, "tag_id", None) != self.tag_id:
            return False
        return self._confidence(detection) >= self.min_confidence

    @staticmethod
    def _confidence(detection: Any) -> float:
        margin = getattr(detection, "decision_margin", None)
        if margin is None:
            return float(getattr(detection, "confidence", 1.0))
        return max(0.0, min(1.0, float(margin) / 100.0))

    @staticmethod
    def _center(detection: Any) -> tuple[float, float]:
        center = getattr(detection, "center", None)
        if center is not None:
            return float(center[0]), float(center[1])
        corners = np.asarray(getattr(detection, "corners"), dtype=float).reshape(-1, 2)
        point = corners.mean(axis=0)
        return float(point[0]), float(point[1])


AprilTag = AprilTagDetector


__all__ = ["AprilTag", "AprilTagDetector"]
