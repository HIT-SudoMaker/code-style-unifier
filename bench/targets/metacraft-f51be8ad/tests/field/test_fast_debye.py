from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import replace

import pytest
import torch

import metacraft.field.debye_qualification as debye_qualification_module
import metacraft.field.fast_debye as fast_debye_module
from metacraft.field import CoordinateFrame, Medium
from metacraft.field.debye import (
    AplanaticPupil,
    AplanaticSurface,
    DebyeObservation,
    FocalCoordinates,
    PupilPolarization,
)
from metacraft.field.fast_debye import (
    CZT_DEBYE_REALIZATION,
    FFT_DEBYE_REALIZATION,
    CZTDebyeRealization,
    FFTDebyeRealization,
    evaluate_czt_debye,
    evaluate_fft_debye,
    fft_focal_axis,
    observe_czt_debye,
    observe_fft_debye,
)
from metacraft.field.debye_qualification import form_aplanatic_reference


def _pupil(numerical_aperture: float) -> AplanaticPupil:
    component = 2.0**-0.5
    return AplanaticPupil(
        surface=AplanaticSurface(
            focal_length_m=4.0e-6,
            angular_radius_rad=math.asin(numerical_aperture),
        ),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        medium_refractive_index=1.0,
        polarization=PupilPolarization(component, 1j * component),
        wavelength_m=532e-9,
    )


def _assert_complex_parity(
    actual: tuple[torch.Tensor, torch.Tensor, torch.Tensor],
    expected: tuple[torch.Tensor, torch.Tensor, torch.Tensor],
) -> None:
    reference_scale = max(
        float(torch.max(torch.abs(component)).item()) for component in expected
    )
    for calculated, reference in zip(actual, expected, strict=True):
        torch.testing.assert_close(
            calculated,
            reference,
            rtol=4e-3,
            atol=4e-4 * reference_scale,
        )


def test_accelerated_debye_realizations_and_qualification_keep_owners() -> None:
    """
    Expose paired accelerations without naming a new scientific route.
    """

    assert {
        "CZT_DEBYE_REALIZATION",
        "FFT_DEBYE_REALIZATION",
        "CZTDebyeRealization",
        "FFTDebyeRealization",
        "evaluate_czt_debye",
        "evaluate_fft_debye",
        "fft_focal_axis",
        "observe_czt_debye",
        "observe_fft_debye",
    }.issubset(fast_debye_module.__all__)
    assert {
        "AplanaticFocusQualification",
        "form_aplanatic_reference",
        "qualify_czt_debye",
        "qualify_fft_debye",
    }.issubset(debye_qualification_module.__all__)


def test_joint_aplanatic_reference_forms_the_requested_cartesian_region() -> None:
    """
    Prepare once, qualify FFT/CZT agreement, then return the requested CZT grid.
    """

    observation = form_aplanatic_reference(
        _pupil(0.8),
        horizontal_axis_m=(-40e-9, 20e-9),
        vertical_axis_m=(-30e-9, 0.0, 30e-9),
        axial_offset_m=12e-9,
        fft_realization=FFTDebyeRealization(
            device="cpu",
            pupil_samples=65,
        ),
        czt_realization=CZTDebyeRealization(
            device="cpu",
            pupil_samples=65,
        ),
    )

    assert observation.coordinates.point_count == 6
    assert observation.coordinates == FocalCoordinates(
        (-40e-9, 20e-9, -40e-9, 20e-9, -40e-9, 20e-9),
        (-30e-9, -30e-9, 0.0, 0.0, 30e-9, 30e-9),
        (12e-9,) * 6,
    )
    assert observation.realization_identity == CZT_DEBYE_REALIZATION


@pytest.mark.parametrize("numerical_aperture", (0.35, 0.8))
def test_fft_and_czt_match_on_the_fft_conjugate_grid(
    numerical_aperture: float,
) -> None:
    """
    Preserve complex vector amplitude on exact FFT-conjugate coordinates.
    """

    pupil = _pupil(numerical_aperture)
    realization = FFTDebyeRealization(
        device="cpu",
        pupil_samples=129,
        axial_plane_batch_size=1,
    )
    axis = fft_focal_axis(pupil, realization=realization)
    center = len(axis) // 2
    wavelength = pupil.wavelength_m
    coordinates = FocalCoordinates(
        horizontal_m=(
            axis[center],
            axis[center + 1],
            axis[center],
            axis[center - 1],
        ),
        vertical_m=(
            axis[center],
            axis[center],
            axis[center + 1],
            axis[center - 1],
        ),
        axial_m=(0.0, 0.04 * wavelength, 0.04 * wavelength, 0.0),
    )

    observed = evaluate_fft_debye(
        pupil,
        coordinates,
        realization=realization,
    )

    assert observed.coordinates == coordinates
    assert observed.realization_identity == FFT_DEBYE_REALIZATION
    czt = evaluate_czt_debye(
        pupil,
        coordinates,
        realization=CZTDebyeRealization(
            device="cpu",
            pupil_samples=realization.pupil_samples,
        ),
    )
    _assert_complex_parity(observed.electric_components, czt.electric_components)


@pytest.mark.parametrize("numerical_aperture", (0.35, 0.8))
def test_czt_debye_preserves_requested_off_axis_and_through_focus_coordinates(
    numerical_aperture: float,
) -> None:
    """
    Let a uniform requested window retain phase away from axis and focus.
    """

    pupil = _pupil(numerical_aperture)
    wavelength = pupil.wavelength_m
    horizontal = tuple(scale * wavelength for scale in (-0.18, -0.03, 0.12))
    vertical = tuple(scale * wavelength for scale in (-0.11, 0.07))
    axial = (-0.08 * wavelength, 0.06 * wavelength)
    coordinates = FocalCoordinates(
        horizontal_m=tuple(x for z in axial for y in vertical for x in horizontal),
        vertical_m=tuple(y for z in axial for y in vertical for x in horizontal),
        axial_m=tuple(z for z in axial for y in vertical for x in horizontal),
    )
    realization = CZTDebyeRealization(
        device="cpu",
        pupil_samples=129,
        axial_plane_batch_size=1,
    )

    observed = evaluate_czt_debye(
        pupil,
        coordinates,
        realization=realization,
    )

    assert observed.coordinates == coordinates
    assert observed.realization_identity == CZT_DEBYE_REALIZATION
    assert all(
        torch.isfinite(component).all() for component in observed.electric_components
    )


@pytest.mark.parametrize("axial_scale", (-0.08, 0.08))
def test_czt_debye_nonzero_plane_is_not_geometric_focus_with_new_metadata(
    axial_scale: float,
) -> None:
    """
    Let a translated physical plane change samples, not only their label.
    """

    pupil = _pupil(0.8)
    transverse = (-0.12 * pupil.wavelength_m, 0.0, 0.12 * pupil.wavelength_m)
    translated = FocalCoordinates(
        horizontal_m=transverse,
        vertical_m=(0.0, 0.0, 0.0),
        axial_m=tuple(axial_scale * pupil.wavelength_m for _ in transverse),
    )
    geometric_focus = FocalCoordinates(
        horizontal_m=transverse,
        vertical_m=(0.0, 0.0, 0.0),
        axial_m=(0.0, 0.0, 0.0),
    )
    realization = CZTDebyeRealization(device="cpu", pupil_samples=129)

    translated_field = evaluate_czt_debye(
        pupil,
        translated,
        realization=realization,
    )
    focal_field = evaluate_czt_debye(
        pupil,
        geometric_focus,
        realization=realization,
    )

    assert any(
        not torch.allclose(actual, reference, rtol=1e-10, atol=1e-12)
        for actual, reference in zip(
            translated_field.electric_components,
            focal_field.electric_components,
            strict=True,
        )
    )


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
@pytest.mark.parametrize("axial_scale", (-0.08, 0.0, 0.08))
def test_czt_debye_keeps_axial_plane_parity_across_cpu_and_cuda(
    axial_scale: float,
) -> None:
    """
    Preserve one translated plane when execution moves to CUDA.
    """

    pupil = _pupil(0.8)
    coordinates = FocalCoordinates(
        horizontal_m=(-0.1 * pupil.wavelength_m, 0.0, 0.1 * pupil.wavelength_m),
        vertical_m=(0.0, 0.0, 0.0),
        axial_m=tuple(axial_scale * pupil.wavelength_m for _ in range(3)),
    )
    cpu = evaluate_czt_debye(
        pupil,
        coordinates,
        realization=CZTDebyeRealization(device="cpu", pupil_samples=129),
    )
    cuda = evaluate_czt_debye(
        pupil,
        coordinates,
        realization=CZTDebyeRealization(
            device=f"cuda:{torch.cuda.current_device()}",
            pupil_samples=129,
        ),
    )

    _assert_complex_parity(
        tuple(component.cpu() for component in cuda.electric_components),
        cpu.electric_components,
    )


def test_fast_debye_separately_preserves_phase_normalization_and_handedness() -> None:
    """
    Keep intensity agreement from hiding phase, scale, or polarization errors.
    """

    pupil = _pupil(0.8)
    fft_realization = FFTDebyeRealization(device="cpu", pupil_samples=129)
    axis = fft_focal_axis(pupil, realization=fft_realization)
    center = len(axis) // 2
    fft_coordinates = FocalCoordinates(
        horizontal_m=(axis[center - 1], axis[center], axis[center + 1]),
        vertical_m=(0.0, 0.0, 0.0),
        axial_m=(0.0, 0.0, 0.0),
    )
    observed = evaluate_fft_debye(
        pupil,
        fft_coordinates,
        realization=fft_realization,
    )
    expected = evaluate_czt_debye(
        pupil,
        fft_coordinates,
        realization=CZTDebyeRealization(device="cpu", pupil_samples=129),
    )
    reference_scale = max(
        float(torch.max(torch.abs(component)).item())
        for component in expected.electric_components
    )

    for actual_component, expected_component in zip(
        observed.electric_components,
        expected.electric_components,
        strict=True,
    ):
        significant = torch.abs(expected_component) > 1e-4 * reference_scale
        torch.testing.assert_close(
            torch.abs(actual_component),
            torch.abs(expected_component),
            rtol=4e-3,
            atol=4e-4 * reference_scale,
        )
        torch.testing.assert_close(
            torch.angle(
                actual_component[significant]
                * torch.conj(expected_component[significant])
            ),
            torch.zeros_like(torch.angle(expected_component[significant])),
            rtol=0.0,
            atol=4e-3,
        )
    center = 1
    torch.testing.assert_close(
        observed.vertical_component[center],
        1j * observed.horizontal_component[center],
        rtol=1e-11,
        atol=1e-11,
    )


@pytest.mark.parametrize(
    ("realization", "evaluate"),
    (
        (
            FFTDebyeRealization(device="cpu", pupil_samples=65),
            evaluate_fft_debye,
        ),
        (
            CZTDebyeRealization(device="cpu", pupil_samples=65),
            evaluate_czt_debye,
        ),
    ),
)
def test_capacity_changes_batching_not_field_or_binding_identity(
    realization: FFTDebyeRealization | CZTDebyeRealization,
    evaluate: Callable[..., DebyeObservation],
) -> None:
    """
    Let capacity bound work without changing the scientific realization.
    """

    pupil = _pupil(0.8)
    if isinstance(realization, FFTDebyeRealization):
        axis = fft_focal_axis(pupil, realization=realization)
        center = len(axis) // 2
        horizontal = axis[center]
        vertical = axis[center]
    else:
        horizontal = 0.07 * pupil.wavelength_m
        vertical = -0.03 * pupil.wavelength_m
    coordinates = FocalCoordinates(
        horizontal_m=(horizontal,) * 3,
        vertical_m=(vertical,) * 3,
        axial_m=(-20e-9, 0.0, 20e-9),
    )
    separated = replace(realization, axial_plane_batch_size=1)
    together = replace(realization, axial_plane_batch_size=3)

    first = evaluate(pupil, coordinates, realization=separated)
    second = evaluate(pupil, coordinates, realization=together)

    assert separated == together
    assert separated.as_mapping() == together.as_mapping()
    assert first.realization_identity == second.realization_identity
    for left, right in zip(
        first.electric_components,
        second.electric_components,
        strict=True,
    ):
        torch.testing.assert_close(left, right, rtol=0.0, atol=0.0)


def test_fast_debye_bindings_record_one_shared_physical_method() -> None:
    """
    Identify acceleration without inventing a second scientific method.
    """

    fft = FFTDebyeRealization(device="cpu", pupil_samples=65)
    czt = CZTDebyeRealization(device="cpu", pupil_samples=65)

    assert fft.source_method == czt.source_method == "Richards--Wolf Debye"
    assert fft.identity == FFT_DEBYE_REALIZATION
    assert czt.identity == CZT_DEBYE_REALIZATION
    for binding in (fft.as_mapping(), czt.as_mapping()):
        assert binding["sampling"] == {"direction_cosine_samples_per_axis": 65}
        assert binding["window"] == "hard circular pupil"
        assert binding["coordinate_convention"] == (
            "Cartesian points relative to geometric focus"
        )
        assert binding["device"] == "cpu"
        assert binding["complex_dtype"] == "complex128"
        assert binding["source_method"] == "Richards--Wolf Debye"


def test_fast_debye_observation_prefers_one_selected_cuda_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Select CUDA once and preserve that selection in both realizations.
    """

    monkeypatch.setattr(
        fast_debye_module.torch.cuda,
        "is_available",
        lambda: True,
    )
    monkeypatch.setattr(
        fast_debye_module.torch.cuda,
        "current_device",
        lambda: 3,
    )

    assert observe_fft_debye().device == "cuda:3"
    assert observe_czt_debye().device == "cuda:3"


def test_failed_selected_cuda_device_never_falls_back() -> None:
    """
    Surface one selected-device failure instead of changing realization.
    """

    pupil = _pupil(0.8)

    with pytest.raises(RuntimeError):
        evaluate_czt_debye(
            pupil,
            FocalCoordinates((0.0,), (0.0,), (0.0,)),
            realization=CZTDebyeRealization(
                device="cuda:999",
                pupil_samples=65,
            ),
        )


def test_fast_debye_rejects_hidden_coordinate_interpolation() -> None:
    """
    Require FFT observations to use their exact conjugate focal grid.
    """

    pupil = _pupil(0.8)

    with pytest.raises(ValueError, match="fft_debye_coordinates_unmatched"):
        evaluate_fft_debye(
            pupil,
            FocalCoordinates((13e-9,), (0.0,), (0.0,)),
            realization=FFTDebyeRealization(
                device="cpu",
                pupil_samples=65,
            ),
        )
