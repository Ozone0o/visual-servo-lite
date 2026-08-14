"""Tests for EMAFilter."""

from __future__ import annotations

from visual_servo_lite.filters import EMAFilter


class TestEMAFilter:
    """测试 EMAFilter 类。"""

    def test_initial_value(self):
        ema = EMAFilter(alpha=0.5, initial=None)
        assert ema.value == 0
        assert ema.has_value is False

    def test_initial_value_set(self):
        ema = EMAFilter(alpha=0.5, initial=10.0)
        assert ema.value == 10.0
        assert ema.has_value is True

    def test_first_update(self):
        ema = EMAFilter(alpha=0.5, initial=None)
        result = ema.update(4.0)
        assert result == 4.0
        assert ema.value == 4.0
        assert ema.has_value is True

    def test_smoothing(self):
        ema = EMAFilter(alpha=0.5, initial=0.0)
        ema.update(10.0)
        assert ema.value == 5.0
        ema.update(10.0)
        assert ema.value == 7.5

    def test_alpha_range(self):
        ema = EMAFilter(alpha=1.0, initial=0.0)
        ema.update(5.0)
        # alpha=1.0 应该完全跟随新值
        assert ema.value == 5.0

    def test_history(self):
        ema = EMAFilter(alpha=1.0, initial=0.0)
        for v in [1, 2, 3, 4, 5]:
            ema.update(v)
        assert len(ema._history) == 5

    def test_history_limit(self):
        ema = EMAFilter(alpha=1.0, initial=0.0)
        for v in range(150):
            ema.update(float(v))
        assert len(ema._history) == 100

    def test_integer_value(self):
        ema = EMAFilter(alpha=1.0, initial=0)
        ema.update(10)
        assert ema.value == 10
