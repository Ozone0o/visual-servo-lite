"""Built-in controller plugins."""

from luma.controllers.base import BaseController, as_tracking_error
from luma.controllers.p_controller import DeadZonePController, PController
from luma.controllers.pid import PID, PIDController
from luma.controllers.smooth import SmoothController
from luma.registry import controller_registry, register_controller

controller_registry.register("p", PController)
controller_registry.register("pid", PIDController)
controller_registry.register("smooth", SmoothController)

__all__ = [
    "BaseController",
    "DeadZonePController",
    "PID",
    "PIDController",
    "PController",
    "SmoothController",
    "as_tracking_error",
    "controller_registry",
    "register_controller",
]
