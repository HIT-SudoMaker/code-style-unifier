from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from data.configs.perturbation import PerturbationOperationConfig
from data.configs.perturbation_registry import (
    build_psf_kernel_metadata,
    operation_spec_for,
    PerturbationExecutionContext,
)
from data.types import SampleProvenance


def apply_perturbation_operations(
    image: np.ndarray,
    operations: Sequence[PerturbationOperationConfig],
    *,
    provenance: SampleProvenance,
    degradation_seed: int | None = None,
) -> tuple[np.ndarray, list[dict[str, object]], dict[str, object]]:
    """
    依次应用扰动算子并返回图像、算子记录和额外扰动元数据
    """
    output = image.astype(np.float32, copy=False)
    applied_operations: list[dict[str, object]] = []
    extra_metadata: dict[str, object] = {}
    context = PerturbationExecutionContext(
        provenance=provenance,
        degradation_seed=degradation_seed,
    )

    for operation in operations:
        result = operation_spec_for(operation).apply(output, operation, context)
        output = result.image
        applied_operations.append(result.operation_record)
        extra_metadata.update(result.extra_metadata)

    return output.astype(np.float32, copy=False), applied_operations, extra_metadata
