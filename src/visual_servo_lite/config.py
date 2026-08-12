"""配置文件加载与合并."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from visual_servo_lite.models import (
    ControllerConfig,
    LostConfig,
    PanTiltConfig,
)

logger = logging.getLogger(__name__)

# 默认配置
_DEFAULTS = {
    "pan_tilt": {
        "max_yaw": 90.0,
        "max_pitch": 45.0,
        "min_yaw": -90.0,
        "min_pitch": -45.0,
        "max_cmd_rate": 30.0,
    },
    "controller": {
        "yaw_gain": 1.0,
        "pitch_gain": 1.0,
        "dead_zone": 0.05,
        "ema_alpha": 0.3,
        "max_single_cmd_yaw": 5.0,
        "max_single_cmd_pitch": 5.0,
        "command_rate": 30.0,
    },
    "lost": {
        "short_lost_timeout": 1.0,
        "long_lost_timeout": 3.0,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """深度合并两个字典，override 优先."""
    result = base.copy()
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def load_config(path: str | Path | None) -> dict:
    """加载配置文件并合并默认值.

    Args:
        path: YAML 配置文件路径，None 则使用全默认值.

    Returns:
        合并后的配置字典.
    """
    cfg = _deep_merge(_DEFAULTS, {})
    if path and Path(path).exists():
        logger.info("加载配置文件: %s", path)
        with open(path, "r", encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
        cfg = _deep_merge(cfg, user_cfg)
    elif path:
        logger.warning("配置文件不存在: %s，使用全默认值")
    return cfg


def build_configs(cfg: dict) -> tuple[PanTiltConfig, ControllerConfig, LostConfig]:
    """从配置字典构建 dataclass 实例.

    Returns:
        (PanTiltConfig, ControllerConfig, LostConfig)
    """
    pt_cfg = PanTiltConfig(**cfg.get("pan_tilt", {}))
    ctl_cfg = ControllerConfig(**cfg.get("controller", {}))
    lost_cfg = LostConfig(**cfg.get("lost", {}))
    return pt_cfg, ctl_cfg, lost_cfg
