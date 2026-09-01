from __future__ import annotations

import torch

from .field import OpticalField, _has_same_source_lineage


def _has_device_placement_mismatch(
    field_1: OpticalField,
    field_2: OpticalField,
) -> bool:
    envelope_device = field_1.envelope.device
    return (
        field_2.envelope.device != envelope_device
        or any(
            isinstance(length, torch.Tensor)
            and length.device != field.envelope.device
            for field in (field_1, field_2)
            for length in field.path_reference.lengths
        )
    )

def _collect_coherent_field_findings(
    field_1: OpticalField,
    field_2: OpticalField,
    *,
    prefix: str,
) -> list[str]:
    findings: list[str] = []
    if field_1.spectrum.wavelengths != field_2.spectrum.wavelengths:
        findings.append(prefix + "frequency_mismatch")
    if field_1.spectrum.weights != field_2.spectrum.weights:
        findings.append(prefix + "spectral_weight_mismatch")
    if (
        field_1.polarization_representation
        is not field_2.polarization_representation
    ):
        findings.append(prefix + "polarization_mismatch")
    if field_1.medium.physical_identity() != field_2.medium.physical_identity():
        findings.append(prefix + "medium_mismatch")
    if not field_1.grid.is_inference_compatible_with(field_2.grid):
        findings.append(prefix + "grid_mismatch")
    if field_1.normalization is not field_2.normalization:
        findings.append(prefix + "normalization_mismatch")
    if field_1.envelope_shape != field_2.envelope_shape:
        findings.append(prefix + "axis_mismatch")
    if field_1.envelope.dtype is not field_2.envelope.dtype:
        findings.append(prefix + "precision_mismatch")
    if not _has_same_source_lineage(field_1, field_2):
        findings.append(prefix + "source_lineage_mismatch")
    if _has_device_placement_mismatch(field_1, field_2):
        findings.append(prefix + "device_mismatch")
    return findings
