from __future__ import annotations

import json
import math
from pathlib import Path
import time
import tracemalloc

import numpy
import pytest
import torch

from metacraft.authority import reference_for
from metacraft.field import (
    ComponentBasis,
    CoordinateFrame,
    Field,
    FieldComponent,
    Medium,
    PlaneSurface,
)
from metacraft.field.angular_spectrum import (
    AngularSpectrumRealization,
    propagate_field,
)
from metacraft.field.vector_angular_spectrum import (
    VectorAngularSpectrumRealization,
    propagate_electromagnetic_field,
    survey_electromagnetic_field,
)
from metacraft.science.metalens import (
    FocalRegion,
    FocusSurvey,
    evaluate_focus,
    evaluate_vector_focus,
)
from metacraft.science.metalens.focus import observe_focal_region


DECISION = Path("docs/research/2026-08-12-propagation-parity-decision.json")


def test_low_na_linear_field_has_strict_transverse_parity_on_cpu() -> None:
    errors, power_error = _linear_parity("cpu")
    assert max(errors.values()) <= 1e-12
    assert power_error <= 1e-12


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
def test_low_na_linear_field_has_strict_transverse_parity_on_cuda() -> None:
    errors, power_error = _linear_parity(f"cuda:{torch.cuda.current_device()}")
    assert max(errors.values()) <= 2e-12
    assert power_error <= 2e-12


def test_current_period_and_pb_basis_block_natural_replacement() -> None:
    with pytest.raises(ValueError, match="vector_field_sampling_unsupported"):
        propagate_electromagnetic_field(
            _linear_field(spacing_m=480e-9),
            distance_m=1e-6,
            realization=VectorAngularSpectrumRealization("cpu", 1024**3),
        )
    with pytest.raises(ValueError, match="vector_field_basis_unsupported"):
        propagate_electromagnetic_field(
            _pb_field(),
            distance_m=1e-6,
            realization=VectorAngularSpectrumRealization("cpu", 1024**3),
        )


def test_machine_decision_matches_recomputed_parity_and_incomplete_seal() -> None:
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    assert decision["verdict"] == "dual_applicability"
    assert decision["seal"] == {
        "status": "incomplete",
        "blocking_gates": [
            "ticket07",
            "codex_harness",
            "claude_harness",
            "low_na_propagation_native",
            "high_na_pb_native",
        ],
    }
    claims = {item["claim"]: item for item in decision["claims"]}
    errors, power_error = _linear_parity("cpu")
    assert max(errors.values()) <= claims["low_na_linear_transverse_field"][
        "maximum_error"
    ]
    assert power_error <= claims["electromagnetic_power_conservation"][
        "maximum_error"
    ]
    assert claims["period_480_nm_sampling"]["status"] == "failed"
    assert claims["pb_circular_basis_and_power"]["status"] == "failed"


def test_machine_decision_covers_the_public_field_to_focus_matrix() -> None:
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    claims = {item["claim"]: item for item in decision["claims"]}

    assert {
        "pb_basis_projection",
        "sampling_at_half_wavelength",
        "sampling_480_nm_rejection",
        "axial_focus_agreement",
        "x_fwhm_agreement",
        "y_fwhm_agreement",
        "depth_of_focus_agreement",
        "transmission_fraction_agreement",
        "concentration_fraction_agreement",
        "focus_efficiency_agreement",
        "absolute_power_agreement",
        "cpu_memory_budget",
        "cuda_memory_budget",
        "recorded_journey_recomputation",
    } <= claims.keys()
    assert claims["absolute_power_agreement"]["status"] == "not_comparable"
    component, electromagnetic = _focus_pair("cpu")
    measured = {
        name: _relative_difference(component[name], electromagnetic[name])
        for name in component
    }
    for claim, metric in {
        "axial_focus_agreement": "found_focus_m",
        "x_fwhm_agreement": "x_fwhm_m",
        "y_fwhm_agreement": "y_fwhm_m",
        "depth_of_focus_agreement": "dof_m",
        "transmission_fraction_agreement": "transmitted_fraction",
        "concentration_fraction_agreement": "focused_fraction",
        "focus_efficiency_agreement": "focus_efficiency",
    }.items():
        assert measured[metric] == pytest.approx(claims[claim]["cpu_error"], abs=1e-15)
        assert measured[metric] <= claims[claim]["maximum_error"]


def test_public_focus_matrix_stays_within_cpu_memory_contract() -> None:
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    budget = decision["performance"]["public_focus_matrix"]["cpu"]
    tracemalloc.start()
    started = time.perf_counter()
    _focus_pair("cpu")
    runtime_seconds = time.perf_counter() - started
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert runtime_seconds <= 2.0
    assert peak_bytes <= budget["maximum_bytes"]
    assert budget["memory_status"] == "passed"


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
def test_public_focus_matrix_stays_within_cuda_memory_contract() -> None:
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    budget = decision["performance"]["public_focus_matrix"]["cuda"]
    device = f"cuda:{torch.cuda.current_device()}"
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    component, electromagnetic = _focus_pair(device)
    torch.cuda.synchronize(device)
    runtime_seconds = time.perf_counter() - started
    peak_bytes = torch.cuda.max_memory_allocated()
    assert runtime_seconds <= 5.0
    assert peak_bytes <= budget["maximum_bytes"]
    assert budget["memory_status"] == "passed"
    assert _relative_difference(
        component["focus_efficiency"], electromagnetic["focus_efficiency"]
    ) <= 0.01


def test_linear_projection_reaches_comparable_public_focus_metrics() -> None:
    component, electromagnetic = _focus_pair("cpu")
    for name in ("found_focus_m", "x_fwhm_m", "y_fwhm_m", "dof_m"):
        assert _relative_difference(component[name], electromagnetic[name]) <= 0.1
    for name in ("transmitted_fraction", "focused_fraction", "focus_efficiency"):
        assert _relative_difference(component[name], electromagnetic[name]) <= 0.01


def test_pb_projection_is_explicit_and_lossless() -> None:
    circular = _pb_field()
    linear = _circular_to_linear(circular)
    restored = _linear_to_circular(linear)
    for name in circular.component_names:
        assert numpy.allclose(restored.electric(name), circular.electric(name), atol=1e-14)
    propagated = propagate_electromagnetic_field(
        linear,
        distance_m=1e-6,
        realization=VectorAngularSpectrumRealization("cpu", 1024**3),
    )
    assert propagated.field.basis is ComponentBasis.CARTESIAN


def test_electromagnetic_sampling_accepts_the_edge_and_rejects_480_nm() -> None:
    edge = _linear_field(spacing_m=470e-9)
    propagated = propagate_electromagnetic_field(
        edge,
        distance_m=1e-6,
        realization=VectorAngularSpectrumRealization("cpu", 1024**3),
    )
    assert propagated.field.surface.spacing_m == 470e-9
    with pytest.raises(ValueError, match="vector_field_sampling_unsupported"):
        propagate_electromagnetic_field(
            _linear_field(spacing_m=480e-9),
            distance_m=1e-6,
            realization=VectorAngularSpectrumRealization("cpu", 1024**3),
        )


def _linear_parity(device: str) -> tuple[dict[str, float], float]:
    source = _linear_field(spacing_m=200e-9)
    component = propagate_field(
        source,
        distance_range_m=(1e-6, 2e-6),
        preferred_distance_m=1.5e-6,
        components=("x", "y"),
        realization=AngularSpectrumRealization(device, 1024**3),
    )
    electromagnetic = propagate_electromagnetic_field(
        source,
        distance_m=component.principal_distance_m,
        realization=VectorAngularSpectrumRealization(device, 1024**3),
    )
    errors = {
        name: _aligned_error(
            component.principal_field.electric(name),
            electromagnetic.field.electric(name),
        )
        for name in ("x", "y")
    }
    power_error = abs(
        electromagnetic.input_longitudinal_power_w
        - electromagnetic.output_longitudinal_power_w
    ) / electromagnetic.input_longitudinal_power_w
    return errors, power_error


def _focus_pair(device: str) -> tuple[dict[str, float], dict[str, float]]:
    wavelength = 400e-9
    spacing = 150e-9
    focal_length = 20e-6
    numerical_aperture = 0.5
    radius = focal_length * numerical_aperture / math.sqrt(1 - numerical_aperture**2)
    half_cells = math.ceil(radius / spacing)
    axis = numpy.arange(-half_cells, half_cells + 1) * spacing
    position_y, position_x = numpy.meshgrid(axis, axis, indexing="ij")
    radial = numpy.hypot(position_x, position_y)
    occupied = radial <= radius
    phase = -2 * numpy.pi / wavelength * (
        numpy.sqrt(focal_length**2 + radial**2) - focal_length
    )
    electric_x = numpy.zeros(radial.shape, dtype=numpy.complex128)
    electric_x[occupied] = 0.8 * numpy.exp(1j * phase[occupied])
    field = Field(
        wavelength_m=wavelength,
        surface=PlaneSurface(0.0, spacing, electric_x.shape),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        basis=ComponentBasis.TRANSVERSE_LINEAR,
        electric_components=(
            _component("x", electric_x),
            _component("y", numpy.zeros_like(electric_x)),
        ),
        source_references=(reference_for(b"parity focus field"),),
        incident_reference_power=float(0.64 * numpy.count_nonzero(occupied)),
    )
    component_propagation = propagate_field(
        field,
        distance_range_m=(0.8 * focal_length, 1.2 * focal_length),
        preferred_distance_m=focal_length,
        components=("x", "y"),
        realization=AngularSpectrumRealization(device, 1024**3),
    )
    component_region = observe_focal_region(
        component_propagation,
        field_reference=reference_for(b"component focus region"),
        expected_focus_m=focal_length,
    )
    component_focus = evaluate_focus(component_region, numerical_aperture=numerical_aperture)

    vector_survey = survey_electromagnetic_field(
        field,
        distance_range_m=(0.8 * focal_length, 1.2 * focal_length),
        preferred_distance_m=focal_length,
        realization=VectorAngularSpectrumRealization(device, 1024**3),
    )
    selected = vector_survey.selected_propagation
    vector_region = FocalRegion(
        wavelength_m=wavelength,
        spacing_m=spacing,
        expected_focus_m=focal_length,
        found_focus_m=selected.distance_m,
        focus_plane_position_m=selected.field.surface.position_m,
        observed_components=("x", "y", "z"),
        axial_distances_m=vector_survey.distances_m,
        axial_peak_intensities=vector_survey.peak_intensities,
        component_axial_peak_intensities=vector_survey.component_peak_intensities,
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
    vector_focus = evaluate_vector_focus(
        vector_region,
        numerical_aperture=math.nextafter(0.5, 1.0),
    )
    return _focus_metrics(component_focus), _focus_metrics(vector_focus)


def _focus_metrics(focus: FocusSurvey) -> dict[str, float]:
    x_width = focus.x_half_maximum.width_m
    y_width = focus.y_half_maximum.width_m
    depth = focus.depth_of_focus.width_m
    assert x_width is not None
    assert y_width is not None
    assert depth is not None
    return {
        "found_focus_m": focus.found_focus_m,
        "x_fwhm_m": x_width,
        "y_fwhm_m": y_width,
        "dof_m": depth,
        "transmitted_fraction": focus.transmitted_fraction,
        "focused_fraction": focus.focused_fraction,
        "focus_efficiency": focus.focus_efficiency,
    }


def _relative_difference(left: float, right: float) -> float:
    return abs(left - right) / max(abs(left), abs(right))


def _circular_to_linear(field: Field) -> Field:
    right = field.electric("right")
    left = field.electric("left")
    scale = math.sqrt(2)
    return Field(
        wavelength_m=field.wavelength_m,
        surface=field.surface,
        frame=field.frame,
        medium=field.medium,
        basis=ComponentBasis.TRANSVERSE_LINEAR,
        electric_components=(
            _component("x", (right + left) / scale),
            _component("y", 1j * (right - left) / scale),
        ),
        source_references=field.source_references,
        incident_reference_power=field.incident_reference_power,
    )


def _linear_to_circular(field: Field) -> Field:
    electric_x = field.electric("x")
    electric_y = field.electric("y")
    scale = math.sqrt(2)
    return Field(
        wavelength_m=field.wavelength_m,
        surface=field.surface,
        frame=field.frame,
        medium=field.medium,
        basis=ComponentBasis.CIRCULAR,
        electric_components=(
            _component("right", (electric_x - 1j * electric_y) / scale),
            _component("left", (electric_x + 1j * electric_y) / scale),
        ),
        source_references=field.source_references,
        incident_reference_power=field.incident_reference_power,
    )


def _aligned_error(observed: numpy.ndarray, reference: numpy.ndarray) -> float:
    scale = numpy.vdot(reference, observed) / numpy.vdot(reference, reference)
    return float(
        numpy.linalg.norm(observed - scale * reference)
        / numpy.linalg.norm(observed)
    )


def _linear_field(*, spacing_m: float) -> Field:
    size = 17
    axis = (numpy.arange(size) - (size - 1) / 2) * spacing_m
    position_y, position_x = numpy.meshgrid(axis, axis, indexing="ij")
    envelope = numpy.exp(
        -(position_x**2 + position_y**2) / (2 * (800e-9) ** 2)
    )
    phase = numpy.exp(1j * 0.08 * position_x / spacing_m)
    electric_x = envelope * phase
    return Field(
        wavelength_m=940e-9,
        surface=PlaneSurface(0.0, spacing_m, electric_x.shape),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        basis=ComponentBasis.TRANSVERSE_LINEAR,
        electric_components=(
            _component("x", electric_x),
            _component("y", 0.1j * electric_x),
        ),
        source_references=(reference_for(b"propagation parity field"),),
        incident_reference_power=1.0,
    )


def _pb_field() -> Field:
    linear = _linear_field(spacing_m=200e-9)
    return Field(
        wavelength_m=linear.wavelength_m,
        surface=linear.surface,
        frame=linear.frame,
        medium=linear.medium,
        basis=ComponentBasis.CIRCULAR,
        electric_components=(
            _component("right", linear.electric("x")),
            _component("left", linear.electric("y")),
        ),
        source_references=linear.source_references,
        incident_reference_power=linear.incident_reference_power,
    )


def _component(name: str, values: numpy.ndarray) -> FieldComponent:
    samples = numpy.asarray(values, dtype=numpy.complex128)
    samples.setflags(write=False)
    return FieldComponent(name, samples)
