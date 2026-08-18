"""Tests for Luma configuration loading and component construction."""

from __future__ import annotations

from luma.config import build_components, load_config


class TestLoadConfig:
    def test_load_none_returns_defaults(self):
        cfg = load_config(None)
        assert cfg["controller"]["yaw_gain"] == 1.0
        assert cfg["controller"]["dead_zone"] == 0.05

    def test_build_components_returns_runtime_plugins(self):
        cfg = load_config(None)
        detector, controller, adapter = build_components(cfg)
        assert detector is not None
        assert controller is not None
        assert adapter is not None

    def test_custom_config_values(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            "controller:\n  name: p\n  kp: 2.0\n  dead_zone: 0.1\n",
            encoding="utf-8",
        )
        cfg = load_config(yaml_file)
        detector, controller, adapter = build_components(cfg)
        assert controller.kp_x == 2.0
        assert controller.dead_zone == 0.1
