from __future__ import annotations

import importlib


__all__ = [
    "FixedMeasurementRequest",
    "FixedMeasurementRecord",
    "FixedOpticalRecord",
    "run_fixed_measurement",
    "record_fixed_optical_states",
]

_LAZY_EXPORTS = {
    "FixedMeasurementRequest": ("experiment", "FixedMeasurementRequest"),
    "FixedMeasurementRecord": ("experiment", "FixedMeasurementRecord"),
    "FixedOpticalRecord": ("optics.records", "FixedOpticalRecord"),
    "run_fixed_measurement": ("experiment", "run_fixed_measurement"),
    "record_fixed_optical_states": (
        "optics.records",
        "record_fixed_optical_states",
    ),
}


def __getattr__(name: str) -> object:
    """Load Fixed implementation only when a caller requests one export."""
    export = _LAZY_EXPORTS.get(name)
    if export is None:
        raise AttributeError(name)
    module_name, attribute_name = export
    module = importlib.import_module(f"{__name__}.{module_name}")
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value
