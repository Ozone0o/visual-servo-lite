"""YAML configuration helpers for the Luma CLI and applications."""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: dict[str, Any] = {
    "detector": {
        "name": "color",
        "lower_h": 0,
        "lower_s": 100,
        "lower_v": 100,
        "upper_h": 20,
        "upper_s": 255,
        "upper_v": 255,
        "min_area": 100,
    },
    "controller": {
        "name": "smooth",
        "kp": 8.0,
        "yaw_gain": 1.0,
        "pitch_gain": 1.0,
        "dead_zone": 0.05,
        "ema_alpha": 0.3,
        "max_single_cmd_yaw": 5.0,
        "max_single_cmd_pitch": 5.0,
        "command_rate": 30.0,
        "alpha": 0.25,
        "max_output": 5.0,
    },
    "adapter": {"name": "mock"},
    "pan_tilt": {},
    "pipeline": {"lost_timeout": 1.0, "lost_behavior": "stop"},
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load a YAML file over the safe built-in defaults."""

    config = copy.deepcopy(DEFAULT_CONFIG)
    if path is None:
        return config
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Luma config does not exist: {source}")
    with source.open(encoding="utf-8") as handle:
        user_config = yaml.safe_load(handle) or {}
    if not isinstance(user_config, dict):
        raise ValueError("Luma config root must be a mapping")
    return deep_merge(config, user_config)


def build_components(
    config: dict[str, Any],
    *,
    custom_detector: Any | None = None,
    custom_adapter: Any | None = None,
) -> tuple[Any, Any, Any]:
    """Build detector, controller and adapter instances from config."""

    # Importing the packages registers built-ins exactly once.
    from luma.adapters import CustomRobotAdapter
    from luma.detectors import CustomDetector
    from luma.registry import adapter_registry, controller_registry, detector_registry

    detector_cfg = dict(config.get("detector", {}))
    detector_name = detector_cfg.pop("name", "color")
    if detector_name == "custom":
        if custom_detector is None:
            raise ValueError("custom detector selected but custom_detector was not supplied")
        detector = CustomDetector(custom_detector)
    else:
        detector = detector_registry.create(detector_name, **detector_cfg)

    controller_cfg = dict(config.get("controller", {}))
    controller_name = controller_cfg.pop("name", "p")
    if controller_name == "smooth":
        controller_cfg = {
            "kp": controller_cfg.get("kp", controller_cfg.get("yaw_gain", 1.0)),
            "alpha": controller_cfg.get("alpha", controller_cfg.get("ema_alpha", 0.25)),
            "max_output": controller_cfg.get(
                "max_output", controller_cfg.get("max_single_cmd_yaw")
            ),
        }
    elif controller_name == "p":
        controller_cfg = {
            "kp": controller_cfg.get("kp", controller_cfg.get("yaw_gain", 1.0)),
            "kp_y": controller_cfg.get("kp_y", controller_cfg.get("pitch_gain")),
            "dead_zone": controller_cfg.get("dead_zone", 0.0),
            "max_output": controller_cfg.get("max_output"),
        }
        controller_cfg = {key: value for key, value in controller_cfg.items() if value is not None}
    controller = controller_registry.create(controller_name, **controller_cfg)

    adapter_cfg = dict(config.get("adapter", {}))
    adapter_name = adapter_cfg.pop("name", "mock")
    if adapter_name == "custom":
        if custom_adapter is None:
            raise ValueError("custom adapter selected but custom_adapter was not supplied")
        adapter = CustomRobotAdapter(custom_adapter)
    else:
        adapter = adapter_registry.create(adapter_name, **adapter_cfg)
    return detector, controller, adapter


__all__ = [
    "DEFAULT_CONFIG",
    "build_components",
    "deep_merge",
    "load_config",
]
