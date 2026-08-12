"""测试配置模块."""

from __future__ import annotations

import pytest

from visual_servo_lite.config import build_configs, load_config
from visual_servo_lite.models import ControllerConfig, LostConfig, PanTiltConfig


class TestLoadConfig:
    def test_load_none_returns_defaults(self):
        cfg = load_config(None)
        assert cfg["controller"]["yaw_gain"] == 1.0
        assert cfg["controller"]["dead_zone"] == 0.05

    def test_build_configs_returns_tuple(self):
        cfg = load_config(None)
        pt, ctl, lost = build_configs(cfg)
        assert isinstance(pt, PanTiltConfig)
        assert isinstance(ctl, ControllerConfig)
        assert isinstance(lost, LostConfig)

    def test_custom_config_values(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            "controller:\n  yaw_gain: 2.0\n  dead_zone: 0.1\n",
            encoding="utf-8",
        )
        cfg = load_config(yaml_file)
        pt, ctl, lost = build_configs(cfg)
        assert ctl.yaw_gain == 2.0
        assert ctl.dead_zone == 0.1
