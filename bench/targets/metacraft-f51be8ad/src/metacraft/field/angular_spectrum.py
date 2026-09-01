from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import math
from types import MappingProxyType

import numpy
from numpy.typing import NDArray
import torch

from ._device_memory import observe_available_device_memory
from .sample import Field, FieldComponent, PlaneSurface

ANGULAR_SPECTRUM_REALIZATION = "metacraft.field.angular_spectrum"
_COMPLEX_BYTES = torch.empty((), dtype=torch.complex128).element_size()
_REAL_BYTES = torch.empty((), dtype=torch.float64).element_size()
_DIRECT_REFERENCE_SIZE = 20
_DIRECT_REFERENCE_SPACING_M = 200e-9
_DIRECT_REFERENCE_WAVELENGTH_M = 400e-9
_DIRECT_REFERENCE_DISTANCE_M = 10e-6
_DIRECT_REFERENCE_MAXIMUM_ERROR = 1e-2
_AIRY_SAMPLE_COUNT = 128
_AIRY_SPACING_M = 250e-9
_AIRY_WAVELENGTH_M = 400e-9
_AIRY_FOCAL_DISTANCE_M = 160e-6
_AIRY_APERTURE_DIAMETER_M = 16e-6
_AIRY_PARAXIAL_NUMERICAL_APERTURE = 0.05
_AIRY_MAXIMUM_RADIUS_ERROR = 5e-2


@dataclass(frozen=True, slots=True)
class AngularSpectrumConvention:
    """
    Freeze every mathematical choice of the current field realization.
    """

    padding_factor: int = 2
    evanescent_terms: str = "discarded"
    coordinate_order: str = "y x"
    forward_exponent: str = "negative"
    propagation_exponent: str = "positive"
    inverse_normalization: str = "sample count"
    spectral_order: str = "unshifted"

    def __post_init__(self) -> None:
        """
        Require a well-formed numerical convention.
        """

        if self.padding_factor < 1:
            raise ValueError("padding_factor_invalid")

    def as_mapping(self) -> dict[str, object]:
        """
        Return provider-neutral numerical provenance.
        """

        return {
            "coordinate_order": self.coordinate_order,
            "evanescent_terms": self.evanescent_terms,
            "forward_exponent": self.forward_exponent,
            "inverse_normalization": self.inverse_normalization,
            "padding_factor": self.padding_factor,
            "propagation_exponent": self.propagation_exponent,
            "spectral_order": self.spectral_order,
        }

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object],
    ) -> AngularSpectrumConvention:
        """
        Restore and validate one exact numerical convention.
        """

        return cls(
            padding_factor=int(str(value["padding_factor"])),
            evanescent_terms=str(value["evanescent_terms"]),
            coordinate_order=str(value["coordinate_order"]),
            forward_exponent=str(value["forward_exponent"]),
            propagation_exponent=str(value["propagation_exponent"]),
            inverse_normalization=str(value["inverse_normalization"]),
            spectral_order=str(value["spectral_order"]),
        )


@dataclass(frozen=True, slots=True)
class AngularSpectrumRealization:
    """
    Bind the one tensor program to exact local execution facts.
    """

    device: str
    working_memory_bytes: int | None = field(compare=False, repr=False)
    convention: AngularSpectrumConvention = field(
        default_factory=AngularSpectrumConvention
    )
    identity: str = ANGULAR_SPECTRUM_REALIZATION
    implementation: str = "torch"
    complex_dtype: str = "complex128"
    real_dtype: str = "float64"

    def __post_init__(self) -> None:
        """
        Reject incomplete or alternate realization facts.
        """

        if self.identity != ANGULAR_SPECTRUM_REALIZATION:
            raise ValueError("field_realization_identity_unsupported")
        if self.implementation != "torch":
            raise ValueError("field_implementation_unsupported")
        if self.device != "cpu" and not self.device.startswith("cuda:"):
            raise ValueError("field_device_unsupported")
        if self.complex_dtype != "complex128":
            raise ValueError("field_complex_dtype_unsupported")
        if self.real_dtype != "float64":
            raise ValueError("field_real_dtype_unsupported")
        if (
            self.working_memory_bytes is not None
            and self.working_memory_bytes < 0
        ):
            raise ValueError("field_working_memory_invalid")
        if self.convention != AngularSpectrumConvention():
            raise ValueError("field_convention_unsupported")

    def as_mapping(self) -> dict[str, object]:
        """
        Return the exact realization as binding-safe values.
        """

        return {
            "complex_dtype": self.complex_dtype,
            "convention": self.convention.as_mapping(),
            "device": self.device,
            "identity": self.identity,
            "implementation": self.implementation,
            "real_dtype": self.real_dtype,
        }

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object],
    ) -> AngularSpectrumRealization:
        """
        Restore an exact realization from an admitted binding.
        """

        convention = value["convention"]
        if not isinstance(convention, Mapping):
            raise ValueError("field_convention_invalid")
        return cls(
            device=str(value["device"]),
            working_memory_bytes=None,
            convention=AngularSpectrumConvention.from_mapping(convention),
            identity=str(value["identity"]),
            implementation=str(value["implementation"]),
            complex_dtype=str(value["complex_dtype"]),
            real_dtype=str(value["real_dtype"]),
        )


@dataclass(frozen=True, slots=True)
class AngularSpectrumQualification:
    """
    Record checks made on one exact realization.
    """

    realization: AngularSpectrumRealization
    reconstruction_error: float
    refinement_error: float
    is_qualified: bool
    reason: str | None = None
    complex_field_error: float = math.inf
    airy_radius_error: float = math.inf

    def as_mapping(self) -> dict[str, object]:
        """
        Return qualification evidence without changing its realization.
        """

        expected_airy_radius_m = (
            1.22
            * _AIRY_WAVELENGTH_M
            * _AIRY_FOCAL_DISTANCE_M
            / _AIRY_APERTURE_DIAMETER_M
        )
        return {
            "airy_limit": {
                "aperture_diameter_m": repr(
                    _AIRY_APERTURE_DIAMETER_M
                ),
                "expected_first_dark_radius_m": repr(
                    expected_airy_radius_m
                ),
                "focal_distance_m": repr(_AIRY_FOCAL_DISTANCE_M),
                "maximum_relative_radius_error": repr(
                    _AIRY_MAXIMUM_RADIUS_ERROR
                ),
                "measurement": "first minimum on averaged central rows",
                "paraxial_numerical_aperture": repr(
                    _AIRY_PARAXIAL_NUMERICAL_APERTURE
                ),
                "search_window": "0.6 to 1.4 expected radius",
                "shape": [_AIRY_SAMPLE_COUNT, _AIRY_SAMPLE_COUNT],
                "spacing_m": repr(_AIRY_SPACING_M),
                "wavelength_m": repr(_AIRY_WAVELENGTH_M),
            },
            "airy_radius_error": repr(self.airy_radius_error),
            "direct_reference": {
                "comparison": "relative complex l2",
                "comparison_shape": [
                    _DIRECT_REFERENCE_SIZE // 2,
                    _DIRECT_REFERENCE_SIZE // 2,
                ],
                "distance_m": repr(_DIRECT_REFERENCE_DISTANCE_M),
                "maximum_relative_error": repr(
                    _DIRECT_REFERENCE_MAXIMUM_ERROR
                ),
                "method": "Rayleigh-Sommerfeld first integral",
                "normalization": (
                    "absolute field, error divided by reference l2"
                ),
                "propagation_direction": "positive z",
                "shape": [
                    _DIRECT_REFERENCE_SIZE,
                    _DIRECT_REFERENCE_SIZE,
                ],
                "spacing_m": repr(_DIRECT_REFERENCE_SPACING_M),
                "wavelength_m": repr(_DIRECT_REFERENCE_WAVELENGTH_M),
            },
            "complex_field_error": repr(self.complex_field_error),
            "qualified": self.is_qualified,
            "reason": self.reason,
            "reconstruction_error": repr(self.reconstruction_error),
            "refinement_error": repr(self.refinement_error),
        }


class FieldMemoryUnavailable(RuntimeError):
    """
    Report that the bound realization cannot hold one propagation plane.
    """


@dataclass(frozen=True, slots=True)
class _PreparedField:
    """
    Keep one source spectrum ready for repeated bounded propagation.
    """

    spectrum: torch.Tensor | None
    longitudinal_wave_number: torch.Tensor
    is_propagating: torch.Tensor
    crop: tuple[slice, slice]
    source_shape: tuple[int, int]
    batch_size: int
    device: torch.device

    def at(self, distance_m: float) -> NDArray[numpy.complex128]:
        """
        Propagate the prepared source to one non-negative distance.
        """

        return self.at_distances((distance_m,))[0]

    def at_distances(
        self,
        distances_m: Sequence[float],
    ) -> NDArray[numpy.complex128]:
        """
        Propagate one prepared source through bounded axial batches.
        """

        distances = tuple(float(value) for value in distances_m)
        if any(value < 0 or not math.isfinite(value) for value in distances):
            raise ValueError("field_scale_invalid")
        if not distances:
            return numpy.empty(
                (0, *self.source_shape),
                dtype=numpy.complex128,
            )
        batches = []
        for start in range(0, len(distances), self.batch_size):
            stop = start + self.batch_size
            planes = self.planes(distances[start:stop])
            batches.append(
                planes.detach().cpu().numpy().astype(
                    numpy.complex128,
                    copy=False,
                )
            )
        return numpy.concatenate(batches, axis=0)

    def planes(self, distances_m: Sequence[float]) -> torch.Tensor:
        """
        Return one already bounded batch on the bound device.
        """

        distances = torch.tensor(
            tuple(distances_m),
            dtype=torch.float64,
            device=self.device,
        )
        if self.spectrum is None:
            return torch.zeros(
                (len(distances_m), *self.source_shape),
                dtype=torch.complex128,
                device=self.device,
            )
        transfer = torch.exp(
            1j
            * distances[:, None, None]
            * self.longitudinal_wave_number[None, :, :]
        )
        transfer = torch.where(
            distances[:, None, None] == 0,
            torch.ones_like(transfer),
            transfer * self.is_propagating[None, :, :],
        )
        planes = torch.fft.ifft2(
            self.spectrum[None, :, :] * transfer,
            dim=(-2, -1),
            norm="backward",
        )
        return planes[(slice(None), *self.crop)]


@dataclass(frozen=True, slots=True)
class AxialObservation:
    """
    Retain component intensity peaks observed at ordered axial distances.
    """

    distances_m: tuple[float, ...]
    observed_components: tuple[str, ...]
    peak_intensities: tuple[float, ...]
    component_peak_intensities: Mapping[str, tuple[float, ...]]

    def __post_init__(self) -> None:
        """
        Freeze one finite observation with a complete component curve.
        """

        if (
            not self.distances_m
            or any(
                not math.isfinite(value) or value < 0
                for value in self.distances_m
            )
            or any(
                right <= left
                for left, right in zip(
                    self.distances_m,
                    self.distances_m[1:],
                )
            )
        ):
            raise ValueError("field_observation_distances_invalid")
        if (
            not self.observed_components
            or len(set(self.observed_components))
            != len(self.observed_components)
        ):
            raise ValueError("field_observed_components_invalid")
        if (
            len(self.peak_intensities) != len(self.distances_m)
            or any(
                not math.isfinite(value) or value < 0
                for value in self.peak_intensities
            )
        ):
            raise ValueError("field_observation_intensities_invalid")
        if any(
            len(values) != len(self.distances_m)
            or any(
                not math.isfinite(value) or value < 0
                for value in values
            )
            for values in self.component_peak_intensities.values()
        ):
            raise ValueError("field_component_observation_invalid")
        object.__setattr__(
            self,
            "component_peak_intensities",
            MappingProxyType(
                {
                    name: tuple(values)
                    for name, values in (
                        self.component_peak_intensities.items()
                    )
                }
            ),
        )


@dataclass(frozen=True, slots=True)
class FieldPropagation:
    """
    Retain one finished axial observation and its matching propagated field.
    """

    observation: AxialObservation
    principal_distance_m: float
    principal_field: Field
    input_component_power: Mapping[str, float]
    realization: Mapping[str, object]

    def __post_init__(self) -> None:
        """
        Freeze one internally consistent, non-executable propagation outcome.
        """

        if self.principal_distance_m not in self.observation.distances_m:
            raise ValueError("field_matching_distance_missing")
        if not set(self.observation.observed_components) <= set(
            self.principal_field.component_names
        ):
            raise ValueError("field_observed_components_invalid")
        if set(self.input_component_power) != set(
            self.principal_field.component_names
        ):
            raise ValueError("field_input_power_incomplete")
        if any(
            not math.isfinite(value) or value < 0
            for value in self.input_component_power.values()
        ):
            raise ValueError("field_input_power_invalid")
        object.__setattr__(
            self,
            "input_component_power",
            MappingProxyType(dict(self.input_component_power)),
        )
        object.__setattr__(
            self,
            "realization",
            MappingProxyType(dict(self.realization)),
        )


def observe_angular_spectrum() -> AngularSpectrumRealization:
    """
    Observe and bind one exact local Torch realization.
    """

    if torch.cuda.is_available():
        device = f"cuda:{torch.cuda.current_device()}"
    else:
        device = "cpu"
    return AngularSpectrumRealization(
        device=device,
        working_memory_bytes=_safe_working_memory(
            observe_available_device_memory(device).available_bytes
        ),
    )


def qualify_angular_spectrum(
    realization: AngularSpectrumRealization | None = None,
) -> AngularSpectrumQualification:
    """
    Qualify the exact production configuration on its bound device.
    """

    selected = realization or observe_angular_spectrum()
    try:
        working_memory_bytes = _execution_budget(selected)
    except (OSError, RuntimeError) as error:
        return AngularSpectrumQualification(
            selected,
            math.inf,
            math.inf,
            False,
            type(error).__name__,
        )
    if working_memory_bytes <= 0:
        return AngularSpectrumQualification(
            selected,
            math.inf,
            math.inf,
            False,
            "field_memory_unavailable",
        )
    try:
        reconstruction_error = _reconstruction_error(
            selected,
            working_memory_bytes,
        )
        refinement_error = _refinement_error(
            selected,
            working_memory_bytes,
        )
        complex_field_error = _direct_scalar_error(
            selected,
            working_memory_bytes,
        )
        airy_radius_error = _airy_radius_error(
            selected,
            working_memory_bytes,
        )
    except (FieldMemoryUnavailable, RuntimeError) as error:
        return AngularSpectrumQualification(
            selected,
            math.inf,
            math.inf,
            False,
            type(error).__name__,
        )
    is_qualified = (
        reconstruction_error <= 1e-12
        and refinement_error <= 5e-3
        and complex_field_error <= _DIRECT_REFERENCE_MAXIMUM_ERROR
        and airy_radius_error <= _AIRY_MAXIMUM_RADIUS_ERROR
    )
    return AngularSpectrumQualification(
        selected,
        reconstruction_error,
        refinement_error,
        is_qualified,
        None if is_qualified else "field_numerical_qualification_failed",
        complex_field_error=complex_field_error,
        airy_radius_error=airy_radius_error,
    )


def propagate_field(
    field: Field,
    *,
    distance_range_m: tuple[float, float],
    preferred_distance_m: float,
    components: tuple[str, ...],
    realization: AngularSpectrumRealization,
) -> FieldPropagation:
    """
    Observe one interval and retain its principal propagated field.
    """

    lower_m, upper_m = distance_range_m
    if (
        not math.isfinite(lower_m)
        or not math.isfinite(upper_m)
        or lower_m < 0
        or upper_m <= lower_m
        or not math.isfinite(preferred_distance_m)
        or not lower_m <= preferred_distance_m <= upper_m
    ):
        raise ValueError("field_distance_range_invalid")
    if (
        not components
        or len(set(components)) != len(components)
        or not set(components) <= set(field.component_names)
    ):
        raise ValueError("field_observed_components_invalid")
    budget = _execution_budget(realization)
    component_count = len(
        (*field.electric_components, *field.magnetic_components)
    )
    component_budget = budget // max(component_count, 1)
    electric = {
        name: _prepare(
            field.electric(name),
            spacing_m=field.surface.spacing_m,
            wavelength_m=field.wavelength_m,
            realization=realization,
            working_memory_bytes=component_budget,
            requested_planes=17,
        )[0]
        for name in field.component_names
    }
    magnetic = {
        component.name: _prepare(
            field.magnetic(component.name),
            spacing_m=field.surface.spacing_m,
            wavelength_m=field.wavelength_m,
            realization=realization,
            working_memory_bytes=component_budget,
            requested_planes=17,
        )[0]
        for component in field.magnetic_components
    }
    survey_distances = tuple(
        float(value)
        for value in numpy.linspace(lower_m, upper_m, 17)
    )
    survey = _observe(
        electric,
        survey_distances,
        components=components,
    )
    survey_index = _principal(
        survey.distances_m,
        survey.peak_intensities,
        preferred_distance_m,
    )
    observations = {
        distance: (
            survey.peak_intensities[index],
            {
                name: values[index]
                for name, values in (
                    survey.component_peak_intensities.items()
                )
            },
        )
        for index, distance in enumerate(survey.distances_m)
    }
    if 0 < survey_index < len(survey_distances) - 1:
        refinement_distances = tuple(
            float(value)
            for value in numpy.linspace(
                survey_distances[survey_index - 1],
                survey_distances[survey_index + 1],
                17,
            )
        )
        refinement = _observe(
            electric,
            refinement_distances,
            components=components,
        )
        observations.update(
            {
                distance: (
                    refinement.peak_intensities[index],
                    {
                        name: values[index]
                        for name, values in (
                            refinement.component_peak_intensities.items()
                        )
                    },
                )
                for index, distance in enumerate(
                    refinement.distances_m
                )
            }
        )
    distances = tuple(sorted(observations))
    observation = AxialObservation(
        distances_m=distances,
        observed_components=components,
        peak_intensities=tuple(
            observations[distance][0] for distance in distances
        ),
        component_peak_intensities={
            name: tuple(
                observations[distance][1][name]
                for distance in distances
            )
            for name in field.component_names
        },
    )
    principal_index = _principal(
        observation.distances_m,
        observation.peak_intensities,
        preferred_distance_m,
    )
    principal_distance_m = observation.distances_m[principal_index]
    return FieldPropagation(
        observation=observation,
        principal_distance_m=principal_distance_m,
        principal_field=_propagated_field(
            field,
            electric,
            magnetic,
            principal_distance_m,
        ),
        input_component_power={
            name: float(numpy.sum(numpy.abs(field.electric(name)) ** 2))
            for name in field.component_names
        },
        realization=_propagation_provenance(
            realization,
            electric,
            magnetic,
        ),
    )


def _observe(
    prepared: Mapping[str, _PreparedField],
    distances_m: tuple[float, ...],
    *,
    components: tuple[str, ...],
) -> AxialObservation:
    peaks, component_peaks = _survey(
        prepared,
        distances_m,
        observed_components=components,
    )
    return AxialObservation(
        distances_m=distances_m,
        observed_components=components,
        peak_intensities=tuple(float(value) for value in peaks),
        component_peak_intensities={
            name: tuple(float(value) for value in values)
            for name, values in component_peaks.items()
        },
    )


def _principal(
    distances_m: tuple[float, ...],
    peak_intensities: tuple[float, ...],
    preferred_distance_m: float,
) -> int:
    return min(
        range(len(distances_m)),
        key=lambda index: (
            -peak_intensities[index],
            abs(distances_m[index] - preferred_distance_m),
            distances_m[index],
        ),
    )


def _propagated_field(
    source: Field,
    electric: Mapping[str, _PreparedField],
    magnetic: Mapping[str, _PreparedField],
    distance_m: float,
) -> Field:
    electric_components = tuple(
        FieldComponent(
            name,
            _immutable(electric[name].at(distance_m)),
        )
        for name in source.component_names
    )
    magnetic_components = tuple(
        FieldComponent(
            component.name,
            _immutable(magnetic[component.name].at(distance_m)),
        )
        for component in source.magnetic_components
    )
    return Field(
        wavelength_m=source.wavelength_m,
        surface=PlaneSurface(
            source.surface.position_m + distance_m,
            source.surface.spacing_m,
            source.surface.shape,
        ),
        frame=source.frame,
        medium=source.medium,
        basis=source.basis,
        electric_components=electric_components,
        magnetic_components=magnetic_components,
        source_references=source.source_references,
        incident_reference_power=source.incident_reference_power,
    )


def _propagation_provenance(
    realization: AngularSpectrumRealization,
    electric: Mapping[str, _PreparedField],
    magnetic: Mapping[str, _PreparedField],
) -> dict[str, object]:
    prepared = (*electric.items(), *magnetic.items())
    spectra = [
        name for name, item in prepared if item.spectrum is not None
    ]
    return {
        **realization.as_mapping(),
        "prepared_spectra": spectra,
        "spectrum_preparations": {
            name: 1 for name in sorted(spectra)
        },
    }


def _prepare(
    field: NDArray[numpy.complexfloating],
    *,
    spacing_m: float,
    wavelength_m: float,
    realization: AngularSpectrumRealization,
    working_memory_bytes: int,
    requested_planes: int,
) -> tuple[_PreparedField, int]:
    """
    Prepare one source without re-observing the selected device.
    """

    source = numpy.asarray(field, dtype=numpy.complex128)
    if source.ndim != 2 or min(source.shape) < 2:
        raise ValueError("field_shape_invalid")
    if not numpy.isfinite(source).all():
        raise ValueError("field_not_finite")
    if spacing_m <= 0 or wavelength_m <= 0:
        raise ValueError("field_scale_invalid")
    rows = source.shape[0] * realization.convention.padding_factor
    columns = source.shape[1] * realization.convention.padding_factor
    batch_size = _batch_size(
        (rows, columns),
        working_memory_bytes=working_memory_bytes,
        requested_planes=requested_planes,
    )
    device = torch.device(realization.device)
    source_tensor = torch.tensor(
        source,
        dtype=torch.complex128,
        device=device,
    )
    padded, crop = _pad(source_tensor, realization.convention.padding_factor)
    wave_number_magnitude = torch.tensor(
        2 * math.pi / wavelength_m,
        dtype=torch.float64,
        device=device,
    )
    wave_number_x = (
        2
        * math.pi
        * torch.fft.fftfreq(
            columns,
            d=spacing_m,
            dtype=torch.float64,
            device=device,
        )
    )
    wave_number_y = (
        2
        * math.pi
        * torch.fft.fftfreq(
            rows,
            d=spacing_m,
            dtype=torch.float64,
            device=device,
        )
    )
    transverse_squared = (
        wave_number_y[:, None].square()
        + wave_number_x[None, :].square()
    )
    is_propagating = transverse_squared <= wave_number_magnitude.square()
    longitudinal = torch.sqrt(
        torch.clamp(
            wave_number_magnitude.square() - transverse_squared,
            min=0.0,
        )
    )
    spectrum = (
        None
        if not numpy.any(source)
        else torch.fft.fft2(padded, dim=(-2, -1), norm="backward")
    )
    return (
        _PreparedField(
            spectrum=spectrum,
            longitudinal_wave_number=longitudinal,
            is_propagating=is_propagating,
            crop=crop,
            source_shape=source.shape,
            batch_size=batch_size,
            device=device,
        ),
        batch_size,
    )


def _survey(
    prepared: Mapping[str, _PreparedField],
    distances_m: tuple[float, ...],
    *,
    observed_components: tuple[str, ...],
) -> tuple[
    NDArray[numpy.float64],
    dict[str, NDArray[numpy.float64]],
]:
    sources = tuple(prepared.items())
    if not sources:
        raise ValueError("field_components_empty")
    batch_size = min(source.batch_size for _, source in sources)
    total_peaks: list[float] = []
    component_peaks: dict[str, list[float]] = {
        name: [] for name, _ in sources
    }
    observed = set(observed_components)
    for start in range(0, len(distances_m), batch_size):
        distances = distances_m[start : start + batch_size]
        total_intensity: torch.Tensor | None = None
        for name, source in sources:
            planes = source.planes(distances)
            intensity = planes.abs().square()
            peaks = torch.amax(intensity, dim=(-2, -1))
            component_peaks[name].extend(
                float(value)
                for value in peaks.detach().cpu().tolist()
            )
            if name in observed:
                total_intensity = (
                    intensity
                    if total_intensity is None
                    else total_intensity + intensity
                )
        if total_intensity is None:
            raise ValueError("field_components_empty")
        peaks = torch.amax(total_intensity, dim=(-2, -1))
        total_peaks.extend(
            float(value) for value in peaks.detach().cpu().tolist()
        )
    return (
        numpy.asarray(total_peaks, dtype=numpy.float64),
        {
            name: numpy.asarray(values, dtype=numpy.float64)
            for name, values in component_peaks.items()
        },
    )


def _immutable(
    values: NDArray[numpy.complexfloating],
) -> NDArray[numpy.complex128]:
    samples = numpy.array(
        values,
        dtype="<c16",
        order="C",
        copy=True,
    )
    samples.setflags(write=False)
    return samples


def _execution_budget(realization: AngularSpectrumRealization) -> int:
    current = _safe_working_memory(
        observe_available_device_memory(
            realization.device
        ).available_bytes
    )
    if realization.working_memory_bytes is None:
        return current
    return min(realization.working_memory_bytes, current)


def _batch_size(
    padded_shape: tuple[int, int],
    *,
    working_memory_bytes: int,
    requested_planes: int,
) -> int:
    pixels = math.prod(padded_shape)
    static_bytes = pixels * (
        2 * _COMPLEX_BYTES + 3 * _REAL_BYTES + 1
    )
    plane_bytes = pixels * (
        3 * _COMPLEX_BYTES + _REAL_BYTES
    )
    available = working_memory_bytes - static_bytes
    if available < plane_bytes:
        raise FieldMemoryUnavailable("field_memory_unavailable")
    return min(requested_planes, available // plane_bytes)


def _reconstruction_error(
    realization: AngularSpectrumRealization,
    working_memory_bytes: int,
) -> float:
    axis = numpy.linspace(-1.0, 1.0, 32, dtype=numpy.float64)
    position_x, position_y = numpy.meshgrid(axis, axis)
    window = numpy.outer(numpy.hanning(32), numpy.hanning(32))
    source = numpy.asarray(
        numpy.exp(-3.0 * (position_x**2 + position_y**2)) * window,
        dtype=numpy.complex128,
    )
    prepared, _ = _prepare(
        source,
        spacing_m=100e-9,
        wavelength_m=400e-9,
        realization=realization,
        working_memory_bytes=working_memory_bytes,
        requested_planes=1,
    )
    reconstructed = prepared.at(0.0)
    return float(numpy.max(numpy.abs(reconstructed - source)))


def _refinement_error(
    realization: AngularSpectrumRealization,
    working_memory_bytes: int,
) -> float:
    peaks = []
    extent_m = 12e-6
    for size in (64, 128):
        spacing_m = extent_m / size
        axis = (
            numpy.arange(size, dtype=numpy.float64) - size // 2
        ) * spacing_m
        position_x, position_y = numpy.meshgrid(axis, axis)
        window = numpy.outer(numpy.hanning(size), numpy.hanning(size))
        source = numpy.asarray(
            numpy.exp(
                -(position_x**2 + position_y**2) / (2e-6) ** 2
            )
            * window,
            dtype=numpy.complex128,
        )
        prepared, _ = _prepare(
            source,
            spacing_m=spacing_m,
            wavelength_m=400e-9,
            realization=realization,
            working_memory_bytes=working_memory_bytes,
            requested_planes=1,
        )
        propagated = prepared.at(10e-6)
        peaks.append(float(abs(propagated[size // 2, size // 2]) ** 2))
    return abs(peaks[1] - peaks[0]) / peaks[1]


def _direct_scalar_error(
    realization: AngularSpectrumRealization,
    working_memory_bytes: int,
) -> float:
    """
    Compare one propagated field with direct Rayleigh-Sommerfeld quadrature.
    """

    size = _DIRECT_REFERENCE_SIZE
    spacing_m = _DIRECT_REFERENCE_SPACING_M
    wavelength_m = _DIRECT_REFERENCE_WAVELENGTH_M
    distance_m = _DIRECT_REFERENCE_DISTANCE_M
    device = torch.device(realization.device)
    axis = (
        torch.arange(size, dtype=torch.float64, device=device)
        - (size - 1) / 2
    ) * spacing_m
    position_y, position_x = torch.meshgrid(
        axis,
        axis,
        indexing="ij",
    )
    source = torch.exp(
        -(position_x.square() + position_y.square())
        / (2 * (800e-9) ** 2)
    ).to(torch.complex128)
    prepared, _ = _prepare(
        source.detach().cpu().numpy(),
        spacing_m=spacing_m,
        wavelength_m=wavelength_m,
        realization=realization,
        working_memory_bytes=working_memory_bytes,
        requested_planes=1,
    )
    propagated = torch.as_tensor(
        prepared.at(distance_m),
        dtype=torch.complex128,
        device=device,
    )

    separation_y = (
        position_y[:, :, None, None]
        - position_y[None, None, :, :]
    )
    separation_x = (
        position_x[:, :, None, None]
        - position_x[None, None, :, :]
    )
    distance = torch.sqrt(
        separation_x.square()
        + separation_y.square()
        + distance_m**2
    )
    wave_number = 2 * math.pi / wavelength_m
    kernel = (
        torch.exp(1j * wave_number * distance)
        * distance_m
        * (1 - 1j * wave_number * distance)
        / (2 * math.pi * distance.pow(3))
    )
    reference = (
        torch.sum(
            source[None, None, :, :] * kernel,
            dim=(-2, -1),
        )
        * spacing_m**2
    )
    comparison = slice(size // 4, 3 * size // 4)
    difference = (
        propagated[comparison, comparison]
        - reference[comparison, comparison]
    )
    return float(
        (
            torch.linalg.vector_norm(difference)
            / torch.linalg.vector_norm(
                reference[comparison, comparison]
            )
        )
        .detach()
        .cpu()
    )


def _airy_radius_error(
    realization: AngularSpectrumRealization,
    working_memory_bytes: int,
) -> float:
    """
    Compare one low-na circular-pupil focus with the Airy first dark radius.
    """

    size = _AIRY_SAMPLE_COUNT
    spacing_m = _AIRY_SPACING_M
    wavelength_m = _AIRY_WAVELENGTH_M
    focal_distance_m = _AIRY_FOCAL_DISTANCE_M
    aperture_diameter_m = _AIRY_APERTURE_DIAMETER_M
    device = torch.device(realization.device)
    axis = (
        torch.arange(size, dtype=torch.float64, device=device)
        - (size - 1) / 2
    ) * spacing_m
    position_y, position_x = torch.meshgrid(
        axis,
        axis,
        indexing="ij",
    )
    radius = torch.sqrt(position_x.square() + position_y.square())
    wave_number = 2 * math.pi / wavelength_m
    is_in_pupil = radius <= aperture_diameter_m / 2
    converging_phase = torch.exp(
        -1j
        * wave_number
        * (
            torch.sqrt(focal_distance_m**2 + radius.square())
            - focal_distance_m
        )
    )
    source = torch.where(
        is_in_pupil,
        converging_phase,
        torch.zeros_like(converging_phase),
    ).to(torch.complex128)
    prepared, _ = _prepare(
        source.detach().cpu().numpy(),
        spacing_m=spacing_m,
        wavelength_m=wavelength_m,
        realization=realization,
        working_memory_bytes=working_memory_bytes,
        requested_planes=1,
    )
    focal_field = torch.as_tensor(
        prepared.at(focal_distance_m),
        dtype=torch.complex128,
        device=device,
    )
    central_line = torch.mean(
        focal_field[size // 2 - 1 : size // 2 + 1],
        dim=0,
    )
    expected_radius = (
        1.22
        * wavelength_m
        * focal_distance_m
        / aperture_diameter_m
    )
    candidates = torch.nonzero(
        (axis > 0.6 * expected_radius)
        & (axis < 1.4 * expected_radius),
        as_tuple=False,
    ).flatten()
    candidate_intensity = central_line[candidates].abs().square()
    observed_radius = axis[
        candidates[torch.argmin(candidate_intensity)]
    ]
    return float(
        (
            torch.abs(observed_radius - expected_radius)
            / expected_radius
        )
        .detach()
        .cpu()
    )


def _pad(
    field: torch.Tensor,
    factor: int,
) -> tuple[torch.Tensor, tuple[slice, slice]]:
    target_rows = field.shape[0] * factor
    target_columns = field.shape[1] * factor
    before_rows = (target_rows - field.shape[0]) // 2
    before_columns = (target_columns - field.shape[1]) // 2
    after_rows = target_rows - field.shape[0] - before_rows
    after_columns = target_columns - field.shape[1] - before_columns
    padded = torch.nn.functional.pad(
        field,
        (before_columns, after_columns, before_rows, after_rows),
    )
    crop = (
        slice(before_rows, before_rows + field.shape[0]),
        slice(before_columns, before_columns + field.shape[1]),
    )
    return padded, crop


def _safe_working_memory(available_bytes: int) -> int:
    reserve = max(512 * 1024**2, available_bytes // 5)
    return max(0, available_bytes - reserve)
