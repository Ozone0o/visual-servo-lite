"""Safety-gate tests for the canonical Luma pipeline."""

from __future__ import annotations

import time

from luma import LumaPipeline, MotionCommand, SafetyGate, SafetyLimits, Target
from luma.adapters.mock import MockAdapter


class FixedDetector:
    def detect(self, frame) -> Target:
        return Target(ex=0.2, ey=0.0, visible=True)


class NonFiniteController:
    def compute(self, error, dt=None) -> MotionCommand:
        return MotionCommand(yaw=float("nan"))


class FailingDetector:
    def detect(self, frame):
        raise RuntimeError("camera failed")


class FailingAdapter(MockAdapter):
    def send(self, command: MotionCommand) -> bool:
        self.commands.append(command)
        return False


def test_non_finite_controller_output_becomes_stop() -> None:
    pipeline = LumaPipeline(FixedDetector(), NonFiniteController(), MockAdapter())

    result = pipeline.process(object())

    assert result.command.magnitude == 0.0
    assert "non_finite_yaw" in result.command.metadata["safety_violation"]


def test_detector_failure_is_a_safe_stop() -> None:
    pipeline = LumaPipeline(FailingDetector(), NonFiniteController(), MockAdapter())

    result = pipeline.process(object())

    assert result.command.magnitude == 0.0
    assert result.target.metadata["safety_fault"] == "detector_error:RuntimeError"


def test_stale_frame_is_rejected() -> None:
    pipeline = LumaPipeline(
        FixedDetector(),
        NonFiniteController(),
        MockAdapter(),
        safety_limits=SafetyLimits(max_frame_age=0.01),
    )

    result = pipeline.process(object(), timestamp=time.time() - 1.0)

    assert result.command.magnitude == 0.0
    assert "stale_frame" in result.command.metadata["safety_violation"]


def test_adapter_rejection_attempts_stop() -> None:
    adapter = FailingAdapter()
    pipeline = LumaPipeline(FixedDetector(), NonFiniteController(), adapter)

    result = pipeline.step_and_send(object())

    assert result.command.magnitude == 0.0
    assert len(adapter.commands) == 2
    assert adapter.commands[-1].magnitude == 0.0
    assert pipeline.last_adapter_error == "adapter_rejected_command"


def test_rate_limit_is_explicit_and_deterministic() -> None:
    gate = SafetyGate(SafetyLimits(max_command_rate_hz=10.0, max_frame_age=None))
    command = MotionCommand(yaw=1.0)

    first, first_decision = gate.enforce(command, now=0.0)
    second, second_decision = gate.enforce(command, now=0.01)

    assert first_decision.allowed is True
    assert first.magnitude == 1.0
    assert second_decision.allowed is False
    assert second.magnitude == 0.0
    assert "command_rate_limit" in second.metadata["safety_violation"]


def test_ros_clock_age_can_be_checked_without_wall_clock_conversion() -> None:
    gate = SafetyGate(SafetyLimits(max_frame_age=0.1))

    command, decision = gate.enforce(MotionCommand(), frame_age=0.25)

    assert decision.allowed is False
    assert command.magnitude == 0.0
    assert "stale_frame" in decision.reasons


def test_linear_and_angular_channels_have_independent_limits() -> None:
    gate = SafetyGate(
        SafetyLimits(
            max_command_rate_hz=None,
            channel_limits={
                "linear_x": {"max_value": 0.2, "max_delta": 0.1},
                "angular_z": {"max_value": 0.3, "max_delta": 0.1},
            },
        )
    )

    _, decision = gate.enforce(MotionCommand(linear_x=0.5))

    assert decision.allowed is False
    assert "linear_x_limit" in decision.reasons
