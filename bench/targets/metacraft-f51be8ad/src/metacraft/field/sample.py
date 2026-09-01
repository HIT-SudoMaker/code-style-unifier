from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

import numpy
from numpy.typing import NDArray

from ..authority import Reference


class ComponentBasis(str, Enum):
    """
    Names the closed transverse bases supported by current field methods.
    """

    TRANSVERSE_LINEAR = "transverse linear"
    CIRCULAR = "circular"
    CARTESIAN = "cartesian"

    @property
    def components(self) -> tuple[str, ...]:
        """
        Return every required electric component in canonical order.
        """

        if self is ComponentBasis.TRANSVERSE_LINEAR:
            return ("x", "y")
        if self is ComponentBasis.CIRCULAR:
            return ("right", "left")
        return ("x", "y", "z")


@dataclass(frozen=True, slots=True)
class PlaneSurface:
    """
    Locates one regularly sampled plane normal to propagation.
    """

    position_m: float
    spacing_m: float
    shape: tuple[int, int]

    def __post_init__(self) -> None:
        """
        Reject coordinates that cannot describe a sampled plane.
        """

        if not math.isfinite(self.position_m):
            raise ValueError("surface_position_invalid")
        if not math.isfinite(self.spacing_m) or self.spacing_m <= 0:
            raise ValueError("surface_spacing_invalid")
        if len(self.shape) != 2 or min(self.shape) < 2:
            raise ValueError("surface_shape_invalid")


@dataclass(frozen=True, slots=True)
class CoordinateFrame:
    """
    States how samples and propagation axes are interpreted.
    """

    sample_order: tuple[str, str] = ("y", "x")
    normal_axis: str = "z"
    propagation_direction: str = "positive"

    def __post_init__(self) -> None:
        """
        Keep the current transverse frame explicit and closed.
        """

        if self.sample_order != ("y", "x"):
            raise ValueError("frame_sample_order_unsupported")
        if self.normal_axis != "z":
            raise ValueError("frame_normal_axis_unsupported")
        if self.propagation_direction != "positive":
            raise ValueError("frame_propagation_direction_unsupported")


@dataclass(frozen=True, slots=True)
class Medium:
    """
    Names one locally uniform propagation medium.
    """

    identity: str

    def __post_init__(self) -> None:
        """
        Require a named propagation medium.
        """

        if not self.identity.strip():
            raise ValueError("medium_identity_empty")


@dataclass(frozen=True, slots=True)
class FieldComponent:
    """
    Couples one physical component name to immutable complex samples.
    """

    name: str
    values: NDArray[numpy.complex128]

    def __post_init__(self) -> None:
        """
        Freeze one finite two-dimensional component array.
        """

        values = _samples(self.values, dimensions=2)
        object.__setattr__(self, "values", values)


@dataclass(frozen=True, slots=True)
class Field:
    """
    Carries one single-wavelength electromagnetic fact.
    """

    wavelength_m: float
    surface: PlaneSurface
    frame: CoordinateFrame
    medium: Medium
    basis: ComponentBasis
    electric_components: tuple[FieldComponent, ...]
    source_references: tuple[Reference, ...]
    incident_reference_power: float
    magnetic_components: tuple[FieldComponent, ...] = ()

    def __post_init__(self) -> None:
        """
        Enforce one complete, immutable component basis.
        """

        if not math.isfinite(self.wavelength_m) or self.wavelength_m <= 0:
            raise ValueError("field_wavelength_invalid")
        _validate_components(
            self.electric_components,
            basis=self.basis,
            shape=self.surface.shape,
            kind="electric",
            is_present=True,
        )
        _validate_components(
            self.magnetic_components,
            basis=self.basis,
            shape=self.surface.shape,
            kind="magnetic",
            is_present=bool(self.magnetic_components),
        )
        if not self.source_references:
            raise ValueError("field_sources_empty")
        if (
            not math.isfinite(self.incident_reference_power)
            or self.incident_reference_power <= 0
        ):
            raise ValueError("field_incident_reference_power_invalid")
        if len(set(self.source_references)) != len(self.source_references):
            raise ValueError("field_source_duplicate")

    @property
    def component_names(self) -> tuple[str, ...]:
        """
        Return electric component names in basis order.
        """

        return tuple(component.name for component in self.electric_components)

    def electric(self, name: str) -> NDArray[numpy.complex128]:
        """
        Return one immutable electric component by its physical name.
        """

        return _component(self.electric_components, name)

    def magnetic(self, name: str) -> NDArray[numpy.complex128]:
        """
        Return one immutable magnetic component by its physical name.
        """

        return _component(self.magnetic_components, name)


def _samples(
    values: NDArray[numpy.complexfloating],
    *,
    dimensions: int,
) -> NDArray[numpy.complex128]:
    if not isinstance(values, numpy.ndarray):
        raise ValueError("field_component_array_required")
    if values.flags.writeable:
        raise ValueError("field_component_mutable")
    if values.dtype != numpy.dtype("<c16"):
        raise ValueError("field_component_dtype_invalid")
    if not values.flags.c_contiguous:
        raise ValueError("field_component_order_invalid")
    if values.ndim != dimensions or min(values.shape) < 2:
        raise ValueError("field_component_shape_invalid")
    if not numpy.isfinite(values).all():
        raise ValueError("field_component_not_finite")
    samples = numpy.array(values, dtype="<c16", order="C", copy=True)
    samples.setflags(write=False)
    return samples


def _validate_components(
    components: tuple[FieldComponent, ...],
    *,
    basis: ComponentBasis,
    shape: tuple[int, int],
    kind: str,
    is_present: bool,
) -> None:
    names = tuple(component.name for component in components)
    if is_present and names != basis.components:
        raise ValueError(f"{kind}_components_incomplete")
    if not is_present and components:
        raise ValueError(f"{kind}_components_incomplete")
    if any(component.values.shape != shape for component in components):
        raise ValueError(f"{kind}_component_shape_mismatch")


def _component(
    components: tuple[FieldComponent, ...],
    name: str,
) -> NDArray[numpy.complex128]:
    matches = tuple(item.values for item in components if item.name == name)
    if len(matches) != 1:
        raise KeyError(name)
    return matches[0]
