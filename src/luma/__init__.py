"""Luma — lightweight visual intelligence and servo control for robots.

Give robots eyes and motion.
"""

# Import built-ins so ``detector_registry.names()`` is useful immediately
# after ``import luma``.  Optional third-party dependencies remain lazy.
from luma import adapters as adapters  # noqa: E402,F401
from luma import controllers as controllers  # noqa: E402,F401
from luma import detectors as detectors  # noqa: E402,F401
from luma.core import Camera
from luma.core.pipeline import LumaPipeline, PipelineState
from luma.metrics import Metrics, MetricsRecorder
from luma.models import (
    MotionCommand,
    PipelineResult,
    Target,
    TrackingError,
)
from luma.registry import (
    adapter_registry,
    controller_registry,
    detector_registry,
    register_adapter,
    register_controller,
    register_detector,
)
from luma.safety import ChannelLimit, SafetyDecision, SafetyGate, SafetyLimits

__version__ = "0.2.0"

__all__ = [
    "Camera",
    "ChannelLimit",
    "LumaPipeline",
    "Metrics",
    "MetricsRecorder",
    "MotionCommand",
    "PipelineResult",
    "PipelineState",
    "Target",
    "TrackingError",
    "SafetyDecision",
    "SafetyGate",
    "SafetyLimits",
    "adapter_registry",
    "controller_registry",
    "detector_registry",
    "register_adapter",
    "register_controller",
    "register_detector",
]
