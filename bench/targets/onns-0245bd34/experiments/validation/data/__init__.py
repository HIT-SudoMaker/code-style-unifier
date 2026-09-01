from __future__ import annotations

from importlib import import_module

__all__ = [
    "data_validation_utils",
    "run_data",
    "validate_degradation_scenarios",
    "validate_end_to_end_pipeline",
    "validate_raw_sources",
]

_MODULES = set(__all__)


def __getattr__(name: str) -> object:
    """
    延迟导入data validation子模块
    """
    if name in _MODULES:
        return import_module(f"{__name__}.{name}")
    message = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(message)
