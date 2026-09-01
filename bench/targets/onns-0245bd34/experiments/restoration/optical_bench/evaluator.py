from __future__ import annotations

import torch

from experiments.restoration.optical_bench.configuration import OpticalBenchConfig
from experiments.restoration.optical_bench.propagation import (
    _propagate_interferometric_transfer,
)
from experiments.restoration.optical_bench.topology import DualArmFields


def propagate_evaluator_complex_transfer(
    input_field: torch.Tensor,
    processing_transfer: torch.Tensor,
    bench_config: OpticalBenchConfig,
    *,
    is_reference_enabled: bool = True,
    is_processing_enabled: bool = True,
    reference_phase_offset_radians: torch.Tensor | None = None,
) -> DualArmFields:
    """Evaluate an arbitrary complex-transfer upper bound on the shared bench."""
    return _propagate_interferometric_transfer(
        input_field,
        processing_transfer,
        bench_config,
        is_reference_enabled=is_reference_enabled,
        is_processing_enabled=is_processing_enabled,
        reference_phase_offset_radians=reference_phase_offset_radians,
    )
