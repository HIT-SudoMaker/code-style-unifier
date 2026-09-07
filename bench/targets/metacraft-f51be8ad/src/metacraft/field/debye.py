from __future__ import annotations

from dataclasses import dataclass
import math

import torch

from .sample import CoordinateFrame, Medium


@dataclass(frozen=True, slots=True)
class DebyeConvention:
    """
    State the shared Richards--Wolf convention used by every realization.
    """

    pupil_surface: str = "aplanatic reference sphere"
    apodization: str = "square root cosine"
    angular_quadrature: str = "composite midpoint"
    time_dependence: str = "negative angular frequency"
    propagation_exponent: str = "positive spatial phase"
    longitudinal_component_sign: str = "negative"

    def __post_init__(self) -> None:
        """
        Reject a convention outside the single qualified physical method.
        """

        if (
            self.pupil_surface != "aplanatic reference sphere"
            or self.apodization != "square root cosine"
            or self.angular_quadrature != "composite midpoint"
            or self.time_dependence != "negative angular frequency"
            or self.propagation_exponent != "positive spatial phase"
            or self.longitudinal_component_sign != "negative"
        ):
            raise ValueError("debye_convention_unsupported")

    def as_mapping(self) -> dict[str, str]:
        """
        Return the physical convention as stable descriptive values.
        """

        return {
            "angular_quadrature": self.angular_quadrature,
            "apodization": self.apodization,
            "longitudinal_component_sign": (self.longitudinal_component_sign),
            "propagation_exponent": self.propagation_exponent,
            "pupil_surface": self.pupil_surface,
            "time_dependence": self.time_dependence,
        }


@dataclass(frozen=True, slots=True)
class AplanaticSurface:
    """
    Declare one ideal aplanatic reference sphere around its geometric focus.
    """

    focal_length_m: float
    angular_radius_rad: float
    kind: str = "aplanatic reference sphere"

    def __post_init__(self) -> None:
        """
        Require one finite forward reference sphere.
        """

        if not math.isfinite(self.focal_length_m) or self.focal_length_m <= 0:
            raise ValueError("debye_focal_length_invalid")
        if (
            not math.isfinite(self.angular_radius_rad)
            or not 0 < self.angular_radius_rad < math.pi / 2
        ):
            raise ValueError("debye_angular_radius_invalid")
        if self.kind != DebyeConvention().pupil_surface:
            raise ValueError("debye_pupil_surface_unsupported")


@dataclass(frozen=True, slots=True)
class PupilPolarization:
    """
    Declare a normalized Jones vector under one explicit time convention.

    The relative sign of the vertical complex quadrature declares handedness;
    no ambiguous right/left label is inferred at this shared field boundary.
    """

    horizontal_component: complex
    vertical_component: complex
    time_dependence: str = "negative angular frequency"

    def __post_init__(self) -> None:
        """
        Require one finite normalized polarization.
        """

        horizontal = complex(self.horizontal_component)
        vertical = complex(self.vertical_component)
        if not all(
            math.isfinite(value)
            for value in (
                horizontal.real,
                horizontal.imag,
                vertical.real,
                vertical.imag,
            )
        ):
            raise ValueError("debye_polarization_not_finite")
        power = abs(horizontal) ** 2 + abs(vertical) ** 2
        if not math.isclose(power, 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("debye_polarization_not_normalized")
        if self.time_dependence != DebyeConvention().time_dependence:
            raise ValueError("debye_time_convention_unsupported")
        object.__setattr__(self, "horizontal_component", horizontal)
        object.__setattr__(self, "vertical_component", vertical)


@dataclass(frozen=True, slots=True)
class AplanaticPupil:
    """
    Couple one ideal reference sphere to its optical illumination facts.
    """

    surface: AplanaticSurface
    frame: CoordinateFrame
    medium: Medium
    medium_refractive_index: float
    polarization: PupilPolarization
    wavelength_m: float
    apodization: str = "square root cosine"

    def __post_init__(self) -> None:
        """
        Require a complete pupil under the shared Debye convention.
        """

        if (
            not math.isfinite(self.medium_refractive_index)
            or self.medium_refractive_index <= 0
        ):
            raise ValueError("debye_medium_index_invalid")
        if not math.isfinite(self.wavelength_m) or self.wavelength_m <= 0:
            raise ValueError("debye_wavelength_invalid")
        if self.apodization != DebyeConvention().apodization:
            raise ValueError("debye_apodization_unsupported")
        if self.frame != CoordinateFrame():
            raise ValueError("debye_coordinate_frame_unsupported")


@dataclass(frozen=True, slots=True)
class FocalCoordinates:
    """
    Name corresponding Cartesian points relative to the geometric focus.
    """

    horizontal_m: tuple[float, ...]
    vertical_m: tuple[float, ...]
    axial_m: tuple[float, ...]

    def __post_init__(self) -> None:
        """
        Freeze one finite, non-empty coordinate sequence.
        """

        horizontal = tuple(float(value) for value in self.horizontal_m)
        vertical = tuple(float(value) for value in self.vertical_m)
        axial = tuple(float(value) for value in self.axial_m)
        if (
            not horizontal
            or len(horizontal) != len(vertical)
            or len(horizontal) != len(axial)
            or not all(
                math.isfinite(value)
                for values in (horizontal, vertical, axial)
                for value in values
            )
        ):
            raise ValueError("debye_focal_coordinates_invalid")
        object.__setattr__(self, "horizontal_m", horizontal)
        object.__setattr__(self, "vertical_m", vertical)
        object.__setattr__(self, "axial_m", axial)

    @property
    def point_count(self) -> int:
        """
        Return the number of corresponding focal points.
        """

        return len(self.horizontal_m)


@dataclass(frozen=True, slots=True, eq=False)
class DebyeObservation:
    """
    Retain one calculated complex focal-field observation.

    This calculation value is not an admitted ``Field`` and carries no claim
    that arbitrary sampled exit-plane evidence established it.
    """

    coordinates: FocalCoordinates
    horizontal_component: torch.Tensor
    vertical_component: torch.Tensor
    longitudinal_component: torch.Tensor
    realization_identity: str

    def __post_init__(self) -> None:
        """
        Require three finite complex components on one exact device.
        """

        components = self.electric_components
        if (
            not self.realization_identity.strip()
            or any(
                component.dtype != torch.complex128
                or component.ndim != 1
                or component.shape != (self.coordinates.point_count,)
                for component in components
            )
            or len({component.device for component in components}) != 1
            or not all(
                bool(torch.isfinite(component).all().item()) for component in components
            )
        ):
            raise ValueError("debye_observation_invalid")

    @property
    def electric_components(
        self,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Return horizontal, vertical, and longitudinal components in order.
        """

        return (
            self.horizontal_component,
            self.vertical_component,
            self.longitudinal_component,
        )


__all__ = [
    "AplanaticPupil",
    "AplanaticSurface",
    "DebyeConvention",
    "DebyeObservation",
    "FocalCoordinates",
    "PupilPolarization",
]
