from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import math
from types import MappingProxyType

import torch

from ..authority import Document

from ._device_memory import observe_available_device_memory
from .sample import ComponentBasis, Field, FieldComponent, PlaneSurface

VECTOR_ANGULAR_SPECTRUM_CAPABILITY = "vector_angular_spectrum_propagation"
VECTOR_ANGULAR_SPECTRUM_REALIZATION = "metacraft.field.vector_angular_spectrum"
VECTOR_ANGULAR_SPECTRUM_BINDING_SCHEMA = (
    "metacraft.binding.vector_angular_spectrum_propagation"
)
_SPEED_OF_LIGHT_M_PER_S = 299_792_458.0
_VACUUM_PERMEABILITY_H_PER_M = 1.256_637_062_12e-6
_QUALIFICATION_LIMIT = 1e-12


@dataclass(frozen=True, slots=True)
class VectorAngularSpectrumConvention:
    """
    Freeze the physical and numerical meaning of one vector propagation.
    """

    padding_factor: int = 2
    evanescent_terms: str = "discarded"
    coordinate_order: str = "y x"
    propagation_direction: str = "positive z"
    input_basis: str = "transverse linear"
    output_basis: str = "cartesian"
    longitudinal_rule: str = "wave vector dot electric field equals zero"
    power_measure: str = "integrated longitudinal Poynting vector"
    power_surface: str = "full padded plane; returned field cropped to source window"
    magnetic_storage: str = (
        "reconstructed for power and retained only inside realization"
    )
    wavelength_meaning: str = "wavelength in propagation medium"

    def as_mapping(self) -> dict[str, object]:
        """
        Return every convention that determines the scientific field.
        """

        return {
            "coordinate_order": self.coordinate_order,
            "evanescent_terms": self.evanescent_terms,
            "input_basis": self.input_basis,
            "longitudinal_rule": self.longitudinal_rule,
            "magnetic_storage": self.magnetic_storage,
            "output_basis": self.output_basis,
            "padding_factor": self.padding_factor,
            "power_measure": self.power_measure,
            "power_surface": self.power_surface,
            "propagation_direction": self.propagation_direction,
            "wavelength_meaning": self.wavelength_meaning,
        }

    @classmethod
    def from_mapping(
        cls,
        values: Mapping[str, object],
    ) -> VectorAngularSpectrumConvention:
        """
        Restore one exact reviewed convention.
        """

        convention = cls(
            padding_factor=int(str(values["padding_factor"])),
            evanescent_terms=str(values["evanescent_terms"]),
            coordinate_order=str(values["coordinate_order"]),
            propagation_direction=str(values["propagation_direction"]),
            input_basis=str(values["input_basis"]),
            output_basis=str(values["output_basis"]),
            longitudinal_rule=str(values["longitudinal_rule"]),
            magnetic_storage=str(values["magnetic_storage"]),
            power_measure=str(values["power_measure"]),
            power_surface=str(values["power_surface"]),
            wavelength_meaning=str(values["wavelength_meaning"]),
        )
        if convention != cls():
            raise ValueError("vector_field_convention_unsupported")
        return convention


@dataclass(frozen=True, slots=True)
class VectorAngularSpectrumRealization:
    """
    Bind one Torch vector propagation to its selected device.
    """

    device: str
    working_memory_bytes: int | None = field(compare=False, repr=False)
    convention: VectorAngularSpectrumConvention = field(
        default_factory=VectorAngularSpectrumConvention
    )
    identity: str = VECTOR_ANGULAR_SPECTRUM_REALIZATION
    implementation: str = "torch"
    complex_dtype: str = "complex128"
    real_dtype: str = "float64"

    def __post_init__(self) -> None:
        """
        Refuse an alternate implementation or hidden numerical convention.
        """

        if self.identity != VECTOR_ANGULAR_SPECTRUM_REALIZATION:
            raise ValueError("vector_field_realization_unsupported")
        if self.implementation != "torch":
            raise ValueError("vector_field_implementation_unsupported")
        if self.device != "cpu" and not _is_cuda_device(self.device):
            raise ValueError("vector_field_device_unsupported")
        if self.complex_dtype != "complex128":
            raise ValueError("vector_field_complex_dtype_unsupported")
        if self.real_dtype != "float64":
            raise ValueError("vector_field_real_dtype_unsupported")
        if self.working_memory_bytes is not None and self.working_memory_bytes < 0:
            raise ValueError("vector_field_working_memory_invalid")
        if self.convention != VectorAngularSpectrumConvention():
            raise ValueError("vector_field_convention_unsupported")

    def as_mapping(self) -> dict[str, object]:
        """
        Return identity-bearing facts without transient capacity.
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
        values: Mapping[str, object],
    ) -> VectorAngularSpectrumRealization:
        """
        Restore one bound realization without inventing capacity.
        """

        convention = values["convention"]
        if not isinstance(convention, Mapping):
            raise ValueError("vector_field_convention_invalid")
        return cls(
            device=str(values["device"]),
            working_memory_bytes=None,
            convention=VectorAngularSpectrumConvention.from_mapping(convention),
            identity=str(values["identity"]),
            implementation=str(values["implementation"]),
            complex_dtype=str(values["complex_dtype"]),
            real_dtype=str(values["real_dtype"]),
        )


@dataclass(frozen=True, slots=True)
class VectorAngularSpectrumQualification:
    """
    Record the independent facts earned by one exact realization.
    """

    realization: VectorAngularSpectrumRealization
    wave_vector_error: float
    transversality_error: float
    phase_advance_error: float
    longitudinal_recovery_error: float
    direct_component_error: float
    poynting_error: float
    is_qualified: bool
    reason: str | None = None

    def __post_init__(self) -> None:
        """
        Reject a success that its recorded errors did not earn.
        """

        errors = (
            self.wave_vector_error,
            self.transversality_error,
            self.phase_advance_error,
            self.longitudinal_recovery_error,
            self.direct_component_error,
            self.poynting_error,
        )
        if any(value < 0 or math.isnan(value) for value in errors):
            raise ValueError("vector_field_qualification_error_invalid")
        if self.is_qualified != (self.reason is None):
            raise ValueError("vector_field_qualification_inconsistent")
        if self.is_qualified and (
            not all(math.isfinite(value) for value in errors)
            or max(errors) > _QUALIFICATION_LIMIT
        ):
            raise ValueError("vector_field_qualification_unearned")

    def as_mapping(self) -> dict[str, object]:
        """
        Return one reviewable qualification record.
        """

        return {
            "applicability": {
                "component_basis": ("transverse linear input; cartesian output"),
                "coordinate_order": "y x",
                "evanescent_terms": "discarded",
                "medium": "air or vacuum",
                "magnetic_storage": "reconstructed transiently for power",
                "power_measure": ("integrated longitudinal Poynting vector"),
                "power_surface": (
                    "full padded plane; returned field cropped " "to source window"
                ),
                "propagation_direction": "positive z",
                "sampling_bound": ("spacing at most one half in-medium wavelength"),
            },
            "direct_reference": {
                "comparison": "relative complex l2",
                "components": ["x", "y", "z"],
                "method": "explicit two-dimensional discrete transform",
                "maximum_error": repr(_QUALIFICATION_LIMIT),
            },
            "direct_component_error": repr(self.direct_component_error),
            "longitudinal_recovery_error": repr(self.longitudinal_recovery_error),
            "oblique_plane_wave": {
                "checks": [
                    "wave-vector direction",
                    "transversality",
                    "phase advance",
                    "longitudinal recovery",
                    "longitudinal Poynting power",
                ],
                "maximum_error": repr(_QUALIFICATION_LIMIT),
            },
            "phase_advance_error": repr(self.phase_advance_error),
            "poynting_error": repr(self.poynting_error),
            "qualified": self.is_qualified,
            "realization": self.realization.as_mapping(),
            "reason": self.reason,
            "transversality_error": repr(self.transversality_error),
            "wave_vector_error": repr(self.wave_vector_error),
        }

    @classmethod
    def from_mapping(
        cls,
        values: Mapping[str, object],
    ) -> VectorAngularSpectrumQualification:
        """
        Restore only an exact, self-consistent qualification record.
        """

        realization = values["realization"]
        if not isinstance(realization, Mapping):
            raise ValueError("vector_field_qualification_invalid")
        restored = cls(
            realization=VectorAngularSpectrumRealization.from_mapping(realization),
            wave_vector_error=float(str(values["wave_vector_error"])),
            transversality_error=float(str(values["transversality_error"])),
            phase_advance_error=float(str(values["phase_advance_error"])),
            longitudinal_recovery_error=float(
                str(values["longitudinal_recovery_error"])
            ),
            direct_component_error=float(str(values["direct_component_error"])),
            poynting_error=float(str(values["poynting_error"])),
            is_qualified=values["qualified"] is True,
            reason=(None if values["reason"] is None else str(values["reason"])),
        )
        if restored.as_mapping() != dict(values):
            raise ValueError("vector_field_qualification_invalid")
        return restored


@dataclass(frozen=True, slots=True)
class LongitudinalPowerPlane:
    """
    Retain the sampled longitudinal Poynting density of one returned plane.
    """

    surface: PlaneSurface
    power_density_w_per_m2: torch.Tensor = field(
        compare=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        """
        Freeze one finite density map on the same grid as its electric field.
        """

        density = self.power_density_w_per_m2
        if (
            density.dtype is not torch.float64
            or tuple(density.shape) != self.surface.shape
            or not bool(torch.all(torch.isfinite(density)))
        ):
            raise ValueError("longitudinal_power_plane_invalid")
        object.__setattr__(
            self,
            "power_density_w_per_m2",
            density.detach().cpu().clone(),
        )

    def integrate(self, is_selected: torch.Tensor | None = None) -> float:
        """
        Integrate all samples or one explicitly bounded region.
        """

        if is_selected is None:
            selected = self.power_density_w_per_m2
        else:
            is_selected = is_selected.to(device="cpu", dtype=torch.bool)
            if tuple(is_selected.shape) != self.surface.shape:
                raise ValueError("longitudinal_power_mask_invalid")
            selected = self.power_density_w_per_m2[is_selected]
        return float(torch.sum(selected) * self.surface.spacing_m**2)


@dataclass(frozen=True, slots=True)
class ElectromagneticPropagation:
    """
    Retain one propagated field and its longitudinal power balance.
    """

    field: Field
    distance_m: float
    input_longitudinal_power_w: float
    output_longitudinal_power_w: float
    output_longitudinal_power: LongitudinalPowerPlane
    realization: Mapping[str, object]

    def __post_init__(self) -> None:
        """
        Freeze one finite propagation outcome.
        """

        if (
            not math.isfinite(self.distance_m)
            or self.distance_m < 0
            or not math.isfinite(self.input_longitudinal_power_w)
            or self.input_longitudinal_power_w < 0
            or not math.isfinite(self.output_longitudinal_power_w)
            or self.output_longitudinal_power_w < 0
        ):
            raise ValueError("vector_field_propagation_invalid")
        if self.output_longitudinal_power.surface != self.field.surface:
            raise ValueError("vector_field_power_surface_mismatch")
        object.__setattr__(
            self,
            "realization",
            MappingProxyType(dict(self.realization)),
        )


@dataclass(frozen=True, slots=True)
class ElectromagneticFieldSurvey:
    """
    Retain one bounded axial survey and its selected vector field.

    Axial peaks belong to the summed Cartesian intensity at one sample;
    component peaks remain separate diagnostic curves and are never summed
    across different sample locations.
    """

    selected_propagation: ElectromagneticPropagation
    distances_m: tuple[float, ...]
    peak_intensities: tuple[float, ...]
    component_peak_intensities: Mapping[str, tuple[float, ...]]

    def __post_init__(self) -> None:
        distances = tuple(float(value) for value in self.distances_m)
        peaks = tuple(float(value) for value in self.peak_intensities)
        component_peaks = {
            name: tuple(float(value) for value in values)
            for name, values in self.component_peak_intensities.items()
        }
        if (
            len(distances) < 3
            or len(peaks) != len(distances)
            or any(
                not math.isfinite(distance) or distance < 0 for distance in distances
            )
            or any(right <= left for left, right in zip(distances, distances[1:]))
            or any(not math.isfinite(peak) or peak < 0 for peak in peaks)
            or self.selected_propagation.distance_m not in distances
        ):
            raise ValueError("vector_field_survey_invalid")
        if set(component_peaks) != {"x", "y", "z"} or any(
            len(values) != len(distances)
            or any(not math.isfinite(value) or value < 0 for value in values)
            for values in component_peaks.values()
        ):
            raise ValueError("vector_field_survey_components_invalid")
        object.__setattr__(self, "distances_m", distances)
        object.__setattr__(self, "peak_intensities", peaks)
        object.__setattr__(
            self,
            "component_peak_intensities",
            MappingProxyType(component_peaks),
        )


@dataclass(frozen=True, slots=True)
class _PreparedVectorSpectrum:
    """
    Retain one padded vector spectrum throughout an axial survey.
    """

    electric_x: torch.Tensor
    electric_y: torch.Tensor
    electric_z: torch.Tensor
    magnetic_x: torch.Tensor
    magnetic_y: torch.Tensor
    magnetic_z: torch.Tensor
    wave_number_z: torch.Tensor
    crop: tuple[slice, slice]
    distance_batch_size: int


def observe_vector_angular_spectrum() -> VectorAngularSpectrumRealization:
    """
    Select CUDA when present and Torch CPU only when CUDA is absent.
    """

    if torch.cuda.is_available():
        device = f"cuda:{torch.cuda.current_device()}"
    else:
        device = "cpu"
    return VectorAngularSpectrumRealization(
        device=device,
        working_memory_bytes=int(
            observe_available_device_memory(device).available_bytes * 0.8
        ),
    )


def qualify_vector_angular_spectrum(
    realization: VectorAngularSpectrumRealization | None = None,
) -> VectorAngularSpectrumQualification:
    """
    Qualify one selected device without another device or method fallback.
    """

    selected = realization or observe_vector_angular_spectrum()
    try:
        budget = _execution_budget(selected)
        if budget <= 0:
            raise RuntimeError("vector_field_memory_unavailable")
        oblique = _oblique_plane_wave_errors(selected)
        direct_component_error = _direct_component_error(selected)
    except (OSError, RuntimeError) as error:
        return VectorAngularSpectrumQualification(
            selected,
            math.inf,
            math.inf,
            math.inf,
            math.inf,
            math.inf,
            math.inf,
            False,
            type(error).__name__,
        )
    errors = (*oblique, direct_component_error)
    is_qualified = max(errors) <= _QUALIFICATION_LIMIT
    return VectorAngularSpectrumQualification(
        selected,
        wave_vector_error=oblique[0],
        transversality_error=oblique[1],
        phase_advance_error=oblique[2],
        longitudinal_recovery_error=oblique[3],
        direct_component_error=direct_component_error,
        poynting_error=oblique[4],
        is_qualified=is_qualified,
        reason=(
            None if is_qualified else "vector_field_numerical_qualification_failed"
        ),
    )


def vector_angular_spectrum_binding(
    qualification: VectorAngularSpectrumQualification,
) -> Document:
    """
    Encode one qualified realization for the existing Binding seam.
    """

    if not qualification.is_qualified:
        raise ValueError("vector_field_qualification_required")
    return Document(
        VECTOR_ANGULAR_SPECTRUM_BINDING_SCHEMA,
        {
            "operations": ["propagate_electromagnetic_field"],
            "qualification": qualification.as_mapping(),
            "qualified": True,
            "realization": qualification.realization.as_mapping(),
        },
    )


def restore_vector_angular_spectrum_binding(
    document: Document,
) -> VectorAngularSpectrumRealization:
    """
    Restore the exact realization admitted through one binding document.
    """

    realization = document.values.get("realization")
    qualification = document.values.get("qualification")
    if (
        document.schema_identifier != VECTOR_ANGULAR_SPECTRUM_BINDING_SCHEMA
        or document.values.get("operations") != ["propagate_electromagnetic_field"]
        or document.values.get("qualified") is not True
        or not isinstance(realization, Mapping)
        or not isinstance(qualification, Mapping)
    ):
        raise ValueError("vector_field_binding_invalid")
    try:
        restored = VectorAngularSpectrumQualification.from_mapping(qualification)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("vector_field_binding_invalid") from error
    if not restored.is_qualified or restored.realization.as_mapping() != realization:
        raise ValueError("vector_field_binding_invalid")
    return restored.realization


def propagate_electromagnetic_field(
    field: Field,
    *,
    distance_m: float,
    realization: VectorAngularSpectrumRealization,
) -> ElectromagneticPropagation:
    """
    Propagate one transverse sampled field and recover its coupled components.
    """

    _require_applicable(field, distance_m)
    prepared = _prepare_vector_spectrum(field, realization=realization)
    return _materialize_prepared_vector_spectrum(
        field,
        prepared,
        distance_m=distance_m,
        realization=realization,
    )


def _materialize_prepared_vector_spectrum(
    field: Field,
    prepared: _PreparedVectorSpectrum,
    *,
    distance_m: float,
    realization: VectorAngularSpectrumRealization,
) -> ElectromagneticPropagation:
    """
    Materialize one field and matching power plane without another FFT.
    """

    spectra = {
        "x": prepared.electric_x,
        "y": prepared.electric_y,
        "z": prepared.electric_z,
        "h_x": prepared.magnetic_x,
        "h_y": prepared.magnetic_y,
        "h_z": prepared.magnetic_z,
    }
    initial = {name: torch.fft.ifft2(values) for name, values in spectra.items()}
    transfer = torch.exp(1j * prepared.wave_number_z * distance_m)
    propagated = {
        name: torch.fft.ifft2(values * transfer)
        for name, values in spectra.items()
    }
    input_power = _longitudinal_power(
        initial,
        spacing_m=field.surface.spacing_m,
    )
    output_power = _longitudinal_power(
        propagated,
        spacing_m=field.surface.spacing_m,
    )
    output_surface = PlaneSurface(
        field.surface.position_m + distance_m,
        field.surface.spacing_m,
        field.surface.shape,
    )
    output = Field(
        wavelength_m=field.wavelength_m,
        surface=output_surface,
        frame=field.frame,
        medium=field.medium,
        basis=ComponentBasis.CARTESIAN,
        electric_components=tuple(
            _field_component(name, propagated[name][prepared.crop])
            for name in ("x", "y", "z")
        ),
        source_references=field.source_references,
        incident_reference_power=field.incident_reference_power,
    )
    return ElectromagneticPropagation(
        field=output,
        distance_m=distance_m,
        input_longitudinal_power_w=input_power,
        output_longitudinal_power_w=output_power,
        output_longitudinal_power=LongitudinalPowerPlane(
            output_surface,
            _power_density_samples(propagated, prepared.crop),
        ),
        realization=realization.as_mapping(),
    )


def survey_electromagnetic_field(
    field: Field,
    *,
    distance_range_m: tuple[float, float],
    preferred_distance_m: float,
    realization: VectorAngularSpectrumRealization,
) -> ElectromagneticFieldSurvey:
    """
    Survey, locally refine, and retain one principal vector field.

    The implementation keeps only scalar peak observations during the axial
    search. One complete electric field and Poynting plane are materialized
    after the selected distance is known.
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
        raise ValueError("vector_field_distance_range_invalid")
    coarse_distances = _distance_samples(lower_m, upper_m)
    prepared = _prepare_vector_spectrum(field, realization=realization)
    observations = _observe_electromagnetic_peaks(
        prepared,
        coarse_distances,
    )
    selected_distance = _principal_distance(
        observations,
        preferred_distance_m=preferred_distance_m,
    )
    selected_index = coarse_distances.index(selected_distance)
    if 0 < selected_index < len(coarse_distances) - 1:
        refinement_distances = _distance_samples(
            coarse_distances[selected_index - 1],
            coarse_distances[selected_index + 1],
        )
        missing_distances = tuple(
            distance
            for distance in refinement_distances
            if distance not in observations
        )
        observations.update(
            _observe_electromagnetic_peaks(
                prepared,
                missing_distances,
            )
        )
        selected_distance = _principal_distance(
            observations,
            preferred_distance_m=preferred_distance_m,
        )
    distances = tuple(sorted(observations))
    return ElectromagneticFieldSurvey(
        selected_propagation=_materialize_prepared_vector_spectrum(
            field,
            prepared,
            distance_m=selected_distance,
            realization=realization,
        ),
        distances_m=distances,
        peak_intensities=tuple(observations[distance][0] for distance in distances),
        component_peak_intensities={
            name: tuple(observations[distance][1][name] for distance in distances)
            for name in ("x", "y", "z")
        },
    )


def _distance_samples(lower_m: float, upper_m: float) -> tuple[float, ...]:
    interval = upper_m - lower_m
    return tuple(lower_m + interval * index / 16 for index in range(17))


def _prepare_vector_spectrum(
    field: Field,
    *,
    realization: VectorAngularSpectrumRealization,
) -> _PreparedVectorSpectrum:
    _require_applicable(field, 0.0)
    device = torch.device(realization.device)
    _require_memory(field.surface.shape, realization)
    electric_x = torch.tensor(
        field.electric("x"),
        dtype=torch.complex128,
        device=device,
    )
    electric_y = torch.tensor(
        field.electric("y"),
        dtype=torch.complex128,
        device=device,
    )
    padded_x, crop = _pad(
        electric_x,
        realization.convention.padding_factor,
    )
    padded_y, _ = _pad(
        electric_y,
        realization.convention.padding_factor,
    )
    spectra = _complete_spectra(
        torch.fft.fft2(padded_x),
        torch.fft.fft2(padded_y),
        spacing_m=field.surface.spacing_m,
        wavelength_m=field.wavelength_m,
    )
    wave_number_z = spectra.pop("wave_number_z")
    padded_samples = wave_number_z.numel()
    fixed_bytes = padded_samples * 16 * 8
    bytes_per_distance = padded_samples * 16 * 8
    available_for_distances = max(
        bytes_per_distance,
        _execution_budget(realization) - fixed_bytes,
    )
    return _PreparedVectorSpectrum(
        electric_x=spectra["x"],
        electric_y=spectra["y"],
        electric_z=spectra["z"],
        magnetic_x=spectra["h_x"],
        magnetic_y=spectra["h_y"],
        magnetic_z=spectra["h_z"],
        wave_number_z=wave_number_z,
        crop=crop,
        distance_batch_size=max(
            1,
            available_for_distances // bytes_per_distance,
        ),
    )


def _observe_electromagnetic_peaks(
    prepared: _PreparedVectorSpectrum,
    distances_m: tuple[float, ...],
) -> dict[float, tuple[float, dict[str, float]]]:
    observations: dict[float, tuple[float, dict[str, float]]] = {}
    spectra = {
        "x": prepared.electric_x,
        "y": prepared.electric_y,
        "z": prepared.electric_z,
    }
    for start in range(0, len(distances_m), prepared.distance_batch_size):
        batch = distances_m[start : start + prepared.distance_batch_size]
        distances = torch.tensor(
            batch,
            dtype=torch.float64,
            device=prepared.wave_number_z.device,
        )
        transfer = torch.exp(
            1j * distances[:, None, None] * prepared.wave_number_z[None, :, :]
        )
        total_intensity: torch.Tensor | None = None
        component_peaks: dict[str, torch.Tensor] = {}
        for name, spectrum in spectra.items():
            propagated = torch.fft.ifft2(spectrum[None, :, :] * transfer)
            intensity = torch.abs(
                propagated[:, prepared.crop[0], prepared.crop[1]]
            ).square()
            component_peaks[name] = torch.amax(intensity, dim=(-2, -1))
            total_intensity = (
                intensity if total_intensity is None else total_intensity + intensity
            )
        assert total_intensity is not None
        total_peaks = torch.amax(total_intensity, dim=(-2, -1))
        for index, distance in enumerate(batch):
            observations[distance] = (
                float(total_peaks[index].detach().cpu()),
                {
                    name: float(values[index].detach().cpu())
                    for name, values in component_peaks.items()
                },
            )
    return observations


def _principal_distance(
    observations: Mapping[float, tuple[float, Mapping[str, float]]],
    *,
    preferred_distance_m: float,
) -> float:
    return min(
        observations,
        key=lambda distance: (
            -observations[distance][0],
            abs(distance - preferred_distance_m),
            distance,
        ),
    )


def _propagate_tensors(
    electric_x: torch.Tensor,
    electric_y: torch.Tensor,
    *,
    spacing_m: float,
    wavelength_m: float,
    distance_m: float,
    padding_factor: int,
) -> tuple[
    dict[str, torch.Tensor],
    dict[str, torch.Tensor],
    tuple[slice, slice],
]:
    padded_x, crop = _pad(electric_x, padding_factor)
    padded_y, _ = _pad(electric_y, padding_factor)
    spectra = _complete_spectra(
        torch.fft.fft2(padded_x),
        torch.fft.fft2(padded_y),
        spacing_m=spacing_m,
        wavelength_m=wavelength_m,
    )
    wave_number_z = spectra.pop("wave_number_z")
    initial = {name: torch.fft.ifft2(values) for name, values in spectra.items()}
    transfer = torch.exp(1j * wave_number_z * distance_m)
    propagated = {
        name: torch.fft.ifft2(values * transfer) for name, values in spectra.items()
    }
    return initial, propagated, crop


def _complete_spectra(
    electric_x: torch.Tensor,
    electric_y: torch.Tensor,
    *,
    spacing_m: float,
    wavelength_m: float,
) -> dict[str, torch.Tensor]:
    rows, columns = electric_x.shape
    device = electric_x.device
    transverse_y = (
        2
        * math.pi
        * torch.fft.fftfreq(
            rows,
            d=spacing_m,
            device=device,
            dtype=torch.float64,
        )
    )
    transverse_x = (
        2
        * math.pi
        * torch.fft.fftfreq(
            columns,
            d=spacing_m,
            device=device,
            dtype=torch.float64,
        )
    )
    wave_number_y, wave_number_x = torch.meshgrid(
        transverse_y,
        transverse_x,
        indexing="ij",
    )
    wave_number = 2 * math.pi / wavelength_m
    longitudinal_square = (
        wave_number**2 - wave_number_x.square() - wave_number_y.square()
    )
    is_propagating = longitudinal_square > 0
    wave_number_z = torch.sqrt(torch.clamp(longitudinal_square, min=0))
    electric_x = torch.where(
        is_propagating,
        electric_x,
        torch.zeros_like(electric_x),
    )
    electric_y = torch.where(
        is_propagating,
        electric_y,
        torch.zeros_like(electric_y),
    )
    numerator = wave_number_x * electric_x + wave_number_y * electric_y
    electric_z = torch.where(
        is_propagating,
        -numerator
        / torch.where(
            is_propagating,
            wave_number_z,
            torch.ones_like(wave_number_z),
        ),
        torch.zeros_like(electric_x),
    )
    angular_frequency = 2 * math.pi * _SPEED_OF_LIGHT_M_PER_S / wavelength_m
    magnetic_scale = _VACUUM_PERMEABILITY_H_PER_M * angular_frequency
    magnetic_x = (
        wave_number_y * electric_z - wave_number_z * electric_y
    ) / magnetic_scale
    magnetic_y = (
        wave_number_z * electric_x - wave_number_x * electric_z
    ) / magnetic_scale
    magnetic_z = (
        wave_number_x * electric_y - wave_number_y * electric_x
    ) / magnetic_scale
    return {
        "x": electric_x,
        "y": electric_y,
        "z": electric_z,
        "h_x": magnetic_x,
        "h_y": magnetic_y,
        "h_z": magnetic_z,
        "wave_number_z": wave_number_z,
    }


def _oblique_plane_wave_errors(
    realization: VectorAngularSpectrumRealization,
) -> tuple[float, float, float, float, float]:
    device = torch.device(realization.device)
    size = 16
    wavelength_m = 800e-9
    spacing_m = wavelength_m / 4
    distance_m = wavelength_m * 0.7
    transverse_x_index = 1
    transverse_y_index = 2
    electric_x = torch.zeros(
        (size, size),
        dtype=torch.complex128,
        device=device,
    )
    electric_y = torch.zeros_like(electric_x)
    electric_x[transverse_y_index, transverse_x_index] = 1
    electric_y[transverse_y_index, transverse_x_index] = torch.tensor(
        0.25j,
        dtype=torch.complex128,
        device=device,
    )
    spectra = _complete_spectra(
        electric_x,
        electric_y,
        spacing_m=spacing_m,
        wavelength_m=wavelength_m,
    )
    wave_number_z = spectra["wave_number_z"]
    frequency = torch.fft.fftfreq(
        size,
        d=spacing_m,
        device=device,
        dtype=torch.float64,
    )
    wave_number_x = 2 * math.pi * frequency[transverse_x_index]
    wave_number_y = 2 * math.pi * frequency[transverse_y_index]
    longitudinal = wave_number_z[
        transverse_y_index,
        transverse_x_index,
    ]
    electric = torch.stack(
        (
            spectra["x"][transverse_y_index, transverse_x_index],
            spectra["y"][transverse_y_index, transverse_x_index],
            spectra["z"][transverse_y_index, transverse_x_index],
        )
    )
    wave_vector = torch.stack((wave_number_x, wave_number_y, longitudinal)).to(
        torch.complex128
    )
    transversality = torch.abs(torch.sum(wave_vector * electric))
    scale = torch.linalg.vector_norm(wave_vector) * torch.linalg.vector_norm(electric)
    transversality_error = float((transversality / scale).cpu())
    expected_longitudinal = (
        -(wave_number_x * electric[0] + wave_number_y * electric[1]) / longitudinal
    )
    longitudinal_error = float(
        (
            torch.abs(electric[2] - expected_longitudinal)
            / torch.abs(expected_longitudinal)
        ).cpu()
    )
    initial = {
        name: torch.fft.ifft2(values)
        for name, values in spectra.items()
        if name != "wave_number_z"
    }
    transfer = torch.exp(1j * wave_number_z * distance_m)
    propagated = {
        name: torch.fft.ifft2(values * transfer)
        for name, values in spectra.items()
        if name != "wave_number_z"
    }
    phase_x = propagated["x"][0, 1] / propagated["x"][0, 0]
    phase_y = propagated["x"][1, 0] / propagated["x"][0, 0]
    expected_x = torch.exp(1j * wave_number_x * spacing_m)
    expected_y = torch.exp(1j * wave_number_y * spacing_m)
    wave_vector_error = float(
        torch.maximum(
            torch.abs(phase_x - expected_x),
            torch.abs(phase_y - expected_y),
        ).cpu()
    )
    observed_advance = propagated["x"][0, 0] / initial["x"][0, 0]
    expected_advance = torch.exp(1j * longitudinal * distance_m)
    phase_error = float(torch.abs(observed_advance - expected_advance).cpu())
    input_power = _longitudinal_power(initial, spacing_m=spacing_m)
    output_power = _longitudinal_power(
        propagated,
        spacing_m=spacing_m,
    )
    poynting_error = abs(output_power - input_power) / input_power
    return (
        wave_vector_error,
        transversality_error,
        phase_error,
        longitudinal_error,
        poynting_error,
    )


def _direct_component_error(
    realization: VectorAngularSpectrumRealization,
) -> float:
    device = torch.device(realization.device)
    size = 6
    spacing_m = 200e-9
    wavelength_m = 800e-9
    distance_m = 1.3e-6
    axis = torch.arange(size, dtype=torch.float64, device=device) - (size - 1) / 2
    position_y, position_x = torch.meshgrid(axis, axis, indexing="ij")
    envelope = torch.exp(-(position_x.square() + position_y.square()) / 3)
    electric_x = envelope.to(torch.complex128)
    electric_y = (0.2j * envelope).to(torch.complex128)
    _, propagated, crop = _propagate_tensors(
        electric_x,
        electric_y,
        spacing_m=spacing_m,
        wavelength_m=wavelength_m,
        distance_m=distance_m,
        padding_factor=2,
    )
    padded_x, _ = _pad(electric_x, 2)
    padded_y, _ = _pad(electric_y, 2)
    forward, inverse = _direct_transform_matrices(
        padded_x.shape[0],
        device=device,
    )
    spectrum_x = forward @ padded_x @ forward.T
    spectrum_y = forward @ padded_y @ forward.T
    spectra = _complete_spectra(
        spectrum_x,
        spectrum_y,
        spacing_m=spacing_m,
        wavelength_m=wavelength_m,
    )
    wave_number_z = spectra.pop("wave_number_z")
    transfer = torch.exp(1j * wave_number_z * distance_m)
    errors = []
    for name in ("x", "y", "z"):
        reference = inverse @ (spectra[name] * transfer) @ inverse.T
        reference = reference[crop]
        observed = propagated[name][crop]
        errors.append(
            torch.linalg.vector_norm(observed - reference)
            / torch.linalg.vector_norm(reference)
        )
    return float(torch.max(torch.stack(errors)).cpu())


def _direct_transform_matrices(
    size: int,
    *,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor]:
    index = torch.arange(size, dtype=torch.float64, device=device)
    phase = index[:, None] * index[None, :]
    forward = torch.exp(-2j * math.pi * phase / size).to(torch.complex128)
    inverse = torch.exp(2j * math.pi * phase / size).to(torch.complex128) / size
    return forward, inverse


def _longitudinal_power(
    components: Mapping[str, torch.Tensor],
    *,
    spacing_m: float,
) -> float:
    density = _longitudinal_power_density(components)
    return float((torch.sum(density) * spacing_m**2).detach().cpu())


def _longitudinal_power_density(
    components: Mapping[str, torch.Tensor],
) -> torch.Tensor:
    return 0.5 * torch.real(
        components["x"] * torch.conj(components["h_y"])
        - components["y"] * torch.conj(components["h_x"])
    )


def _power_density_samples(
    components: Mapping[str, torch.Tensor],
    crop: tuple[slice, slice],
) -> torch.Tensor:
    return (
        _longitudinal_power_density(components)[crop]
        .contiguous()
        .detach()
        .cpu()
        .clone()
    )


def _field_component(
    name: str,
    values: torch.Tensor,
) -> FieldComponent:
    samples = values.contiguous().detach().cpu().numpy().copy()
    samples.setflags(write=False)
    return FieldComponent(name, samples)


def _pad(
    values: torch.Tensor,
    factor: int,
) -> tuple[torch.Tensor, tuple[slice, slice]]:
    rows, columns = values.shape
    padded_rows = rows * factor
    padded_columns = columns * factor
    before_rows = (padded_rows - rows) // 2
    before_columns = (padded_columns - columns) // 2
    padded = torch.zeros(
        (padded_rows, padded_columns),
        dtype=torch.complex128,
        device=values.device,
    )
    crop = (
        slice(before_rows, before_rows + rows),
        slice(before_columns, before_columns + columns),
    )
    padded[crop] = values
    return padded, crop


def _require_applicable(field: Field, distance_m: float) -> None:
    if field.basis is not ComponentBasis.TRANSVERSE_LINEAR:
        raise ValueError("vector_field_basis_unsupported")
    if field.magnetic_components:
        raise ValueError("vector_field_input_magnetic_unsupported")
    if field.medium.identity.casefold() not in {"air", "vacuum"}:
        raise ValueError("vector_field_medium_unsupported")
    if field.surface.spacing_m > field.wavelength_m / 2:
        raise ValueError("vector_field_sampling_unsupported")
    if not math.isfinite(distance_m) or distance_m < 0:
        raise ValueError("vector_field_distance_invalid")


def _require_memory(
    shape: tuple[int, int],
    realization: VectorAngularSpectrumRealization,
) -> None:
    padded_samples = shape[0] * shape[1] * realization.convention.padding_factor**2
    required = padded_samples * 16 * 24
    if _execution_budget(realization) < required:
        raise RuntimeError("vector_field_memory_unavailable")


def _execution_budget(
    realization: VectorAngularSpectrumRealization,
) -> int:
    current = int(
        observe_available_device_memory(realization.device).available_bytes * 0.8
    )
    if realization.working_memory_bytes is None:
        return current
    return min(current, realization.working_memory_bytes)


def _is_cuda_device(device: str) -> bool:
    prefix, separator, ordinal = device.partition(":")
    return prefix == "cuda" and separator == ":" and ordinal.isdecimal()
