"""Small signal filters used by compatibility integrations."""

from __future__ import annotations

from collections import deque
from numbers import Real


class EMAFilter:
    """Bounded-history exponential moving average."""

    def __init__(
        self,
        alpha: float = 0.5,
        initial: float | None = None,
        *,
        history_limit: int = 100,
    ) -> None:
        if not 0 < alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")
        if history_limit <= 0:
            raise ValueError("history_limit must be positive")
        self.alpha = float(alpha)
        self._value = 0.0 if initial is None else float(initial)
        self._has_value = initial is not None
        self._history: deque[float] = deque(maxlen=history_limit)

    @property
    def value(self) -> float:
        return self._value

    @property
    def has_value(self) -> bool:
        return self._has_value

    def update(self, value: Real) -> float:
        current = float(value)
        if not self._has_value:
            self._value = current
            self._has_value = True
        else:
            self._value = self.alpha * current + (1 - self.alpha) * self._value
        self._history.append(current)
        return self._value


__all__ = ["EMAFilter"]
