from __future__ import annotations

from dataclasses import dataclass, field
import math

import torch

from .debye import AplanaticPupil, DebyeConvention, DebyeObservation, FocalCoordinates

FFT_DEBYE_REALIZATION = "metacraft.field.fft_debye"
CZT_DEBYE_REALIZATION = "metacraft.field.czt_debye"
_SOURCE_METHOD = "Richards--Wolf Debye"
_PUPIL_WINDOW = "hard circular pupil"
_COORDINATE_CONVENTION = "Cartesian points relative to geometric focus"


@dataclass(frozen=True, slots=True)
class _PreparedAplanaticPupil:
    pupil: AplanaticPupil
    direction_axis: torch.Tensor
    axial_direction: torch.Tensor
    components: tuple[torch.Tensor, torch.Tensor, torch.Tensor]


@dataclass(frozen=True, slots=True)
class FFTDebyeRealization:
    """
    Bind a centered Torch FFT to the shared Debye physical method.
    """

    device: str
    pupil_samples: int = 257
    axial_plane_batch_size: int = field(
        default=1,
        compare=False,
        repr=False,
    )
    convention: DebyeConvention = field(default_factory=DebyeConvention)
    identity: str = FFT_DEBYE_REALIZATION
    source_method: str = _SOURCE_METHOD
    implementation: str = "torch fft"
    window: str = _PUPIL_WINDOW
    coordinate_convention: str = _COORDINATE_CONVENTION
    complex_dtype: str = "complex128"
    real_dtype: str = "float64"

    def __post_init__(self) -> None:
        """
        Require one centered, odd-sampled Torch realization.
        """

        _validate_realization(
            identity=self.identity,
            expected_identity=FFT_DEBYE_REALIZATION,
            source_method=self.source_method,
            implementation=self.implementation,
            expected_implementation="torch fft",
            device=self.device,
            pupil_samples=self.pupil_samples,
            axial_plane_batch_size=self.axial_plane_batch_size,
            convention=self.convention,
            window=self.window,
            coordinate_convention=self.coordinate_convention,
            complex_dtype=self.complex_dtype,
            real_dtype=self.real_dtype,
        )

    def as_mapping(self) -> dict[str, object]:
        """
        Return every fact that identifies this accelerated binding.
        """

        return _binding_mapping(
            identity=self.identity,
            source_method=self.source_method,
            implementation=self.implementation,
            device=self.device,
            pupil_samples=self.pupil_samples,
            convention=self.convention,
            window=self.window,
            coordinate_convention=self.coordinate_convention,
            complex_dtype=self.complex_dtype,
            real_dtype=self.real_dtype,
        )


@dataclass(frozen=True, slots=True)
class CZTDebyeRealization:
    """
    Bind a Torch chirp transform to the shared Debye physical method.
    """

    device: str
    pupil_samples: int = 257
    axial_plane_batch_size: int = field(
        default=1,
        compare=False,
        repr=False,
    )
    convention: DebyeConvention = field(default_factory=DebyeConvention)
    identity: str = CZT_DEBYE_REALIZATION
    source_method: str = _SOURCE_METHOD
    implementation: str = "torch chirp z-transform"
    window: str = _PUPIL_WINDOW
    coordinate_convention: str = _COORDINATE_CONVENTION
    complex_dtype: str = "complex128"
    real_dtype: str = "float64"

    def __post_init__(self) -> None:
        """
        Require one centered, odd-sampled Torch realization.
        """

        _validate_realization(
            identity=self.identity,
            expected_identity=CZT_DEBYE_REALIZATION,
            source_method=self.source_method,
            implementation=self.implementation,
            expected_implementation="torch chirp z-transform",
            device=self.device,
            pupil_samples=self.pupil_samples,
            axial_plane_batch_size=self.axial_plane_batch_size,
            convention=self.convention,
            window=self.window,
            coordinate_convention=self.coordinate_convention,
            complex_dtype=self.complex_dtype,
            real_dtype=self.real_dtype,
        )

    def as_mapping(self) -> dict[str, object]:
        """
        Return every fact that identifies this accelerated binding.
        """

        return _binding_mapping(
            identity=self.identity,
            source_method=self.source_method,
            implementation=self.implementation,
            device=self.device,
            pupil_samples=self.pupil_samples,
            convention=self.convention,
            window=self.window,
            coordinate_convention=self.coordinate_convention,
            complex_dtype=self.complex_dtype,
            real_dtype=self.real_dtype,
        )


def observe_fft_debye() -> FFTDebyeRealization:
    """
    Select one Torch device for the FFT realization without fallback.
    """

    return FFTDebyeRealization(device=_selected_device())


def observe_czt_debye() -> CZTDebyeRealization:
    """
    Select one Torch device for the CZT realization without fallback.
    """

    return CZTDebyeRealization(device=_selected_device())


def fft_focal_axis(
    pupil: AplanaticPupil,
    *,
    realization: FFTDebyeRealization,
) -> tuple[float, ...]:
    """
    Return the exact focal axis conjugate to one FFT pupil sampling.
    """

    device = torch.device(realization.device)
    medium_wavelength = pupil.wavelength_m / pupil.medium_refractive_index
    direction_step = (
        2.0 * math.sin(pupil.surface.angular_radius_rad) / realization.pupil_samples
    )
    focal_step = medium_wavelength / (realization.pupil_samples * direction_step)
    axis = (
        _centered_indices(
            realization.pupil_samples,
            device=device,
        )
        * focal_step
    )
    return tuple(float(value.item()) for value in axis)


def evaluate_fft_debye(
    pupil: AplanaticPupil,
    coordinates: FocalCoordinates,
    *,
    realization: FFTDebyeRealization,
) -> DebyeObservation:
    """
    Evaluate Debye fields on exact coordinates of the conjugate FFT grid.

    No interpolation is hidden inside this realization. Coordinates that do
    not lie on its natural grid fail directly and may instead be requested
    from the CZT realization.
    """

    prepared = _prepare_aplanatic_pupil(
        pupil,
        sample_count=realization.pupil_samples,
        device=torch.device(realization.device),
    )
    return _evaluate_prepared_fft_debye(
        prepared,
        coordinates,
        realization=realization,
    )


def _evaluate_prepared_fft_debye(
    prepared: _PreparedAplanaticPupil,
    coordinates: FocalCoordinates,
    *,
    realization: FFTDebyeRealization,
) -> DebyeObservation:
    _require_prepared_realization(prepared, realization)
    pupil = prepared.pupil
    direction_axis = prepared.direction_axis
    axial_direction = prepared.axial_direction
    pupil_components = prepared.components

    device = torch.device(realization.device)
    (
        horizontal,
        vertical,
        axial,
    ) = _coordinate_tensors(coordinates, device=device)
    focal_step = (
        pupil.wavelength_m
        / pupil.medium_refractive_index
        / (realization.pupil_samples * (direction_axis[1] - direction_axis[0]))
    )
    center = realization.pupil_samples // 2
    horizontal_indices = torch.round(horizontal / focal_step).to(torch.int64)
    vertical_indices = torch.round(vertical / focal_step).to(torch.int64)
    matched_horizontal = horizontal_indices.to(torch.float64) * focal_step
    matched_vertical = vertical_indices.to(torch.float64) * focal_step
    tolerance = torch.finfo(torch.float64).eps * max(
        1.0,
        abs(float(focal_step.item())),
    )
    if (
        bool(torch.any(torch.abs(horizontal - matched_horizontal) > tolerance).item())
        or bool(torch.any(torch.abs(vertical - matched_vertical) > tolerance).item())
        or bool(torch.any(torch.abs(horizontal_indices) > center).item())
        or bool(torch.any(torch.abs(vertical_indices) > center).item())
    ):
        raise ValueError("fft_debye_coordinates_unmatched")

    unique_axial, axial_inverse = torch.unique(
        axial,
        sorted=True,
        return_inverse=True,
    )
    components = _empty_components(coordinates.point_count, device=device)
    wave_number = _wave_number(pupil)
    prefactor = _debye_prefactor(pupil)
    for start in range(
        0,
        unique_axial.numel(),
        realization.axial_plane_batch_size,
    ):
        stop = min(
            unique_axial.numel(),
            start + realization.axial_plane_batch_size,
        )
        is_plane_selected = (axial_inverse >= start) & (axial_inverse < stop)
        if not bool(torch.any(is_plane_selected).item()):
            continue
        axial_phase = torch.exp(
            1j
            * wave_number
            * unique_axial[start:stop, None, None]
            * axial_direction[None, :, :]
        )
        for target, pupil_component in zip(
            components,
            pupil_components,
            strict=True,
        ):
            planes = (
                torch.fft.fftshift(
                    torch.fft.ifft2(
                        torch.fft.ifftshift(
                            axial_phase * pupil_component[None, :, :],
                            dim=(-2, -1),
                        ),
                        dim=(-2, -1),
                    ),
                    dim=(-2, -1),
                )
                * realization.pupil_samples**2
                * prefactor
            )
            target[is_plane_selected] = planes[
                axial_inverse[is_plane_selected] - start,
                vertical_indices[is_plane_selected] + center,
                horizontal_indices[is_plane_selected] + center,
            ]
    return _observation(
        coordinates,
        components,
        realization_identity=realization.identity,
    )


def evaluate_czt_debye(
    pupil: AplanaticPupil,
    coordinates: FocalCoordinates,
    *,
    realization: CZTDebyeRealization,
) -> DebyeObservation:
    """
    Evaluate Debye fields on caller-declared uniform Cartesian focal axes.

    Each distinct horizontal and vertical coordinate set must form a uniform
    axis. Corresponding points may be ordered freely and may span several
    axial planes.
    """

    prepared = _prepare_aplanatic_pupil(
        pupil,
        sample_count=realization.pupil_samples,
        device=torch.device(realization.device),
    )
    return _evaluate_prepared_czt_debye(
        prepared,
        coordinates,
        realization=realization,
    )


def _evaluate_prepared_czt_debye(
    prepared: _PreparedAplanaticPupil,
    coordinates: FocalCoordinates,
    *,
    realization: CZTDebyeRealization,
) -> DebyeObservation:
    _require_prepared_realization(prepared, realization)
    pupil = prepared.pupil
    direction_axis = prepared.direction_axis
    axial_direction = prepared.axial_direction
    pupil_components = prepared.components

    device = torch.device(realization.device)
    (
        horizontal,
        vertical,
        axial,
    ) = _coordinate_tensors(coordinates, device=device)
    (
        horizontal_axis,
        horizontal_inverse,
    ) = _uniform_axis(horizontal)
    (
        vertical_axis,
        vertical_inverse,
    ) = _uniform_axis(vertical)
    unique_axial, axial_inverse = torch.unique(
        axial,
        sorted=True,
        return_inverse=True,
    )
    components = _empty_components(coordinates.point_count, device=device)
    wave_number = _wave_number(pupil)
    prefactor = _debye_prefactor(pupil)
    direction_step = direction_axis[1] - direction_axis[0]
    for start in range(
        0,
        unique_axial.numel(),
        realization.axial_plane_batch_size,
    ):
        stop = min(
            unique_axial.numel(),
            start + realization.axial_plane_batch_size,
        )
        is_plane_selected = (axial_inverse >= start) & (axial_inverse < stop)
        if not bool(torch.any(is_plane_selected).item()):
            continue
        axial_phase = torch.exp(
            1j
            * wave_number
            * unique_axial[start:stop, None, None]
            * axial_direction[None, :, :]
        )
        for target, pupil_component in zip(
            components,
            pupil_components,
            strict=True,
        ):
            planes = (
                _two_dimensional_chirp_transform(
                    axial_phase * pupil_component[None, :, :],
                    direction_start=direction_axis[0],
                    direction_step=direction_step,
                    horizontal_axis=horizontal_axis,
                    vertical_axis=vertical_axis,
                    wave_number=wave_number,
                )
                * prefactor
            )
            target[is_plane_selected] = planes[
                axial_inverse[is_plane_selected] - start,
                vertical_inverse[is_plane_selected],
                horizontal_inverse[is_plane_selected],
            ]
    return _observation(
        coordinates,
        components,
        realization_identity=realization.identity,
    )


def _sample_aplanatic_pupil(
    pupil: AplanaticPupil,
    *,
    sample_count: int,
    device: torch.device,
) -> tuple[
    torch.Tensor,
    torch.Tensor,
    tuple[torch.Tensor, torch.Tensor, torch.Tensor],
]:
    direction_radius = math.sin(pupil.surface.angular_radius_rad)
    direction_step = 2.0 * direction_radius / sample_count
    direction_axis = _centered_indices(sample_count, device=device) * direction_step
    direction_vertical, direction_horizontal = torch.meshgrid(
        direction_axis,
        direction_axis,
        indexing="ij",
    )
    radial_square = direction_horizontal.square() + direction_vertical.square()
    is_occupied = radial_square < direction_radius**2
    axial_direction = torch.sqrt(
        torch.clamp(1.0 - radial_square, min=torch.finfo(torch.float64).tiny)
    )
    radial_direction = torch.sqrt(radial_square)
    azimuth_cosine = torch.where(
        radial_direction > 0,
        direction_horizontal / radial_direction,
        torch.ones_like(radial_direction),
    )
    azimuth_sine = torch.where(
        radial_direction > 0,
        direction_vertical / radial_direction,
        torch.zeros_like(radial_direction),
    )
    horizontal_input = torch.tensor(
        pupil.polarization.horizontal_component,
        dtype=torch.complex128,
        device=device,
    )
    vertical_input = torch.tensor(
        pupil.polarization.vertical_component,
        dtype=torch.complex128,
        device=device,
    )
    cross_component = (axial_direction - 1.0) * azimuth_cosine * azimuth_sine
    horizontal_component = (
        horizontal_input
        * (axial_direction * azimuth_cosine.square() + azimuth_sine.square())
        + vertical_input * cross_component
    )
    vertical_component = horizontal_input * cross_component + vertical_input * (
        axial_direction * azimuth_sine.square() + azimuth_cosine.square()
    )
    longitudinal_component = -(
        horizontal_input * direction_horizontal + vertical_input * direction_vertical
    )
    quadrature_weight = torch.where(
        is_occupied,
        direction_step**2 / torch.sqrt(axial_direction),
        torch.zeros_like(axial_direction),
    )
    components = (
        horizontal_component * quadrature_weight,
        vertical_component * quadrature_weight,
        longitudinal_component * quadrature_weight,
    )
    return (
        direction_axis,
        axial_direction,
        components,
    )


def _prepare_aplanatic_pupil(
    pupil: AplanaticPupil,
    *,
    sample_count: int,
    device: torch.device,
) -> _PreparedAplanaticPupil:
    direction_axis, axial_direction, components = _sample_aplanatic_pupil(
        pupil,
        sample_count=sample_count,
        device=device,
    )
    return _PreparedAplanaticPupil(
        pupil=pupil,
        direction_axis=direction_axis,
        axial_direction=axial_direction,
        components=components,
    )


def _require_prepared_realization(
    prepared: _PreparedAplanaticPupil,
    realization: FFTDebyeRealization | CZTDebyeRealization,
) -> None:
    if len(
        prepared.direction_axis
    ) != realization.pupil_samples or prepared.direction_axis.device != torch.device(
        realization.device
    ):
        raise ValueError("prepared_aplanatic_pupil_mismatch")


def _two_dimensional_chirp_transform(
    samples: torch.Tensor,
    *,
    direction_start: torch.Tensor,
    direction_step: torch.Tensor,
    horizontal_axis: torch.Tensor,
    vertical_axis: torch.Tensor,
    wave_number: float,
) -> torch.Tensor:
    horizontal_step = _axis_step(horizontal_axis)
    horizontal = _chirp_z_transform(
        samples,
        output_count=horizontal_axis.numel(),
        start_phase=wave_number * horizontal_axis[0] * direction_step,
        phase_step=wave_number * horizontal_step * direction_step,
    )
    horizontal = horizontal * torch.exp(
        1j * wave_number * horizontal_axis * direction_start
    )
    vertical_step = _axis_step(vertical_axis)
    vertical = _chirp_z_transform(
        horizontal.transpose(-2, -1),
        output_count=vertical_axis.numel(),
        start_phase=wave_number * vertical_axis[0] * direction_step,
        phase_step=wave_number * vertical_step * direction_step,
    )
    vertical = vertical * torch.exp(1j * wave_number * vertical_axis * direction_start)
    return vertical.transpose(-2, -1)


def _chirp_z_transform(
    samples: torch.Tensor,
    *,
    output_count: int,
    start_phase: torch.Tensor,
    phase_step: torch.Tensor,
) -> torch.Tensor:
    input_count = samples.shape[-1]
    device = samples.device
    source_indices = torch.arange(
        input_count,
        dtype=torch.float64,
        device=device,
    )
    output_indices = torch.arange(
        output_count,
        dtype=torch.float64,
        device=device,
    )
    convolution_indices = torch.arange(
        -(input_count - 1),
        output_count,
        dtype=torch.float64,
        device=device,
    )
    prepared = samples * torch.exp(
        1j * (start_phase * source_indices + 0.5 * phase_step * source_indices.square())
    )
    kernel = torch.exp(-0.5j * phase_step * convolution_indices.square())
    fft_length = 1 << (input_count + output_count - 2).bit_length()
    convolution = torch.fft.ifft(
        torch.fft.fft(prepared, n=fft_length) * torch.fft.fft(kernel, n=fft_length),
    )
    return convolution[
        ...,
        input_count - 1 : input_count - 1 + output_count,
    ] * torch.exp(0.5j * phase_step * output_indices.square())


def _uniform_axis(
    coordinates: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    axis, inverse = torch.unique(
        coordinates,
        sorted=True,
        return_inverse=True,
    )
    if axis.numel() > 2:
        expected = torch.linspace(
            axis[0],
            axis[-1],
            axis.numel(),
            dtype=torch.float64,
            device=axis.device,
        )
        tolerance = torch.finfo(torch.float64).eps * max(
            1.0,
            abs(float(axis[-1].item())),
        )
        if bool(torch.any(torch.abs(axis - expected) > tolerance).item()):
            raise ValueError("czt_debye_coordinates_not_uniform")
    return axis, inverse


def _axis_step(axis: torch.Tensor) -> torch.Tensor:
    if axis.numel() == 1:
        return torch.zeros((), dtype=torch.float64, device=axis.device)
    return axis[1] - axis[0]


def _coordinate_tensors(
    coordinates: FocalCoordinates,
    *,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    return (
        torch.tensor(
            coordinates.horizontal_m,
            dtype=torch.float64,
            device=device,
        ),
        torch.tensor(
            coordinates.vertical_m,
            dtype=torch.float64,
            device=device,
        ),
        torch.tensor(
            coordinates.axial_m,
            dtype=torch.float64,
            device=device,
        ),
    )


def _centered_indices(
    count: int,
    *,
    device: torch.device,
) -> torch.Tensor:
    return torch.arange(count, dtype=torch.float64, device=device) - count // 2


def _empty_components(
    point_count: int,
    *,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    return (
        torch.empty(point_count, dtype=torch.complex128, device=device),
        torch.empty(point_count, dtype=torch.complex128, device=device),
        torch.empty(point_count, dtype=torch.complex128, device=device),
    )


def _observation(
    coordinates: FocalCoordinates,
    components: tuple[torch.Tensor, torch.Tensor, torch.Tensor],
    *,
    realization_identity: str,
) -> DebyeObservation:
    return DebyeObservation(
        coordinates=coordinates,
        horizontal_component=components[0],
        vertical_component=components[1],
        longitudinal_component=components[2],
        realization_identity=realization_identity,
    )


def _wave_number(pupil: AplanaticPupil) -> float:
    return 2.0 * math.pi * pupil.medium_refractive_index / pupil.wavelength_m


def _debye_prefactor(pupil: AplanaticPupil) -> complex:
    return -1j * _wave_number(pupil) * pupil.surface.focal_length_m / (2.0 * math.pi)


def _validate_realization(
    *,
    identity: str,
    expected_identity: str,
    source_method: str,
    implementation: str,
    expected_implementation: str,
    device: str,
    pupil_samples: int,
    axial_plane_batch_size: int,
    convention: DebyeConvention,
    window: str,
    coordinate_convention: str,
    complex_dtype: str,
    real_dtype: str,
) -> None:
    if identity != expected_identity:
        raise ValueError("fast_debye_identity_unsupported")
    if source_method != _SOURCE_METHOD:
        raise ValueError("fast_debye_source_method_unsupported")
    if implementation != expected_implementation:
        raise ValueError("fast_debye_implementation_unsupported")
    if device != "cpu" and not _is_cuda_device(device):
        raise ValueError("fast_debye_device_unsupported")
    if pupil_samples < 33 or pupil_samples % 2 != 1:
        raise ValueError("fast_debye_pupil_sampling_invalid")
    if axial_plane_batch_size < 1:
        raise ValueError("fast_debye_batch_size_invalid")
    if convention != DebyeConvention():
        raise ValueError("fast_debye_convention_unsupported")
    if window != _PUPIL_WINDOW:
        raise ValueError("fast_debye_window_unsupported")
    if coordinate_convention != _COORDINATE_CONVENTION:
        raise ValueError("fast_debye_coordinates_unsupported")
    if complex_dtype != "complex128":
        raise ValueError("fast_debye_complex_dtype_unsupported")
    if real_dtype != "float64":
        raise ValueError("fast_debye_real_dtype_unsupported")


def _binding_mapping(
    *,
    identity: str,
    source_method: str,
    implementation: str,
    device: str,
    pupil_samples: int,
    convention: DebyeConvention,
    window: str,
    coordinate_convention: str,
    complex_dtype: str,
    real_dtype: str,
) -> dict[str, object]:
    return {
        "complex_dtype": complex_dtype,
        "convention": convention.as_mapping(),
        "coordinate_convention": coordinate_convention,
        "device": device,
        "identity": identity,
        "implementation": implementation,
        "real_dtype": real_dtype,
        "sampling": {
            "direction_cosine_samples_per_axis": pupil_samples,
        },
        "source_method": source_method,
        "window": window,
    }


def _is_cuda_device(device: str) -> bool:
    prefix, separator, ordinal = device.partition(":")
    return prefix == "cuda" and separator == ":" and ordinal.isdecimal()


def _selected_device() -> str:
    if torch.cuda.is_available():
        return f"cuda:{torch.cuda.current_device()}"
    return "cpu"


__all__ = [
    "CZT_DEBYE_REALIZATION",
    "FFT_DEBYE_REALIZATION",
    "CZTDebyeRealization",
    "FFTDebyeRealization",
    "evaluate_czt_debye",
    "evaluate_fft_debye",
    "fft_focal_axis",
    "observe_czt_debye",
    "observe_fft_debye",
]
