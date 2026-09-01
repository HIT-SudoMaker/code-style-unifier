from __future__ import annotations

import inspect

import numpy
import pytest
import torch

import metacraft.field.vector_angular_spectrum as vector_module
from metacraft.authority import Document, reference_for
from metacraft.field import (ComponentBasis, CoordinateFrame, Field,
                             FieldComponent, Medium, PlaneSurface)
from metacraft.field._device_memory import AvailableDeviceMemory
from metacraft.field.vector_angular_spectrum import (
    VECTOR_ANGULAR_SPECTRUM_CAPABILITY, VECTOR_ANGULAR_SPECTRUM_REALIZATION,
    VectorAngularSpectrumRealization, observe_vector_angular_spectrum,
    propagate_electromagnetic_field, qualify_vector_angular_spectrum,
    restore_vector_angular_spectrum_binding, survey_electromagnetic_field,
    vector_angular_spectrum_binding)
from metacraft.science import Binding


def _component(name: str, values: numpy.ndarray) -> FieldComponent:
    samples = numpy.asarray(values, dtype=numpy.complex128)
    samples.setflags(write=False)
    return FieldComponent(name, samples)


def _sampled_field(size: int = 16) -> Field:
    wavelength_m = 800e-9
    spacing_m = 200e-9
    axis = (
        numpy.arange(size, dtype=numpy.float64) - (size - 1) / 2
    ) * spacing_m
    position_y, position_x = numpy.meshgrid(axis, axis, indexing="ij")
    envelope = numpy.exp(
        -(position_x**2 + position_y**2) / (2 * (600e-9) ** 2)
    )
    phase = numpy.exp(1j * 2 * numpy.pi * position_x / (8 * spacing_m))
    electric_x = envelope * phase
    electric_y = 0.25j * envelope * phase
    return Field(
        wavelength_m=wavelength_m,
        surface=PlaneSurface(0.0, spacing_m, electric_x.shape),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        basis=ComponentBasis.TRANSVERSE_LINEAR,
        electric_components=(
            _component("x", electric_x),
            _component("y", electric_y),
        ),
        source_references=(reference_for(b"sampled vector plane field"),),
        incident_reference_power=1.0,
    )


def test_cartesian_basis_extends_field_without_changing_existing_bases() -> None:
    """
    Let one Field carry recovered longitudinal components without a type tree.
    """

    assert ComponentBasis.TRANSVERSE_LINEAR.components == ("x", "y")
    assert ComponentBasis.CIRCULAR.components == ("right", "left")
    assert ComponentBasis.CARTESIAN.components == ("x", "y", "z")


def test_vector_angular_spectrum_is_one_separate_method() -> None:
    """
    Keep the vector method distinct from the componentwise implementation.
    """

    assert (
        VECTOR_ANGULAR_SPECTRUM_REALIZATION
        == "metacraft.field.vector_angular_spectrum"
    )
    assert VECTOR_ANGULAR_SPECTRUM_CAPABILITY == (
        "vector_angular_spectrum_propagation"
    )
    assert tuple(
        inspect.signature(propagate_electromagnetic_field).parameters
    ) == ("field", "distance_m", "realization")


def test_qualification_proves_oblique_wave_direct_field_and_power() -> None:
    """
    Qualify direction, transversality, components, phase, and Poynting power.
    """

    realization = VectorAngularSpectrumRealization(
        device="cpu",
        working_memory_bytes=1024**3,
    )

    qualification = qualify_vector_angular_spectrum(realization)
    facts = qualification.as_mapping()

    assert qualification.is_qualified
    assert qualification.wave_vector_error <= 1e-12
    assert qualification.transversality_error <= 1e-12
    assert qualification.phase_advance_error <= 1e-12
    assert qualification.longitudinal_recovery_error <= 1e-12
    assert qualification.direct_component_error <= 1e-12
    assert qualification.poynting_error <= 1e-12
    assert facts["applicability"] == {
        "component_basis": "transverse linear input; cartesian output",
        "coordinate_order": "y x",
        "evanescent_terms": "discarded",
        "magnetic_storage": "reconstructed transiently for power",
        "medium": "air or vacuum",
        "power_measure": "integrated longitudinal Poynting vector",
        "power_surface": (
            "full padded plane; returned field cropped to source window"
        ),
        "propagation_direction": "positive z",
        "sampling_bound": "spacing at most one half in-medium wavelength",
    }


def test_one_sampled_field_recovers_longitudinal_electric_and_power() -> None:
    """
    Propagate all coupled components on one selected Torch device.
    """

    source = _sampled_field()
    realization = VectorAngularSpectrumRealization(
        device="cpu",
        working_memory_bytes=1024**3,
    )

    propagated = propagate_electromagnetic_field(
        source,
        distance_m=2e-6,
        realization=realization,
    )

    assert propagated.field.basis is ComponentBasis.CARTESIAN
    assert propagated.field.component_names == ("x", "y", "z")
    assert propagated.field.magnetic_components == ()
    assert propagated.field.surface.position_m == pytest.approx(2e-6)
    assert numpy.max(numpy.abs(propagated.field.electric("z"))) > 0
    assert propagated.input_longitudinal_power_w > 0
    assert propagated.output_longitudinal_power_w == pytest.approx(
        propagated.input_longitudinal_power_w,
        rel=1e-12,
    )
    assert (
        propagated.output_longitudinal_power.surface
        == propagated.field.surface
    )
    assert propagated.output_longitudinal_power.power_density_w_per_m2.dtype is (
        torch.float64
    )
    assert torch.all(
        torch.isfinite(
            propagated.output_longitudinal_power.power_density_w_per_m2
        )
    )
    assert propagated.realization["device"] == "cpu"
    assert propagated.realization["complex_dtype"] == "complex128"


def test_vector_survey_measures_one_coupled_peak_and_refines_locally() -> None:
    """
    Keep axial search, coupled intensity, and principal field behind one seam.
    """

    source = _sampled_field()
    realization = VectorAngularSpectrumRealization(
        device="cpu",
        working_memory_bytes=1024**3,
    )

    survey = survey_electromagnetic_field(
        source,
        distance_range_m=(1e-6, 3e-6),
        preferred_distance_m=2e-6,
        realization=realization,
    )

    selected = survey.selected_propagation
    selected_index = survey.distances_m.index(selected.distance_m)
    component_intensities = tuple(
        numpy.abs(selected.field.electric(name)) ** 2
        for name in ("x", "y", "z")
    )
    expected_peak = float(numpy.max(sum(component_intensities)))

    assert survey.peak_intensities[selected_index] == pytest.approx(
        expected_peak
    )
    assert survey.peak_intensities[selected_index] < sum(
        survey.component_peak_intensities[name][selected_index]
        for name in ("x", "y", "z")
    )
    assert set(survey.component_peak_intensities) == {"x", "y", "z"}
    assert 17 <= len(survey.distances_m) <= 31
    assert selected.input_longitudinal_power_w == pytest.approx(
        selected.output_longitudinal_power_w,
        rel=1e-12,
    )


def test_vector_survey_prepares_one_spectrum_for_every_axial_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Transform the source once, then vectorize distance on prepared spectra."""

    fft2_calls = 0
    torch_fft2 = vector_module.torch.fft.fft2

    def counted_fft2(*args: object, **kwargs: object) -> torch.Tensor:
        nonlocal fft2_calls
        fft2_calls += 1
        return torch_fft2(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(vector_module.torch.fft, "fft2", counted_fft2)
    survey_electromagnetic_field(
        _sampled_field(),
        distance_range_m=(1e-6, 3e-6),
        preferred_distance_m=2e-6,
        realization=VectorAngularSpectrumRealization(
            device="cpu",
            working_memory_bytes=1024**3,
        ),
    )

    # The same two prepared source transforms drive the axial search and the
    # selected field/power materialization. The count is independent of the
    # sampled distances.
    assert fft2_calls == 2


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
def test_vectorized_survey_keeps_cpu_cuda_peak_parity() -> None:
    """Preserve the selected distance and coupled peaks across Torch devices."""

    source = _sampled_field()
    cpu = survey_electromagnetic_field(
        source,
        distance_range_m=(1e-6, 3e-6),
        preferred_distance_m=2e-6,
        realization=VectorAngularSpectrumRealization(
            device="cpu",
            working_memory_bytes=1024**3,
        ),
    )
    cuda = survey_electromagnetic_field(
        source,
        distance_range_m=(1e-6, 3e-6),
        preferred_distance_m=2e-6,
        realization=VectorAngularSpectrumRealization(
            device="cuda:0",
            working_memory_bytes=1024**3,
        ),
    )

    assert cuda.distances_m == cpu.distances_m
    assert cuda.selected_propagation.distance_m == (
        cpu.selected_propagation.distance_m
    )
    assert cuda.peak_intensities == pytest.approx(
        cpu.peak_intensities,
        rel=2e-12,
        abs=2e-12,
    )


def test_failed_selected_cuda_never_retries_on_cpu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Keep qualification failure on the exact selected CUDA realization.
    """

    realization = VectorAngularSpectrumRealization(
        device="cuda:0",
        working_memory_bytes=None,
    )

    observed_devices: list[str] = []

    def unavailable(device: str) -> AvailableDeviceMemory:
        observed_devices.append(device)
        raise RuntimeError("selected_cuda_failed")

    monkeypatch.setattr(
        vector_module,
        "observe_available_device_memory",
        unavailable,
    )

    qualification = qualify_vector_angular_spectrum(realization)

    assert not qualification.is_qualified
    assert qualification.realization == realization
    assert qualification.reason == "RuntimeError"
    assert observed_devices == ["cuda:0"]


@pytest.mark.parametrize(
    "device",
    ("cuda:", "cuda:-1", "cuda:0:1", "cuda:any", "cudafoo:0"),
)
def test_realization_rejects_malformed_cuda_device(device: str) -> None:
    """
    Accept only the exact non-negative CUDA ordinal form.
    """

    with pytest.raises(
        ValueError,
        match="vector_field_device_unsupported",
    ):
        VectorAngularSpectrumRealization(
            device=device,
            working_memory_bytes=None,
        )


def test_qualified_realization_round_trips_through_one_binding_document() -> None:
    """
    Bind the method through existing Document and Binding values.
    """

    qualification = qualify_vector_angular_spectrum(
        VectorAngularSpectrumRealization(
            device="cpu",
            working_memory_bytes=1024**3,
        )
    )
    document = vector_angular_spectrum_binding(qualification)
    restored = restore_vector_angular_spectrum_binding(
        Document.from_bytes(document.to_bytes())
    )
    binding = Binding(
        VECTOR_ANGULAR_SPECTRUM_CAPABILITY,
        reference_for(document.to_bytes()),
    )

    assert restored == qualification.realization
    assert binding.capability == VECTOR_ANGULAR_SPECTRUM_CAPABILITY


def test_binding_rejects_a_qualification_that_did_not_earn_success() -> None:
    """
    Refuse a forged success at the binding boundary.
    """

    qualification = qualify_vector_angular_spectrum(
        VectorAngularSpectrumRealization(
            device="cpu",
            working_memory_bytes=1024**3,
        )
    )
    document = vector_angular_spectrum_binding(qualification)
    values = dict(document.values)
    qualification_values = dict(values["qualification"])
    qualification_values["direct_component_error"] = "1"
    values["qualification"] = qualification_values

    with pytest.raises(
        ValueError,
        match="vector_field_binding_invalid",
    ):
        restore_vector_angular_spectrum_binding(
            Document(
                document.schema_identifier,
                values,
            )
        )


def test_observation_prefers_present_cuda(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Select CUDA when present; CPU is selected only when CUDA is absent.
    """

    monkeypatch.setattr(
        vector_module.torch.cuda,
        "is_available",
        lambda: True,
    )
    monkeypatch.setattr(
        vector_module.torch.cuda,
        "current_device",
        lambda: 3,
    )
    monkeypatch.setattr(
        vector_module,
        "observe_available_device_memory",
        lambda device: AvailableDeviceMemory(device, 2_000_000_000),
    )

    realization = observe_vector_angular_spectrum()

    assert realization.device == "cuda:3"
    assert realization.working_memory_bytes == 1_600_000_000


def test_propagation_rejects_a_field_outside_qualified_applicability() -> None:
    """
    Refuse hidden convention changes before numerical execution begins.
    """

    source = _sampled_field()
    circular = Field(
        wavelength_m=source.wavelength_m,
        surface=source.surface,
        frame=source.frame,
        medium=source.medium,
        basis=ComponentBasis.CIRCULAR,
        electric_components=(
            _component("right", source.electric("x")),
            _component("left", source.electric("y")),
        ),
        source_references=source.source_references,
        incident_reference_power=source.incident_reference_power,
    )
    realization = VectorAngularSpectrumRealization(
        device="cpu",
        working_memory_bytes=1024**3,
    )

    with pytest.raises(ValueError, match="vector_field_basis_unsupported"):
        propagate_electromagnetic_field(
            circular,
            distance_m=1e-6,
            realization=realization,
        )

    with pytest.raises(ValueError, match="vector_field_sampling_unsupported"):
        propagate_electromagnetic_field(
            Field(
                wavelength_m=source.wavelength_m,
                surface=PlaneSurface(
                    0.0,
                    source.wavelength_m,
                    source.surface.shape,
                ),
                frame=source.frame,
                medium=source.medium,
                basis=source.basis,
                electric_components=source.electric_components,
                source_references=source.source_references,
                incident_reference_power=source.incident_reference_power,
            ),
            distance_m=1e-6,
            realization=realization,
        )


def test_production_vector_kernel_stays_in_torch() -> None:
    """
    Guard the production numerical module against a NumPy implementation.
    """

    source = inspect.getsource(vector_module)

    assert "import numpy" not in source
    assert "from numpy" not in source
    assert "torch.complex128" in source
