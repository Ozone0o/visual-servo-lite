"""Public plugin registries.

Applications can register their own implementation once and construct it by
name from YAML or a command line flag:

    from luma.registry import detector_registry
    detector_registry.register("my-detector", MyDetector)
"""

from __future__ import annotations

from luma.core.registry import PluginRegistry

detector_registry: PluginRegistry = PluginRegistry("detector")
controller_registry: PluginRegistry = PluginRegistry("controller")
adapter_registry: PluginRegistry = PluginRegistry("adapter")


def register_detector(name: str):
    return detector_registry.register(name)


def register_controller(name: str):
    return controller_registry.register(name)


def register_adapter(name: str):
    return adapter_registry.register(name)


__all__ = [
    "PluginRegistry",
    "adapter_registry",
    "controller_registry",
    "detector_registry",
    "register_adapter",
    "register_controller",
    "register_detector",
]
