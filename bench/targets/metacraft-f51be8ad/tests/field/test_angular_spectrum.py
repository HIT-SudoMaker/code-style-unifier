from __future__ import annotations

import numpy
import pytest

import metacraft.field.angular_spectrum as angular_spectrum_module
from metacraft.authority import reference_for
from metacraft.field import (
    ComponentBasis,
    CoordinateFrame,
    Field,
    FieldComponent,
    Medium,
    PlaneSurface,
)
from metacraft.field._device_memory import AvailableDeviceMemory
from metacraft.field.angular_spectrum import (
    AngularSpectrumConvention,
    AngularSpectrumQualification,
    AngularSpectrumRealization,
    observe_angular_spectrum,
    propagate_field,
    qualify_angular_spectrum,
)


def test_angular_spectrum_qualification_names_its_realization() -> None:
    """
    The componentwise propagation qualification names its exact method.
    """

    qualification = qualify_angular_spectrum(
        AngularSpectrumRealization("cpu", 512 * 1024 * 1024)
    )

    assert isinstance(qualification, AngularSpectrumQualification)
    assert isinstance(qualification.is_qualified, bool)


def test_observed_realization_records_one_supported_device() -> None:
    """
    Expose the exact device and reviewed numerical convention as one fact.
    """

    realization = observe_angular_spectrum()

    assert realization.implementation == "torch"
    assert (
        realization.device == "cpu"
        or realization.device.startswith("cuda:")
    )
    assert realization.complex_dtype == "complex128"
    assert realization.real_dtype == "float64"
    assert realization.convention.as_mapping() == {
        "coordinate_order": "y x",
        "evanescent_terms": "discarded",
        "forward_exponent": "negative",
        "inverse_normalization": "sample count",
        "padding_factor": 2,
        "propagation_exponent": "positive",
        "spectral_order": "unshifted",
    }


def test_observation_prefers_the_present_cuda_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Bind CUDA when it is present instead of selecting Torch CPU.
    """

    monkeypatch.setattr(
        angular_spectrum_module.torch.cuda,
        "is_available",
        lambda: True,
    )
    monkeypatch.setattr(
        angular_spectrum_module.torch.cuda,
        "current_device",
        lambda: 2,
    )
    monkeypatch.setattr(
        angular_spectrum_module,
        "observe_available_device_memory",
        lambda device: AvailableDeviceMemory(device, 3_000_000_000),
    )

    realization = observe_angular_spectrum()

    assert realization.device == "cuda:2"
    assert realization.working_memory_bytes == 2_400_000_000


def test_observation_retains_the_minimum_scalar_memory_reserve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        angular_spectrum_module.torch.cuda,
        "is_available",
        lambda: False,
    )
    monkeypatch.setattr(
        angular_spectrum_module,
        "observe_available_device_memory",
        lambda device: AvailableDeviceMemory(device, 1_000_000_000),
    )

    realization = observe_angular_spectrum()

    assert realization.device == "cpu"
    assert realization.working_memory_bytes == 463_129_088


def test_unusable_realization_fails_without_changing_device() -> None:
    """
    Keep a failed qualification on the exact realization it assessed.
    """

    realization = AngularSpectrumRealization(
        device="cpu",
        working_memory_bytes=0,
    )

    qualification = qualify_angular_spectrum(realization)

    assert qualification.realization == realization
    assert not qualification.is_qualified
    assert qualification.reason == "field_memory_unavailable"


def test_failed_selected_device_does_not_fall_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Keep a failed CUDA qualification on CUDA instead of retrying on CPU.
    """

    realization = AngularSpectrumRealization(
        device="cuda:0",
        working_memory_bytes=None,
    )

    observed_devices: list[str] = []

    def fail_memory_observation(device: str) -> AvailableDeviceMemory:
        observed_devices.append(device)
        raise RuntimeError("selected_cuda_failed")

    monkeypatch.setattr(
        angular_spectrum_module,
        "observe_available_device_memory",
        fail_memory_observation,
    )

    qualification = qualify_angular_spectrum(realization)

    assert qualification.realization == realization
    assert not qualification.is_qualified
    assert qualification.reason == "RuntimeError"
    assert observed_devices == ["cuda:0"]


def test_qualification_records_one_direct_complex_field_reference() -> None:
    """
    Prove the propagated complex field against independent scalar diffraction.
    """

    realization = AngularSpectrumRealization(
        device="cpu",
        working_memory_bytes=1024**3,
    )

    qualification = qualify_angular_spectrum(realization)
    reference = qualification.as_mapping()["direct_reference"]

    assert qualification.complex_field_error <= 1e-2
    assert reference == {
        "comparison": "relative complex l2",
        "comparison_shape": [10, 10],
        "distance_m": "1e-05",
        "maximum_relative_error": "0.01",
        "method": "Rayleigh-Sommerfeld first integral",
        "normalization": "absolute field, error divided by reference l2",
        "propagation_direction": "positive z",
        "shape": [20, 20],
        "spacing_m": "2e-07",
        "wavelength_m": "4e-07",
    }


def test_qualification_records_the_low_na_airy_limit() -> None:
    """
    Check one circular pupil against its paraxial first dark radius.
    """

    realization = AngularSpectrumRealization(
        device="cpu",
        working_memory_bytes=1024**3,
    )

    qualification = qualify_angular_spectrum(realization)
    airy_limit = qualification.as_mapping()["airy_limit"]

    assert qualification.airy_radius_error <= 5e-2
    assert airy_limit == {
        "aperture_diameter_m": "1.6e-05",
        "expected_first_dark_radius_m": "4.88e-06",
        "focal_distance_m": "0.00016",
        "maximum_relative_radius_error": "0.05",
        "measurement": "first minimum on averaged central rows",
        "paraxial_numerical_aperture": "0.05",
        "search_window": "0.6 to 1.4 expected radius",
        "shape": [128, 128],
        "spacing_m": "2.5e-07",
        "wavelength_m": "4e-07",
    }


def test_realization_rejects_an_alternate_fourier_sign() -> None:
    """
    Keep an alternate convention outside the one production realization.
    """

    with pytest.raises(ValueError, match="field_convention_unsupported"):
        AngularSpectrumRealization(
            device="cpu",
            working_memory_bytes=1024**3,
            convention=AngularSpectrumConvention(
                forward_exponent="positive"
            ),
        )


def test_realization_rejects_four_times_padding() -> None:
    """
    Keep the reviewed two-times padding as the only public configuration.
    """

    with pytest.raises(ValueError, match="field_convention_unsupported"):
        AngularSpectrumRealization(
            device="cpu",
            working_memory_bytes=1024**3,
            convention=AngularSpectrumConvention(padding_factor=4),
        )


def test_one_realization_propagates_one_linear_component() -> None:
    """
    Qualify and propagate a linear Field without transforming its zero.
    """

    samples = numpy.ones((8, 8), dtype="<c16")
    zeros = numpy.zeros_like(samples)
    samples.setflags(write=False)
    zeros.setflags(write=False)
    field = Field(
        wavelength_m=400e-9,
        surface=PlaneSurface(0.0, 100e-9, samples.shape),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        basis=ComponentBasis.TRANSVERSE_LINEAR,
        electric_components=(
            FieldComponent("x", samples),
            FieldComponent("y", zeros),
        ),
        source_references=(reference_for(b"linear field"),),
        incident_reference_power=64.0,
    )
    realization = observe_angular_spectrum()

    qualification = qualify_angular_spectrum(realization)
    propagation = propagate_field(
        field,
        distance_range_m=(8e-6, 12e-6),
        preferred_distance_m=10e-6,
        components=("x",),
        realization=realization,
    )
    observation = propagation.observation
    plane = propagation.principal_field

    assert qualification.is_qualified
    assert qualification.realization == realization
    assert observation.distances_m[0] == pytest.approx(8e-6)
    assert observation.distances_m[-1] == pytest.approx(12e-6)
    assert propagation.principal_distance_m in observation.distances_m
    assert propagation.realization["prepared_spectra"] == ["x"]
    assert plane.surface.position_m == pytest.approx(
        propagation.principal_distance_m
    )
    assert numpy.array_equal(
        plane.electric("y"),
        numpy.zeros_like(plane.electric("y")),
    )


def test_two_circular_components_prepare_one_spectrum_each() -> None:
    """
    Reuse each circular source spectrum across survey and refinement.
    """

    right = numpy.ones((8, 8), dtype="<c16")
    left = 1j * numpy.ones_like(right)
    right.setflags(write=False)
    left.setflags(write=False)
    field = Field(
        wavelength_m=400e-9,
        surface=PlaneSurface(0.0, 100e-9, right.shape),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        basis=ComponentBasis.CIRCULAR,
        electric_components=(
            FieldComponent("right", right),
            FieldComponent("left", left),
        ),
        source_references=(reference_for(b"circular field"),),
        incident_reference_power=128.0,
    )
    realization = observe_angular_spectrum()

    propagation = propagate_field(
        field,
        distance_range_m=(8e-6, 12e-6),
        preferred_distance_m=10e-6,
        components=("right",),
        realization=realization,
    )

    assert propagation.realization["spectrum_preparations"] == {
        "left": 1,
        "right": 1,
    }


def test_chunk_capacity_changes_neither_field_metrics_nor_evidence() -> None:
    """
    Keep execution capacity outside the identity of one scientific result.
    """

    samples = numpy.arange(64, dtype=numpy.float64).reshape(8, 8)
    samples = numpy.asarray(
        numpy.exp(1j * samples / 8),
        dtype=numpy.complex128,
    )
    zeros = numpy.zeros_like(samples)
    samples.setflags(write=False)
    zeros.setflags(write=False)
    field = Field(
        wavelength_m=400e-9,
        surface=PlaneSurface(0.0, 100e-9, samples.shape),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        basis=ComponentBasis.TRANSVERSE_LINEAR,
        electric_components=(
            FieldComponent("x", samples),
            FieldComponent("y", zeros),
        ),
        source_references=(reference_for(b"chunk invariant field"),),
        incident_reference_power=64.0,
    )
    low_capacity = AngularSpectrumRealization(
        device="cpu",
        working_memory_bytes=64 * 1024,
    )
    high_capacity = AngularSpectrumRealization(
        device="cpu",
        working_memory_bytes=1024**3,
    )

    low = propagate_field(
        field,
        distance_range_m=(8e-6, 12e-6),
        preferred_distance_m=10e-6,
        components=("x",),
        realization=low_capacity,
    )
    high = propagate_field(
        field,
        distance_range_m=(8e-6, 12e-6),
        preferred_distance_m=10e-6,
        components=("x",),
        realization=high_capacity,
    )

    assert low.observation == high.observation
    assert low.realization == high.realization
    assert low.principal_field.source_references == (
        high.principal_field.source_references
    )
    numpy.testing.assert_allclose(
        low.principal_field.electric("x"),
        high.principal_field.electric("x"),
        rtol=0,
        atol=1e-14,
    )
