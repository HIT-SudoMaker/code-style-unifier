from __future__ import annotations

import math

import torch

from ...authority import Document, Reference
from ...field import (
    ComponentBasis,
    CoordinateFrame,
    Field,
    FieldComponent,
    Medium,
    PlaneSurface,
)
from ...field.debye import (
    AplanaticPupil,
    AplanaticSurface,
    PupilPolarization,
)
from ...field.debye_qualification import (
    form_aplanatic_reference,
    restore_aplanatic_reference_binding,
)
from ...field.fast_debye import CZTDebyeRealization, FFTDebyeRealization
from ..study import Study, Task

from .brief import Polarization, require_monochromatic_wavelength
from .design import MetalensDesign, require_metalens_design
from .evidence import MetalensEvidence
from .focal_field_comparison import focal_comparison_slices
from .focus import FocalRegion


def admit_aplanatic_reference(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Form and admit one aplanatic reference on its exact comparison plane.

    This private aim-owned Module forms one independently authored aplanatic
    reference on requested focal coordinates under the exact qualified joint
    FFT/CZT binding, then owns its Field materialization and admission.
    """

    fft_realization, czt_realization = _require_aplanatic_reference_binding(
        evidence,
        task,
    )
    region = evidence.restore_focal_region(study)
    design = require_metalens_design(study)
    reference = _form_aplanatic_reference(
        design,
        region,
        fft_realization=fft_realization,
        czt_realization=czt_realization,
        target_phase_reference=evidence.fact(
            study,
            "target_phase",
        ).reference,
    )
    admitted = evidence.admit_field(task, reference)
    return evidence.with_fact(study, task, admitted)


def _form_aplanatic_reference(
    design: MetalensDesign,
    region: FocalRegion,
    *,
    fft_realization: FFTDebyeRealization,
    czt_realization: CZTDebyeRealization,
    target_phase_reference: Reference,
) -> Field:
    rows, columns = region.shape
    row_slice, column_slice = focal_comparison_slices(
        region,
        numerical_aperture=float(design.numerical_aperture),
    )
    comparison_shape = (
        row_slice.stop - row_slice.start,
        column_slice.stop - column_slice.start,
    )
    horizontal = (
        torch.arange(
            column_slice.start,
            column_slice.stop,
            dtype=torch.float64,
            device=czt_realization.device,
        )
        - (columns - 1) / 2
    ) * region.spacing_m
    vertical = (
        torch.arange(
            row_slice.start,
            row_slice.stop,
            dtype=torch.float64,
            device=czt_realization.device,
        )
        - (rows - 1) / 2
    ) * region.spacing_m
    pupil = AplanaticPupil(
        surface=AplanaticSurface(
            focal_length_m=float(design.focal_length_um) * 1e-6,
            angular_radius_rad=math.asin(float(design.numerical_aperture)),
        ),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        medium_refractive_index=1.0,
        polarization=_pupil_polarization(design.incident_polarization),
        wavelength_m=(
            require_monochromatic_wavelength(design.operating_spectrum) * 1e-9
        ),
    )
    observation = form_aplanatic_reference(
        pupil,
        horizontal_axis_m=tuple(float(value) for value in horizontal.cpu().tolist()),
        vertical_axis_m=tuple(float(value) for value in vertical.cpu().tolist()),
        axial_offset_m=region.aplanatic_axial_offset_m,
        fft_realization=fft_realization,
        czt_realization=czt_realization,
    )
    return Field(
        wavelength_m=pupil.wavelength_m,
        surface=PlaneSurface(
            region.focus_plane_position_m,
            region.spacing_m,
            comparison_shape,
        ),
        frame=region.frame,
        medium=region.medium,
        basis=ComponentBasis.CARTESIAN,
        electric_components=tuple(
            _stored_component(name, values, comparison_shape)
            for name, values in zip(
                ("x", "y", "z"),
                observation.electric_components,
                strict=True,
            )
        ),
        source_references=(target_phase_reference,),
        incident_reference_power=1.0,
    )


def _require_aplanatic_reference_binding(
    evidence: MetalensEvidence,
    task: Task,
) -> tuple[FFTDebyeRealization, CZTDebyeRealization]:
    if task.binding_reference is None:
        raise RuntimeError("aplanatic_reference_binding_mismatch")
    try:
        document = Document.from_bytes(evidence.fetch(task.binding_reference))
        return restore_aplanatic_reference_binding(
            document,
            evidence.fetch,
        )
    except (FileNotFoundError, ValueError) as error:
        raise RuntimeError("aplanatic_reference_binding_mismatch") from error


def _pupil_polarization(incident: Polarization) -> PupilPolarization:
    if incident.kind == "linear":
        if incident.axis == "x":
            return PupilPolarization(1 + 0j, 0 + 0j)
        if incident.axis == "y":
            return PupilPolarization(0 + 0j, 1 + 0j)
    scale = math.sqrt(0.5)
    if incident.kind == "circular" and incident.handedness == "right":
        return PupilPolarization(scale + 0j, -1j * scale)
    if incident.kind == "circular" and incident.handedness == "left":
        return PupilPolarization(scale + 0j, 1j * scale)
    raise RuntimeError("debye_polarization_unsupported")


def _stored_component(
    name: str,
    values: torch.Tensor,
    shape: tuple[int, int],
) -> FieldComponent:
    stored = (
        values.reshape(shape)
        .detach()
        .to(device="cpu", dtype=torch.complex128)
        .numpy()
        .copy(order="C")
    )
    stored.setflags(write=False)
    return FieldComponent(name, stored)


__all__ = ["admit_aplanatic_reference"]
