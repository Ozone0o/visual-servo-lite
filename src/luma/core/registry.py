"""Tiny, explicit plugin registries used by the built-in components."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class PluginRegistry(Generic[T]):
    """Name-to-factory registry with a decorator-friendly API."""

    def __init__(self, kind: str) -> None:
        self.kind = kind
        self._factories: dict[str, Callable[..., T]] = {}

    def register(
        self,
        name: str,
        factory: Callable[..., T] | None = None,
        *,
        replace: bool = False,
    ):
        """Register a factory, or return a decorator when ``factory`` is None."""

        key = name.strip().lower()
        if not key:
            raise ValueError(f"{self.kind} plugin name cannot be empty")

        def add(item: Callable[..., T]) -> Callable[..., T]:
            if key in self._factories and not replace:
                raise ValueError(f"{self.kind} plugin already registered: {key}")
            self._factories[key] = item
            return item

        return add if factory is None else add(factory)

    def get(self, name: str) -> Callable[..., T]:
        key = name.strip().lower()
        try:
            return self._factories[key]
        except KeyError as exc:
            available = ", ".join(self.names()) or "none"
            raise KeyError(f"Unknown {self.kind} plugin {name!r}; available: {available}") from exc

    def create(self, name: str, *args: Any, **kwargs: Any) -> T:
        return self.get(name)(*args, **kwargs)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))

    def __contains__(self, name: str) -> bool:
        return name.strip().lower() in self._factories

    def __iter__(self) -> Iterator[str]:
        return iter(self.names())


__all__ = ["PluginRegistry"]
