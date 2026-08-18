"""Controller helpers and the public controller contract."""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from typing import Any

from luma.core.interfaces import Controller
from luma.models import Target, TrackingError


def as_tracking_error(value: TrackingError | Target | Mapping[str, Any] | Any) -> TrackingError:
    """Accept the common error-like values used by custom controllers."""

    if isinstance(value, TrackingError):
        return value
    if isinstance(value, Target):
        return value.error
    if isinstance(value, Mapping):
        return TrackingError(
            x=float(value.get("x", value.get("ex", 0.0))),
            y=float(value.get("y", value.get("ey", 0.0))),
        )
    return TrackingError(
        x=float(getattr(value, "x", getattr(value, "ex", 0.0))),
        y=float(getattr(value, "y", getattr(value, "ey", 0.0))),
    )


def clamp(value: float, limit: float | None) -> float:
    if limit is None:
        return value
    limit = abs(float(limit))
    return max(-limit, min(limit, value))


class BaseController(Controller):
    """Compatibility name for the Luma controller interface."""

    pass


class ControllerCallAdapter:
    """Adapt legacy controller call shapes once, outside the frame loop.

    The canonical controller contract is ``compute(error, *, dt)``. Older
    integrations used either one argument or ``(error, previous_command)``;
    their call shape is inspected during pipeline construction only.
    """

    def __init__(self, controller: object) -> None:
        self.controller = controller
        self._compute = getattr(controller, "compute")
        parameters = inspect.signature(self._compute).parameters
        dt_parameter = parameters.get("dt")
        if dt_parameter is not None:
            self._mode = (
                "dt_positional"
                if dt_parameter.kind is inspect.Parameter.POSITIONAL_ONLY
                else "dt_keyword"
            )
        elif any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
        ):
            self._mode = "dt_keyword"
        else:
            positional = [
                parameter
                for parameter in parameters.values()
                if parameter.kind
                in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            ]
            self._mode = "previous" if len(positional) >= 2 else "error"

    def compute(
        self,
        error: TrackingError,
        *,
        dt: float,
        previous: Any | None = None,
    ):
        if self._mode == "dt_positional":
            return self._compute(error, dt)
        if self._mode == "dt_keyword":
            return self._compute(error, dt=dt)
        if self._mode == "previous":
            return self._compute(error, previous)
        return self._compute(error)


def adapt_controller(controller: object) -> ControllerCallAdapter:
    """Return a one-time call-shape adapter for a controller instance."""

    if isinstance(controller, ControllerCallAdapter):
        return controller
    return ControllerCallAdapter(controller)


__all__ = [
    "BaseController",
    "ControllerCallAdapter",
    "adapt_controller",
    "as_tracking_error",
    "clamp",
]
