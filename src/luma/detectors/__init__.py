"""Built-in detector plugins."""

from luma.detectors.apriltag import AprilTag, AprilTagDetector
from luma.detectors.base import BaseDetector, coerce_target
from luma.detectors.color import ColorDetector
from luma.detectors.custom import CallableDetector, CustomDetector
from luma.detectors.yolo import YOLO, YOLODetector
from luma.registry import detector_registry, register_detector

detector_registry.register("color", ColorDetector)
detector_registry.register("apriltag", AprilTagDetector)
detector_registry.register("yolo", YOLODetector)
detector_registry.register("custom", CustomDetector)

__all__ = [
    "AprilTag",
    "AprilTagDetector",
    "BaseDetector",
    "CallableDetector",
    "ColorDetector",
    "CustomDetector",
    "YOLODetector",
    "YOLO",
    "coerce_target",
    "detector_registry",
    "register_detector",
]
