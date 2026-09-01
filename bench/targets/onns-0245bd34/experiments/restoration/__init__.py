from __future__ import annotations

import importlib


__all__ = ["optical_bench", "fixed_measurement", "adaptive_measurement"]


def __getattr__(name: str) -> object:
    """Load the shared optical bench or either research-line namespace."""
    if name not in __all__:
        raise AttributeError(name)
    module = importlib.import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module
