"""Fast HSV colour detector with no machine-learning dependency."""

from __future__ import annotations

import logging

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover - depends on the installation extra
    cv2 = None

from luma.detectors.base import BaseDetector
from luma.models import Target

logger = logging.getLogger(__name__)


class ColorDetector(BaseDetector):
    """Detect the largest connected region in an HSV range.

    It is deliberately small and deterministic, which makes it useful for
    bring-up, hardware tests and the included simulation.
    """

    def __init__(
        self,
        lower_h: int = 0,
        lower_s: int = 100,
        lower_v: int = 100,
        upper_h: int = 20,
        upper_s: int = 255,
        upper_v: int = 255,
        min_area: int = 100,
        *,
        blur_kernel: int = 0,
    ) -> None:
        if cv2 is None:
            raise ImportError(
                "ColorDetector requires OpenCV; install with: pip install luma[vision]"
            )
        if min_area < 0:
            raise ValueError("min_area must be >= 0")
        if blur_kernel and (blur_kernel < 3 or blur_kernel % 2 == 0):
            raise ValueError("blur_kernel must be an odd number >= 3")
        self.lower_color = np.array([lower_h, lower_s, lower_v], dtype=np.uint8)
        self.upper_color = np.array([upper_h, upper_s, upper_v], dtype=np.uint8)
        self.min_area = int(min_area)
        self.blur_kernel = blur_kernel

    def detect(self, frame: np.ndarray) -> Target:
        if not hasattr(frame, "shape") or len(frame.shape) < 2:
            raise ValueError("ColorDetector expects an image array")
        height, width = frame.shape[:2]
        if width <= 0 or height <= 0:
            return Target.empty()

        image = frame
        if self.blur_kernel:
            image = cv2.GaussianBlur(image, (self.blur_kernel, self.blur_kernel), 0)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        if self.lower_color[0] <= self.upper_color[0]:
            mask = cv2.inRange(hsv, self.lower_color, self.upper_color)
        else:
            # Hue wraps at 180 (useful for reds split across the HSV edge).
            low = np.array([self.lower_color[0], self.lower_color[1], self.lower_color[2]])
            high = np.array([180, self.upper_color[1], self.upper_color[2]])
            low2 = np.array([0, self.lower_color[1], self.lower_color[2]])
            high2 = self.upper_color
            mask = cv2.bitwise_or(cv2.inRange(hsv, low, high), cv2.inRange(hsv, low2, high2))

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )
        if not contours:
            return Target.empty()
        contour = max(contours, key=cv2.contourArea)
        area = float(cv2.contourArea(contour))
        if area < self.min_area:
            return Target.empty()

        moments = cv2.moments(contour)
        if moments["m00"] == 0:
            return Target.empty()
        cx = float(moments["m10"] / moments["m00"])
        cy = float(moments["m01"] / moments["m00"])
        x, y, box_width, box_height = cv2.boundingRect(contour)
        ex, ey = self.normalize_error(cx, cy, width, height)
        confidence = 1.0 if self.min_area == 0 else min(1.0, area / self.min_area)
        return Target(
            x=cx,
            y=cy,
            width=float(box_width),
            height=float(box_height),
            confidence=confidence,
            visible=True,
            ex=ex,
            ey=ey,
            metadata={"area": area, "bbox": (x, y, box_width, box_height)},
        )


__all__ = ["ColorDetector"]
