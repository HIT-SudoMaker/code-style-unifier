from __future__ import annotations

from importlib import import_module

__all__ = [
    "run_layers",
    "validate_detection",
    "validate_diffraction",
    "validate_lens",
    "validate_modulation",
]

_MODULES = frozenset(__all__)


def __getattr__(name: str) -> object:
    """
    惰性加载 layer validation 子模块
    """
    if name in _MODULES:
        return import_module(f"{__name__}.{name}")
    message = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(message)
