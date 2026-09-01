from __future__ import annotations

from collections.abc import Mapping

import torch

from ...authority import Document, Reference
from ...field import (
    ComponentBasis,
    Medium,
)
from ...field.angular_spectrum import (
    ANGULAR_SPECTRUM_REALIZATION,
    AngularSpectrumRealization,
)
from ...field.angular_spectrum import propagate_field as propagate_component_field
from ...field.evidence import restore_field
from ...field.vector_angular_spectrum import (
    VectorAngularSpectrumRealization,
    restore_vector_angular_spectrum_binding,
    survey_electromagnetic_field,
)
from ..study import Study, Task

from .aperture import Aperture, aperture_document, form_field as form_component_field
from .brief import require_monochromatic_wavelength
from .design import require_metalens_design
from .evidence import MetalensEvidence
from .focal_field_comparison import (
    centered_focal_slices,
    compare_vector_fields,
    require_matching_focal_field,
)
from .focus import FocalRegion
from .focus import evaluate_focus as evaluate_scientific_focus
from .focus import evaluate_vector_focus, observe_focal_region
from .height import HeightChoice


def admit_assigned_aperture(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
    aperture: Aperture,
) -> Study:
    """
    Record one assigned aperture through the shared metalens admission tail.

    Propagation and geometric phases feed distinct aperture computations into
    this one admission path; the tail is declared once here.
    """

    reference = evidence.admit_task(
        task,
        aperture_document(aperture),
        sources=aperture.evidence,
    )
    return evidence.with_fact(study, task, reference)


def admit_formed_field(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
    *,
    basis: ComponentBasis,
    component_channels: Mapping[str, str | None],
) -> Study:
    """
    Form and admit the aperture field through the shared metalens admission tail.

    Each strategy supplies only its component basis and channel mapping; the
    restore, form, admit, and record steps live once here.
    """

    require_coefficient_field_response(evidence.height_choice(study))
    aperture = _restore_aperture(evidence, study)
    aperture_reference = evidence.fact(study, "aperture").reference
    field = form_component_field(
        aperture,
        wavelength_m=(
            require_monochromatic_wavelength(
                require_metalens_design(study).operating_spectrum
            )
            * 1e-9
        ),
        surface_position_m=0.0,
        medium=Medium("air"),
        basis=basis,
        component_channels=component_channels,
        aperture_reference=aperture_reference,
    )
    reference = evidence.admit_field(task, field)
    return evidence.with_fact(study, task, reference)


def require_coefficient_field_response(height_choice: HeightChoice) -> None:
    """
    Keep G0 coefficients from claiming a complete multi-order output field.

    Qualified sampled reference surfaces use their separate field-formation
    path and therefore do not cross this coefficient-only boundary.
    """

    if height_choice.order_regime != "zeroth order":
        raise ValueError("coefficient_field_requires_zeroth_order")


def admit_propagated_field(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
    *,
    components: tuple[str, ...],
) -> Study:
    """
    Propagate and admit the focal region through the shared metalens admission tail.

    Each strategy names only the propagated components; the propagation geometry,
    focal observation, admission, and recording live once here.
    """

    realization = _require_angular_spectrum_binding(evidence, task)
    field = evidence.restore_field(study)
    field_reference = evidence.fact(study, "field").reference
    expected_focus_m = float(require_metalens_design(study).focal_length_um) * 1e-6
    propagation = propagate_component_field(
        field,
        distance_range_m=(
            0.8 * expected_focus_m,
            1.2 * expected_focus_m,
        ),
        preferred_distance_m=expected_focus_m,
        components=components,
        realization=realization,
    )
    region = observe_focal_region(
        propagation,
        field_reference=field_reference,
        expected_focus_m=expected_focus_m,
    )
    reference = evidence.admit_focal_region(
        task,
        region,
        field_reference=field_reference,
    )
    return evidence.with_fact(study, task, reference)


def admit_evaluated_focus(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
    *,
    leakage_component: str | None = None,
) -> Study:
    """
    Evaluate and record the focus through the shared metalens admission tail.

    Each strategy supplies only its leakage component (``None`` for propagation,
    the incident handedness for geometric phase); the evaluation and recording
    live once here.
    """

    region = evidence.restore_focal_region(study)
    focus = evaluate_scientific_focus(
        region,
        numerical_aperture=float(require_metalens_design(study).numerical_aperture),
        leakage_component=leakage_component,
    )
    return evidence.record_focus(
        study,
        task,
        focus,
        focal_region_reference=evidence.fact(
            study,
            "focal_region",
        ).reference,
    )


def admit_vector_focal_region(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Survey one vector field across the declared 0.8f--1.2f interval.
    """

    realization = _require_vector_angular_spectrum_binding(evidence, task)
    field = evidence.restore_field(study)
    field_reference = evidence.fact(study, "field").reference
    expected_focus_m = float(require_metalens_design(study).focal_length_um) * 1e-6
    survey = survey_electromagnetic_field(
        field,
        distance_range_m=(
            0.8 * expected_focus_m,
            1.2 * expected_focus_m,
        ),
        preferred_distance_m=expected_focus_m,
        realization=realization,
    )
    selected = survey.selected_propagation
    region = FocalRegion(
        wavelength_m=selected.field.wavelength_m,
        spacing_m=selected.field.surface.spacing_m,
        expected_focus_m=expected_focus_m,
        found_focus_m=selected.distance_m,
        focus_plane_position_m=selected.field.surface.position_m,
        observed_components=("x", "y", "z"),
        axial_distances_m=survey.distances_m,
        axial_peak_intensities=survey.peak_intensities,
        component_axial_peak_intensities=(survey.component_peak_intensities),
        frame=selected.field.frame,
        medium=selected.field.medium,
        basis=selected.field.basis,
        electric_components=selected.field.electric_components,
        magnetic_components=selected.field.magnetic_components,
        source_references=selected.field.source_references,
        incident_reference_power=selected.input_longitudinal_power_w,
        transmitted_aperture_power={},
        vector_input_power_w=selected.input_longitudinal_power_w,
        vector_output_power_w=selected.output_longitudinal_power_w,
        longitudinal_power_plane=selected.output_longitudinal_power,
        realization=selected.realization,
    )
    reference = evidence.admit_focal_region(
        task,
        region,
        field_reference=field_reference,
    )
    return evidence.with_fact(study, task, reference)


def admit_vector_focus(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Measure one admitted vector focus from its typed Poynting plane.

    The initial conclusion reconstructs one plane at the already admitted
    focus distance. Authority replay restores Focus without another Torch
    execution.
    """

    region = evidence.restore_focal_region(study)
    focus = evaluate_vector_focus(
        region,
        numerical_aperture=float(require_metalens_design(study).numerical_aperture),
    )
    return evidence.record_focus(
        study,
        task,
        focus,
        focal_region_reference=evidence.fact(
            study,
            "focal_region",
        ).reference,
    )


def admit_focal_field_comparison(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Compare and admit observed-versus-ideal vector field evidence.
    """

    region = evidence.restore_focal_region(study)
    ideal_fact = evidence.fact(study, "aplanatic_reference")
    ideal = restore_field(
        Document.from_bytes(evidence.fetch(ideal_fact.reference)),
        evidence.fetch,
    )
    comparison_shape = ideal.surface.shape
    row_slice, column_slice = centered_focal_slices(
        region.shape,
        comparison_shape,
    )
    require_matching_focal_field(
        region,
        ideal,
        comparison_shape=comparison_shape,
    )
    region_fact = evidence.fact(study, "focal_region")
    observed_binding = _required_reference(
        region_fact.binding_reference,
        "vector_angular_spectrum_binding_missing",
    )
    ideal_binding = _required_reference(
        ideal_fact.binding_reference,
        "aplanatic_reference_binding_missing",
    )
    if region.vector_output_power_w is None:
        raise RuntimeError("vector_output_power_missing")
    ideal_device = str(region.realization["device"])
    ideal_components = (
        torch.tensor(
            ideal.electric("x"),
            dtype=torch.complex128,
            device=ideal_device,
        ),
        torch.tensor(
            ideal.electric("y"),
            dtype=torch.complex128,
            device=ideal_device,
        ),
        torch.tensor(
            ideal.electric("z"),
            dtype=torch.complex128,
            device=ideal_device,
        ),
    )
    comparison = compare_vector_fields(
        {
            name: region.electric(name)[row_slice, column_slice]
            for name in ("x", "y", "z")
        },
        ideal_components,
        observed_field_reference=region_fact.reference,
        ideal_field_reference=ideal_fact.reference,
        observed_binding_reference=observed_binding,
        ideal_binding_reference=ideal_binding,
        observed_method="vector angular spectrum",
        ideal_method="CZT Richards--Wolf",
        input_longitudinal_power_w=region.incident_reference_power,
        output_longitudinal_power_w=region.vector_output_power_w,
    )
    reference = evidence.admit_task(
        task,
        comparison.document(),
        sources=(
            region_fact.reference,
            ideal_fact.reference,
            observed_binding,
            ideal_binding,
        ),
    )
    return evidence.with_fact(study, task, reference)


def _require_angular_spectrum_binding(
    evidence: MetalensEvidence,
    task: Task,
) -> AngularSpectrumRealization:
    if task.binding_reference is None:
        raise RuntimeError("angular_spectrum_binding_mismatch")
    try:
        document = Document.from_bytes(evidence.fetch(task.binding_reference))
    except (FileNotFoundError, ValueError) as error:
        raise RuntimeError("angular_spectrum_binding_mismatch") from error
    realization = document.values.get("realization")
    if (
        document.schema_identifier != "metacraft.binding.angular_spectrum_propagation"
        or document.values.get("operations") != ["propagate_field"]
        or document.values.get("qualified") is not True
        or not isinstance(realization, Mapping)
    ):
        raise RuntimeError("angular_spectrum_binding_mismatch")
    try:
        restored = AngularSpectrumRealization.from_mapping(realization)
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("angular_spectrum_binding_mismatch") from error
    if restored.identity != ANGULAR_SPECTRUM_REALIZATION:
        raise RuntimeError("angular_spectrum_binding_mismatch")
    return restored


def _require_vector_angular_spectrum_binding(
    evidence: MetalensEvidence,
    task: Task,
) -> VectorAngularSpectrumRealization:
    if task.binding_reference is None:
        raise RuntimeError("vector_angular_spectrum_binding_mismatch")
    return _restore_vector_realization(evidence, task.binding_reference)


def _restore_vector_realization(
    evidence: MetalensEvidence,
    reference: Reference,
) -> VectorAngularSpectrumRealization:
    try:
        return restore_vector_angular_spectrum_binding(
            Document.from_bytes(evidence.fetch(reference))
        )
    except (FileNotFoundError, ValueError) as error:
        raise RuntimeError("vector_angular_spectrum_binding_mismatch") from error


def _required_reference(
    reference: Reference | None,
    reason: str,
) -> Reference:
    if reference is None:
        raise RuntimeError(reason)
    return reference


def _restore_aperture(
    evidence: MetalensEvidence,
    study: Study,
) -> Aperture:
    reference = evidence.fact(study, "aperture").reference
    return Aperture.from_document(Document.from_bytes(evidence.fetch(reference)))
