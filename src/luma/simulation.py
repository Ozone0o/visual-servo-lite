"""A deterministic camera/robot plant for development without hardware."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from luma.adapters.mock import MockAdapter
from luma.controllers.p_controller import PController
from luma.detectors.color import ColorDetector
from luma.models import MotionCommand
from luma.pipeline import LumaPipeline
from luma.safety import SafetyLimits


@dataclass
class SimulationState:
    """Normalised target error and a simple first-order robot plant."""

    error_x: float = -0.75
    error_y: float = 0.45
    plant_gain: float = 0.08

    @property
    def error_magnitude(self) -> float:
        return math.hypot(self.error_x, self.error_y)

    def apply(self, command: MotionCommand) -> None:
        # The sign convention matches PController: positive yaw reduces a
        # negative (left) image error, and negative pitch reduces a positive
        # (down) image error.
        self.error_x = float(np.clip(self.error_x + command.yaw * self.plant_gain, -1.0, 1.0))
        self.error_y = float(np.clip(self.error_y + command.pitch * self.plant_gain, -1.0, 1.0))


class SimulatedCamera:
    """Render the current simulation state as a red target on a black frame."""

    def __init__(
        self,
        state: SimulationState,
        *,
        width: int = 640,
        height: int = 480,
        radius: int = 22,
    ) -> None:
        self.state = state
        self.width = width
        self.height = height
        self.radius = radius

    def read(self) -> np.ndarray:
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        x = int(round(self.width / 2 + self.state.error_x * self.width / 2))
        y = int(round(self.height / 2 + self.state.error_y * self.height / 2))
        cv2.circle(frame, (x, y), self.radius, (0, 0, 255), -1)
        return frame

    def __iter__(self):
        while True:
            yield self.read()


class SimulatedRobotAdapter(MockAdapter):
    """Record commands and apply them to the simulated robot plant."""

    def __init__(self, state: SimulationState) -> None:
        super().__init__(name="simulation")
        self.state = state

    def send(self, command: MotionCommand) -> bool:
        accepted = super().send(command)
        self.state.apply(command)
        return accepted


@dataclass
class SimulationReport:
    """Outputs from :func:`run_simulation`."""

    errors: list[float] = field(default_factory=list)
    commands: list[MotionCommand] = field(default_factory=list)
    initial_error: float = 0.0
    final_error: float = 0.0

    @property
    def converged(self) -> bool:
        return self.final_error < self.initial_error

    def to_dict(self) -> dict[str, Any]:
        return {
            "steps": len(self.errors),
            "initial_error": round(self.initial_error, 6),
            "final_error": round(self.final_error, 6),
            "converged": self.converged,
        }


def run_simulation(
    *,
    steps: int = 30,
    initial_error_x: float = -0.75,
    initial_error_y: float = 0.45,
    plant_gain: float = 0.08,
) -> SimulationReport:
    """Run a small closed-loop simulation and return convergence metrics."""

    if steps <= 0:
        raise ValueError("steps must be positive")
    state = SimulationState(initial_error_x, initial_error_y, plant_gain)
    camera = SimulatedCamera(state)
    detector = ColorDetector(lower_v=50, min_area=50)
    controller = PController(kp=8.0, max_output=5.0)
    adapter = SimulatedRobotAdapter(state)
    # Simulation steps are intentionally generated without wall-clock delay;
    # disable the real-time publication limit while retaining finite-value and
    # actuator-envelope checks.
    pipeline = LumaPipeline(
        detector,
        controller,
        adapter,
        safety_limits=SafetyLimits(max_command_rate_hz=None),
    )
    initial = state.error_magnitude
    errors: list[float] = []
    commands: list[MotionCommand] = []
    for _ in range(steps):
        result = pipeline.step_and_send(camera.read())
        errors.append(result.error.magnitude)
        commands.append(result.command)
    return SimulationReport(
        errors=errors,
        commands=commands,
        initial_error=initial,
        final_error=state.error_magnitude,
    )


__all__ = [
    "SimulatedCamera",
    "SimulatedRobotAdapter",
    "SimulationReport",
    "SimulationState",
    "run_simulation",
]
