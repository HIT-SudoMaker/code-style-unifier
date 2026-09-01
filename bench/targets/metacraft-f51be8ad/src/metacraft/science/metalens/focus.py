from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
from types import MappingProxyType
from typing import TYPE_CHECKING, cast

import numpy
from numpy.typing import NDArray
import torch

from ...authority import Document, Reference
from ...field import (
    ComponentBasis,
    CoordinateFrame,
    FieldComponent,
    Medium,
    PlaneSurface,
)
from ...field.angular_spectrum import FieldPropagation
from ...field.vector_angular_spectrum import LongitudinalPowerPlane

if TYPE_CHECKING:
    from ..study import Finding


FOCAL_REGION_SCHEMA = (
    "metacraft.science.metalens.retained_focal_region"
)
FOCUS_SCHEMA = "metacraft.science.metalens.focus"
FOCUS_SURVEY_SCHEMA = "metacraft.diagnostic.metalens.focus"


@dataclass(frozen=True, slots=True)
class FocalRegion:
    """
    Retain one propagated metalens observation for later evaluation.
    """

    wavelength_m: float
    spacing_m: float
    expected_focus_m: float
    found_focus_m: float
    focus_plane_position_m: float
    observed_components: tuple[str, ...]
    axial_distances_m: tuple[float, ...]
    axial_peak_intensities: tuple[float, ...]
    component_axial_peak_intensities: Mapping[str, tuple[float, ...]]
    frame: CoordinateFrame
    medium: Medium
    basis: ComponentBasis
    electric_components: tuple[FieldComponent, ...]
    source_references: tuple[Reference, ...]
    incident_reference_power: float
    transmitted_aperture_power: Mapping[str, float]
    realization: Mapping[str, object]
    vector_input_power_w: float | None = None
    vector_output_power_w: float | None = None
    longitudinal_power_plane: LongitudinalPowerPlane | None = None
    magnetic_components: tuple[FieldComponent, ...] = ()

    @property
    def aplanatic_axial_offset_m(self) -> float:
        """
        Locate the observed plane relative to the design focus plane.
        """

        source_plane_position_m = (
            self.focus_plane_position_m - self.found_focus_m
        )
        expected_focus_plane_position_m = (
            source_plane_position_m + self.expected_focus_m
        )
        return (
            self.focus_plane_position_m
            - expected_focus_plane_position_m
        )

    def __post_init__(self) -> None:
        """
        Require one ordered axial survey and one complete component plane.
        """

        distances = self.axial_distances_m
        if (
            len(distances) < 3
            or any(
                not math.isfinite(value) or value <= 0
                for value in distances
            )
            or any(
                right <= left
                for left, right in zip(distances, distances[1:])
            )
        ):
            raise ValueError("focal_region_distances_invalid")
        if not math.isfinite(self.spacing_m) or self.spacing_m <= 0:
            raise ValueError("focal_region_spacing_invalid")
        if not math.isfinite(self.wavelength_m) or self.wavelength_m <= 0:
            raise ValueError("focal_region_wavelength_invalid")
        if (
            not math.isfinite(self.expected_focus_m)
            or self.expected_focus_m <= 0
        ):
            raise ValueError("focal_region_expected_focus_invalid")
        if self.found_focus_m not in distances:
            raise ValueError("focal_region_focus_missing")
        if not math.isfinite(self.focus_plane_position_m):
            raise ValueError("focal_region_plane_position_invalid")
        if (
            not self.observed_components
            or len(set(self.observed_components))
            != len(self.observed_components)
            or not set(self.observed_components)
            <= set(self.basis.components)
        ):
            raise ValueError("focal_region_observed_components_invalid")
        if (
            len(self.axial_peak_intensities) != len(distances)
            or any(
                not math.isfinite(value) or value < 0
                for value in self.axial_peak_intensities
            )
        ):
            raise ValueError("focal_region_axial_intensity_invalid")
        expected_names = self.basis.components
        observed_names = tuple(
            item.name for item in self.electric_components
        )
        if observed_names != expected_names:
            raise ValueError("focal_region_components_incomplete")
        magnetic_names = tuple(
            item.name for item in self.magnetic_components
        )
        if magnetic_names not in {(), expected_names}:
            raise ValueError("focal_region_magnetic_components_incomplete")
        shapes = {
            item.values.shape
            for item in (
                *self.electric_components,
                *self.magnetic_components,
            )
        }
        if len(shapes) != 1:
            raise ValueError("focal_region_component_shape_mismatch")
        shape = next(iter(shapes))
        if len(shape) != 2:
            raise ValueError("focal_region_focus_plane_invalid")
        if set(self.component_axial_peak_intensities) != set(
            expected_names
        ):
            raise ValueError("focal_region_component_curve_incomplete")
        if any(
            len(values) != len(distances)
            or any(
                not math.isfinite(value) or value < 0
                for value in values
            )
            for values in self.component_axial_peak_intensities.values()
        ):
            raise ValueError("focal_region_component_curve_invalid")
        if self.transmitted_aperture_power and set(
            self.transmitted_aperture_power
        ) != set(expected_names):
            raise ValueError("focal_region_transmitted_power_incomplete")
        if any(
            not math.isfinite(value) or value < 0
            for value in self.transmitted_aperture_power.values()
        ):
            raise ValueError("focal_region_transmitted_power_invalid")
        vector_power_values = (
            self.vector_input_power_w,
            self.vector_output_power_w,
            self.longitudinal_power_plane,
        )
        has_vector_power = all(value is not None for value in vector_power_values)
        if any(value is not None for value in vector_power_values) != has_vector_power:
            raise ValueError("focal_region_power_meaning_ambiguous")
        if has_vector_power:
            assert self.vector_input_power_w is not None
            assert self.vector_output_power_w is not None
            assert self.longitudinal_power_plane is not None
            expected_surface = PlaneSurface(
                self.focus_plane_position_m,
                self.spacing_m,
                (shape[0], shape[1]),
            )
            if (
                self.transmitted_aperture_power
                or self.basis is not ComponentBasis.CARTESIAN
                or not math.isfinite(self.vector_input_power_w)
                or self.vector_input_power_w <= 0
                or not math.isfinite(self.vector_output_power_w)
                or self.vector_output_power_w < 0
                or self.longitudinal_power_plane.surface != expected_surface
            ):
                raise ValueError("focal_region_vector_power_invalid")
        elif not self.transmitted_aperture_power:
            raise ValueError("focal_region_power_meaning_ambiguous")
        if (
            not math.isfinite(self.incident_reference_power)
            or self.incident_reference_power <= 0
        ):
            raise ValueError("focal_region_incident_power_invalid")
        if not self.source_references:
            raise ValueError("focal_region_sources_empty")
        object.__setattr__(
            self,
            "component_axial_peak_intensities",
            MappingProxyType(
                {
                    name: tuple(values)
                    for name, values in (
                        self.component_axial_peak_intensities.items()
                    )
                }
            ),
        )
        object.__setattr__(
            self,
            "transmitted_aperture_power",
            MappingProxyType(dict(self.transmitted_aperture_power)),
        )
        object.__setattr__(
            self,
            "realization",
            MappingProxyType(dict(self.realization)),
        )

    @property
    def component_names(self) -> tuple[str, ...]:
        """
        Return propagated electric components in basis order.
        """

        return tuple(
            component.name for component in self.electric_components
        )

    @property
    def shape(self) -> tuple[int, int]:
        """
        Return the common transverse sample shape.
        """

        values = self.electric_components[0].values
        return (values.shape[0], values.shape[1])

    def electric(self, name: str) -> NDArray[numpy.complex128]:
        """
        Return one immutable propagated electric component.
        """

        return _component(self.electric_components, name)

    def magnetic(self, name: str) -> NDArray[numpy.complex128]:
        """
        Return one immutable propagated magnetic component.
        """

        return _component(self.magnetic_components, name)


def observe_focal_region(
    propagation: FieldPropagation,
    *,
    field_reference: Reference,
    expected_focus_m: float,
) -> FocalRegion:
    """
    Validate and assemble one completed metalens focal-region observation.
    """

    if not math.isfinite(expected_focus_m) or expected_focus_m <= 0:
        raise ValueError("focal_region_expected_focus_invalid")
    observation = propagation.observation
    plane = propagation.principal_field
    return FocalRegion(
        wavelength_m=plane.wavelength_m,
        spacing_m=plane.surface.spacing_m,
        expected_focus_m=expected_focus_m,
        found_focus_m=propagation.principal_distance_m,
        focus_plane_position_m=plane.surface.position_m,
        observed_components=observation.observed_components,
        axial_distances_m=observation.distances_m,
        axial_peak_intensities=observation.peak_intensities,
        component_axial_peak_intensities=(
            observation.component_peak_intensities
        ),
        frame=plane.frame,
        medium=plane.medium,
        basis=plane.basis,
        electric_components=plane.electric_components,
        magnetic_components=plane.magnetic_components,
        source_references=(field_reference,),
        incident_reference_power=plane.incident_reference_power,
        transmitted_aperture_power=propagation.input_component_power,
        realization=propagation.realization,
    )


@dataclass(frozen=True, slots=True)
class HalfMaximum:
    """
    Record one bracketed half-maximum span.
    """

    lower_m: float | None
    upper_m: float | None
    width_m: float | None
    is_bracketed: bool

    def as_mapping(self) -> dict[str, object]:
        """
        Return one evidence-safe span.
        """

        return {
            "bracketed": self.is_bracketed,
            "lower_m": _number(self.lower_m),
            "upper_m": _number(self.upper_m),
            "width_m": _number(self.width_m),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> HalfMaximum:
        """
        Restore one exact half-maximum span.
        """

        return cls(
            lower_m=_optional_number(value["lower_m"]),
            upper_m=_optional_number(value["upper_m"]),
            width_m=_optional_number(value["width_m"]),
            is_bracketed=bool(value["bracketed"]),
        )


@dataclass(frozen=True, slots=True)
class FocusConvergence:
    """
    Record the realized axial sampling around one selected focus.
    """

    sample_count: int
    smallest_step_m: float
    is_locally_refined: bool

    def __post_init__(self) -> None:
        """
        Reject sampling that cannot describe an axial survey.
        """

        if self.sample_count < 3:
            raise ValueError("focus_convergence_sample_count_invalid")
        if (
            not math.isfinite(self.smallest_step_m)
            or self.smallest_step_m <= 0
        ):
            raise ValueError("focus_convergence_step_invalid")

    def as_mapping(self) -> dict[str, object]:
        """
        Return evidence-safe convergence facts.
        """

        return {
            "locally_refined": self.is_locally_refined,
            "sample_count": self.sample_count,
            "smallest_step_m": _number(self.smallest_step_m),
        }

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object],
    ) -> FocusConvergence:
        """
        Restore one exact convergence record.
        """

        return cls(
            sample_count=int(str(value["sample_count"])),
            smallest_step_m=float(str(value["smallest_step_m"])),
            is_locally_refined=bool(value["locally_refined"]),
        )


@dataclass(frozen=True, slots=True)
class Leakage:
    """
    Report retained-channel leakage without useful-focus language.
    """

    channel: str
    role: str
    observed_distance_m: float
    transmitted_fraction: float
    peak_intensity: float
    integrated_intensity: float
    axial_distances_m: tuple[float, ...]
    axial_peak_intensities: tuple[float, ...]

    def __post_init__(self) -> None:
        """
        Require one coherent retained-channel observation.
        """

        if self.channel != "retained" or self.role != "leakage":
            raise ValueError("leakage_channel_invalid")
        values = (
            self.observed_distance_m,
            self.transmitted_fraction,
            self.peak_intensity,
            self.integrated_intensity,
        )
        if not all(
            math.isfinite(value) and value >= 0 for value in values
        ):
            raise ValueError("leakage_value_invalid")
        if (
            not self.axial_distances_m
            or len(self.axial_distances_m)
            != len(self.axial_peak_intensities)
            or any(
                not math.isfinite(distance) or distance <= 0
                for distance in self.axial_distances_m
            )
            or any(
                not math.isfinite(peak) or peak < 0
                for peak in self.axial_peak_intensities
            )
            or any(
                right <= left
                for left, right in zip(
                    self.axial_distances_m,
                    self.axial_distances_m[1:],
                )
            )
            or self.observed_distance_m not in self.axial_distances_m
        ):
            raise ValueError("leakage_axial_scan_invalid")

    def as_mapping(self) -> dict[str, object]:
        """
        Return retained-channel evidence without a focus claim.
        """

        return {
            "axial_scan": [
                {
                    "distance_m": _number(distance),
                    "peak_intensity": _number(peak),
                }
                for distance, peak in zip(
                    self.axial_distances_m,
                    self.axial_peak_intensities,
                    strict=True,
                )
            ],
            "channel": self.channel,
            "integrated_intensity": _number(
                self.integrated_intensity
            ),
            "observed_distance_m": _number(
                self.observed_distance_m
            ),
            "peak_intensity": _number(self.peak_intensity),
            "role": self.role,
            "transmitted_fraction": _number(
                self.transmitted_fraction
            ),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> Leakage:
        """
        Restore one exact retained-channel observation.
        """

        scan = _scan(value["axial_scan"])
        return cls(
            channel=str(value["channel"]),
            role=str(value["role"]),
            observed_distance_m=float(
                str(value["observed_distance_m"])
            ),
            transmitted_fraction=float(
                str(value["transmitted_fraction"])
            ),
            peak_intensity=float(str(value["peak_intensity"])),
            integrated_intensity=float(
                str(value["integrated_intensity"])
            ),
            axial_distances_m=tuple(item[0] for item in scan),
            axial_peak_intensities=tuple(item[1] for item in scan),
        )


@dataclass(frozen=True, slots=True)
class FocusSurvey:
    """
    Preserve one exact focal evaluation, including incomplete brackets.
    """

    expected_focus_m: float
    found_focus_m: float
    focal_shift_m: float
    x_half_maximum: HalfMaximum
    y_half_maximum: HalfMaximum
    depth_of_focus: HalfMaximum
    transmitted_fraction: float
    focused_fraction: float
    focus_efficiency: float
    peak_intensity: float
    airy_radius_m: float
    is_focus_bracketed: bool
    observed_components: tuple[str, ...]
    convergence: FocusConvergence
    axial_distances_m: tuple[float, ...]
    axial_peak_intensities: tuple[float, ...]
    leakage: Leakage | None = None

    def __post_init__(self) -> None:
        """
        Require closed component and convergence facts.
        """

        if (
            not self.observed_components
            or len(set(self.observed_components))
            != len(self.observed_components)
        ):
            raise ValueError("focus_components_invalid")
        if (
            len(self.axial_distances_m)
            != len(self.axial_peak_intensities)
            or len(self.axial_distances_m)
            != self.convergence.sample_count
        ):
            raise ValueError("focus_convergence_mismatch")

    @property
    def is_complete(self) -> bool:
        """
        Report whether every required focus measure is bracketed.
        """

        return (
            self.is_focus_bracketed
            and self.x_half_maximum.is_bracketed
            and self.y_half_maximum.is_bracketed
            and self.depth_of_focus.is_bracketed
        )

    @property
    def status(self) -> str:
        """
        Name this record as a diagnostic survey.
        """

        return "complete" if self.is_complete else "incomplete"

    def as_mapping(self) -> dict[str, object]:
        """
        Return the exact focal evaluation as evidence values.
        """

        values: dict[str, object] = {
            "airy_radius_m": _number(self.airy_radius_m),
            "axial_scan": [
                {
                    "distance_m": _number(distance),
                    "peak_intensity": _number(peak),
                }
                for distance, peak in zip(
                    self.axial_distances_m,
                    self.axial_peak_intensities,
                    strict=True,
                )
            ],
            "complete": self.is_complete,
            "convergence": self.convergence.as_mapping(),
            "depth_of_focus": self.depth_of_focus.as_mapping(),
            "expected_focus_m": _number(self.expected_focus_m),
            "focal_shift_m": _number(self.focal_shift_m),
            "focus_bracketed": self.is_focus_bracketed,
            "focus_efficiency": _number(self.focus_efficiency),
            "focused_fraction": _number(self.focused_fraction),
            "found_focus_m": _number(self.found_focus_m),
            "observed_components": list(self.observed_components),
            "peak_intensity": _number(self.peak_intensity),
            "status": self.status,
            "transmitted_fraction": _number(
                self.transmitted_fraction
            ),
            "x_half_maximum": self.x_half_maximum.as_mapping(),
            "y_half_maximum": self.y_half_maximum.as_mapping(),
        }
        if self.leakage is not None:
            values["leakage"] = self.leakage.as_mapping()
        return values

    def finding(
        self,
        record_reference: Reference,
        *,
        claim: str = "focus",
    ) -> Finding:
        """
        Bind an incomplete survey to one typed diagnostic Finding.
        """

        if self.is_complete:
            raise ValueError("focus_survey_complete")
        from ..study import Finding, FindingKind

        return Finding(
            claim=claim,
            kind=FindingKind.INCOMPLETE,
            needs=("focus_incomplete",),
            record_references=(record_reference,),
        )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object],
    ) -> FocusSurvey:
        """
        Restore one focal evaluation without numerical work.
        """

        scan = _scan(value["axial_scan"])
        leakage = value.get("leakage")
        return cls(
            expected_focus_m=float(str(value["expected_focus_m"])),
            found_focus_m=float(str(value["found_focus_m"])),
            focal_shift_m=float(str(value["focal_shift_m"])),
            x_half_maximum=HalfMaximum.from_mapping(
                _mapping(value["x_half_maximum"])
            ),
            y_half_maximum=HalfMaximum.from_mapping(
                _mapping(value["y_half_maximum"])
            ),
            depth_of_focus=HalfMaximum.from_mapping(
                _mapping(value["depth_of_focus"])
            ),
            transmitted_fraction=float(
                str(value["transmitted_fraction"])
            ),
            focused_fraction=float(str(value["focused_fraction"])),
            focus_efficiency=float(str(value["focus_efficiency"])),
            peak_intensity=float(str(value["peak_intensity"])),
            airy_radius_m=float(str(value["airy_radius_m"])),
            is_focus_bracketed=bool(value["focus_bracketed"]),
            observed_components=tuple(
                str(item)
                for item in _sequence(value["observed_components"])
            ),
            convergence=FocusConvergence.from_mapping(
                _mapping(value["convergence"])
            ),
            axial_distances_m=tuple(item[0] for item in scan),
            axial_peak_intensities=tuple(item[1] for item in scan),
            leakage=(
                None
                if leakage is None
                else Leakage.from_mapping(_mapping(leakage))
            ),
        )


@dataclass(frozen=True, slots=True)
class Focus(FocusSurvey):
    """
    Seal one fully bracketed metalens focus.
    """

    def __post_init__(self) -> None:
        """
        Refuse to present an incomplete survey as Focus.
        """

        super(Focus, self).__post_init__()
        if not self.is_complete:
            raise ValueError("focus_incomplete")


def evaluate_focus(
    focal_region: FocalRegion,
    *,
    numerical_aperture: float,
    leakage_component: str | None = None,
) -> Focus | FocusSurvey:
    """
    Evaluate one low-NA focal observation without propagating again.
    """

    if not 0 < numerical_aperture <= 0.5:
        raise ValueError("low_na_required")
    if set(focal_region.transmitted_aperture_power) != set(
        focal_region.component_names
    ):
        raise ValueError("focal_region_transmitted_power_incomplete")
    return _evaluate_focus(
        focal_region,
        numerical_aperture=numerical_aperture,
        leakage_component=leakage_component,
        incident_power=focal_region.incident_reference_power,
        transmitted_power=sum(
            focal_region.transmitted_aperture_power[name]
            for name in focal_region.observed_components
        ),
        focused_power_density=None,
    )


def evaluate_vector_focus(
    focal_region: FocalRegion,
    *,
    numerical_aperture: float,
    leakage_component: str | None = None,
) -> Focus | FocusSurvey:
    """
    Evaluate one high-NA focal observation with explicit Poynting power.

    The focal shape is read from the admitted vector field. Transmission and
    concentration use the Poynting observation returned by the same qualified
    vector propagation rather than caller-supplied power.
    """

    if not 0.5 < numerical_aperture < 1:
        raise ValueError("high_na_required")
    input_power = focal_region.vector_input_power_w
    output_power = focal_region.vector_output_power_w
    power_plane = focal_region.longitudinal_power_plane
    if input_power is None or output_power is None or power_plane is None:
        raise ValueError("vector_focus_power_invalid")
    expected = focal_region.expected_focus_m
    if (
        focal_region.axial_distances_m[0] > 0.8 * expected
        or focal_region.axial_distances_m[-1] < 1.2 * expected
    ):
        raise ValueError("vector_focus_span_incomplete")
    return _evaluate_focus(
        focal_region,
        numerical_aperture=numerical_aperture,
        leakage_component=leakage_component,
        incident_power=input_power,
        transmitted_power=output_power,
        focused_power_density=power_plane.power_density_w_per_m2,
    )


def _evaluate_focus(
    focal_region: FocalRegion,
    *,
    numerical_aperture: float,
    leakage_component: str | None,
    incident_power: float,
    transmitted_power: float,
    focused_power_density: torch.Tensor | None = None,
) -> Focus | FocusSurvey:
    """
    Measure one focal field after its applicability and power are established.
    """

    names = focal_region.observed_components
    if leakage_component is not None and (
        leakage_component not in focal_region.component_names
        or leakage_component in names
    ):
        raise ValueError("leakage_component_invalid")
    device = str(focal_region.realization.get("device", "cpu"))
    component_values = tuple(
        torch.tensor(
            focal_region.electric(name),
            dtype=torch.complex128,
            device=device,
        )
        for name in names
    )
    intensity = torch.stack(
        tuple(torch.abs(values) ** 2 for values in component_values)
    ).sum(dim=0)
    axial_distances = torch.tensor(
        focal_region.axial_distances_m,
        dtype=torch.float64,
        device=device,
    )
    axial_peaks = torch.tensor(
        focal_region.axial_peak_intensities,
        dtype=torch.float64,
        device=device,
    )
    focus_index = focal_region.axial_distances_m.index(
        focal_region.found_focus_m
    )
    found_focus = focal_region.found_focus_m
    flat_peak = int(torch.argmax(intensity).item())
    peak_row = flat_peak // intensity.shape[1]
    peak_column = flat_peak % intensity.shape[1]
    peak = float(intensity[peak_row, peak_column].item())
    x_axis = (
        torch.arange(
            intensity.shape[1],
            dtype=torch.float64,
            device=device,
        )
        - peak_column
    ) * focal_region.spacing_m
    y_axis = (
        torch.arange(
            intensity.shape[0],
            dtype=torch.float64,
            device=device,
        )
        - peak_row
    ) * focal_region.spacing_m
    x_width = _half_maximum(
        x_axis,
        intensity[peak_row, :],
        peak_column,
    )
    y_width = _half_maximum(
        y_axis,
        intensity[:, peak_column],
        peak_row,
    )
    depth = _half_maximum(axial_distances, axial_peaks, focus_index)
    edge_peak = float(
        torch.maximum(axial_peaks[0], axial_peaks[-1]).item()
    )
    focused_peak = float(axial_peaks[focus_index].item())
    peak_contrast = (focused_peak - edge_peak) / max(
        focused_peak,
        torch.finfo(torch.float64).tiny,
    )
    is_focus_bracketed = bool(
        0 < focus_index < axial_distances.numel() - 1
        and peak_contrast > 1e-12
    )
    airy_radius = (
        0.61 * focal_region.wavelength_m / numerical_aperture
    )
    rows, columns = torch.meshgrid(
        torch.arange(
            intensity.shape[0],
            dtype=torch.float64,
            device=device,
        ),
        torch.arange(
            intensity.shape[1],
            dtype=torch.float64,
            device=device,
        ),
        indexing="ij",
    )
    is_in_focal_bucket = torch.hypot(
        (rows - peak_row) * focal_region.spacing_m,
        (columns - peak_column) * focal_region.spacing_m,
    ) <= airy_radius
    focused_power = float(
        torch.sum(intensity[is_in_focal_bucket]).item()
    )
    if focused_power_density is not None:
        density = focused_power_density.to(
            device=device,
            dtype=torch.float64,
        )
        if density.shape != intensity.shape:
            raise ValueError("vector_focus_power_shape_invalid")
        focused_power = float(
            (
                torch.sum(density[is_in_focal_bucket])
                * focal_region.spacing_m**2
            ).item()
        )
        if focused_power < 0:
            raise ValueError("vector_focus_power_invalid")
    transmitted_fraction = transmitted_power / incident_power
    focused_fraction = (
        0.0
        if transmitted_power == 0
        else focused_power / transmitted_power
    )
    focus_efficiency = focused_power / incident_power
    leakage = (
        None
        if leakage_component is None
        else _evaluate_leakage(
            focal_region,
            component=leakage_component,
            observed_distance_m=found_focus,
            device=device,
        )
    )
    values: dict[str, object] = {
        "expected_focus_m": focal_region.expected_focus_m,
        "found_focus_m": found_focus,
        "focal_shift_m": (
            found_focus - focal_region.expected_focus_m
        ),
        "x_half_maximum": x_width,
        "y_half_maximum": y_width,
        "depth_of_focus": depth,
        "transmitted_fraction": transmitted_fraction,
        "focused_fraction": focused_fraction,
        "focus_efficiency": focus_efficiency,
        "peak_intensity": peak,
        "airy_radius_m": airy_radius,
        "is_focus_bracketed": is_focus_bracketed,
        "observed_components": names,
        "convergence": FocusConvergence(
            sample_count=len(axial_distances),
            smallest_step_m=float(
                torch.min(torch.diff(axial_distances)).item()
            ),
            is_locally_refined=len(axial_distances) > 17,
        ),
        "axial_distances_m": tuple(
            float(value) for value in axial_distances.cpu().tolist()
        ),
        "axial_peak_intensities": tuple(
            float(value) for value in axial_peaks.cpu().tolist()
        ),
        "leakage": leakage,
    }
    survey = FocusSurvey(**values)  # type: ignore[arg-type]
    if survey.is_complete:
        return Focus(**values)  # type: ignore[arg-type]
    return survey


def focus_document(
    *,
    focal_region_reference: Reference,
    focus: Focus,
) -> Document:
    """
    Encode one complete Focus under its exact focal observation.
    """

    require_complete_focus(focus)
    return Document(
        FOCUS_SCHEMA,
        {
            "focal_region": focal_region_reference.as_mapping(),
            "focus": focus.as_mapping(),
        },
    )


def restore_focus(document: Document) -> Focus:
    """
    Restore admitted Focus without invoking numerical work.
    """

    if document.schema_identifier != FOCUS_SCHEMA:
        raise ValueError("focus_evidence_mismatch")
    values = document.values.get("focus")
    if not isinstance(values, Mapping):
        raise ValueError("focus_evidence_mismatch")
    try:
        return cast(Focus, Focus.from_mapping(values))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("focus_evidence_mismatch") from error


def require_complete_focus(focus: Focus) -> None:
    """
    Keep conclusions explicit about requiring complete Focus.
    """

    if not isinstance(focus, Focus):
        raise ValueError("focus_incomplete")


def _evaluate_leakage(
    focal_region: FocalRegion,
    *,
    component: str,
    observed_distance_m: float,
    device: str,
) -> Leakage:
    values = torch.tensor(
        focal_region.electric(component),
        dtype=torch.complex128,
        device=device,
    )
    intensity = torch.abs(values) ** 2
    transmitted_power = focal_region.transmitted_aperture_power[
        component
    ]
    return Leakage(
        channel="retained",
        role="leakage",
        observed_distance_m=observed_distance_m,
        transmitted_fraction=(
            transmitted_power
            / focal_region.incident_reference_power
        ),
        peak_intensity=float(torch.max(intensity).item()),
        integrated_intensity=float(torch.sum(intensity).item()),
        axial_distances_m=focal_region.axial_distances_m,
        axial_peak_intensities=(
            focal_region.component_axial_peak_intensities[component]
        ),
    )


def _half_maximum(
    positions: torch.Tensor,
    values: torch.Tensor,
    peak_index: int,
) -> HalfMaximum:
    half = float(values[peak_index].item()) / 2
    left = peak_index
    while left > 0 and float(values[left].item()) >= half:
        left -= 1
    right = peak_index
    while (
        right < len(values) - 1
        and float(values[right].item()) >= half
    ):
        right += 1
    if left == 0 and float(values[left].item()) >= half:
        return HalfMaximum(None, None, None, False)
    if (
        right == len(values) - 1
        and float(values[right].item()) >= half
    ):
        return HalfMaximum(None, None, None, False)
    lower = _crossing(
        float(positions[left].item()),
        float(values[left].item()),
        float(positions[left + 1].item()),
        float(values[left + 1].item()),
        half,
    )
    upper = _crossing(
        float(positions[right - 1].item()),
        float(values[right - 1].item()),
        float(positions[right].item()),
        float(values[right].item()),
        half,
    )
    return HalfMaximum(
        lower_m=lower,
        upper_m=upper,
        width_m=upper - lower,
        is_bracketed=True,
    )


def _crossing(
    left_position: float,
    left_value: float,
    right_position: float,
    right_value: float,
    target: float,
) -> float:
    if right_value == left_value:
        return (left_position + right_position) / 2
    ratio = (target - left_value) / (right_value - left_value)
    return left_position + ratio * (
        right_position - left_position
    )


def _component(
    components: tuple[FieldComponent, ...],
    name: str,
) -> NDArray[numpy.complex128]:
    matches = tuple(
        item.values for item in components if item.name == name
    )
    if len(matches) != 1:
        raise KeyError(name)
    return matches[0]


def _scan(value: object) -> tuple[tuple[float, float], ...]:
    items = _sequence(value)
    result = []
    for item in items:
        values = _mapping(item)
        result.append(
            (
                float(str(values["distance_m"])),
                float(str(values["peak_intensity"])),
            )
        )
    return tuple(result)


def _number(value: float | None) -> str | None:
    return None if value is None else format(value, ".17g")


def _optional_number(value: object) -> float | None:
    return None if value is None else float(str(value))


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("focus_mapping_invalid")
    return value


def _sequence(value: object) -> list[object]:
    if not isinstance(value, list):
        raise ValueError("focus_sequence_invalid")
    return value
