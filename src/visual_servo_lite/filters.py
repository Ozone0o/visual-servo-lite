"""滤波工具函数.

目前提供 EMA（指数移动平均）滤波，供外部 pipeline 或其他模块使用.
"""

from __future__ import annotations

from collections import deque
from typing import TypeVar

T = TypeVar("T", float, int)


class EMAFilter:
    """指数移动平均滤波器.

    用法:
        ema = EMAFilter(alpha=0.3)
        ema.update(1.5)
        value = ema.value  # 当前平滑值
    """

    def __init__(self, alpha: float = 0.3, initial: T | None = None) -> None:
        """初始化 EMA 滤波器.

        Args:
            alpha: 平滑系数 (0, 1]. 越大越贴近原始值.
            initial: 初始值，None 表示尚未有值.
        """
        self.alpha = alpha
        self._value: T | None = initial
        self._history: deque[T] = deque(maxlen=100)

    @property
    def value(self) -> T:
        """当前 EMA 值. 如果尚未 update 过，返回 0."""
        if self._value is None:
            return 0  # type: ignore[return-value]
        return self._value

    @property
    def has_value(self) -> bool:
        return self._value is not None

    def update(self, new_value: T) -> T:
        """输入新值，返回更新后的 EMA 值.

        Args:
            new_value: 新的观测值.

        Returns:
            更新后的 EMA 值.
        """
        if self._value is None:
            self._value = new_value
        else:
            self._value = self.alpha * new_value + (1 - self.alpha) * self._value  # type: ignore[assignment]
        self._history.append(self._value)
        return self.value
