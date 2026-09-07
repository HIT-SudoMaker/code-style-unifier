from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ....science.periodic_response import (
    CircularCrossSection,
    EllipticalCrossSection,
    PeriodicCrossSection,
    PeriodicWork,
    RectangularCrossSection,
    SquareCrossSection,
    periodic_cell_mapping,
)

from ..session import Session, _GratingResponsePlanes
from ..time_budget import PeriodicTimeBudget, plan_periodic_time_budget


@dataclass(frozen=True, slots=True)
class _PeriodicTemplate:
    """
    Own the fixed numerical choices of the periodic Lumerical template.
    """

    minimum_substrate_height_nm: int = 2_000
    placement_step_nm: int = 100
    reference_plane_offset_nm: int = 100
    mesh_accuracy: int = 4
    qualification_refractive_index_guard: Decimal = Decimal("4")


_PERIODIC_TEMPLATE = _PeriodicTemplate()


@dataclass(frozen=True, slots=True)
class _PeriodicResponseLayout:
    """
    Declare one periodic response entirely in world z coordinates.

    The substrate/meta-atom interface is always ``z = 0``. The Lumerical
    analysis-group container and its relative child coordinates are derived
    later and never become part of this value.
    """

    wavelength_nm: int
    period_nm: int
    substrate_height_nm: int
    substrate_interface_z_nm: int
    atom_lower_z_nm: int
    atom_upper_z_nm: int
    solver_lower_z_nm: int
    source_plane_z_nm: int
    reflection_plane_z_nm: int
    transmission_plane_z_nm: int
    solver_upper_z_nm: int
    reference_plane_offset_nm: int

    def __post_init__(self) -> None:
        """
        Reject layouts that weaken the declared interface or clearances.
        """

        values = self.as_mapping()
        if any(type(value) is not int for value in values.values()):
            raise TypeError("periodic_response_layout_integer_required")
        if self.wavelength_nm <= 0 or self.period_nm <= 0:
            raise ValueError("periodic_response_layout_scale_invalid")
        if self.substrate_height_nm <= 0 or self.atom_upper_z_nm <= 0:
            raise ValueError("periodic_response_layout_structure_invalid")
        if self.substrate_interface_z_nm != 0 or self.atom_lower_z_nm != 0:
            raise ValueError("periodic_response_interface_mismatch")
        if not (
            -self.substrate_height_nm
            <= self.solver_lower_z_nm
            < self.source_plane_z_nm
            < self.reflection_plane_z_nm
            < self.substrate_interface_z_nm
            < self.atom_upper_z_nm
            < self.transmission_plane_z_nm
            < self.solver_upper_z_nm
        ):
            raise ValueError("periodic_response_plane_order_invalid")
        if (
            self.source_plane_z_nm - self.solver_lower_z_nm
            != self.reference_plane_offset_nm
            or self.reflection_plane_z_nm - self.source_plane_z_nm
            != self.reference_plane_offset_nm
            or self.solver_upper_z_nm - self.transmission_plane_z_nm
            != self.reference_plane_offset_nm
        ):
            raise ValueError("periodic_response_plane_offset_mismatch")
        rounded_coordinates = (
            self.substrate_height_nm,
            self.solver_lower_z_nm,
            self.source_plane_z_nm,
            self.reflection_plane_z_nm,
            self.transmission_plane_z_nm,
            self.solver_upper_z_nm,
        )
        if any(
            coordinate % _PERIODIC_TEMPLATE.placement_step_nm
            for coordinate in rounded_coordinates
        ):
            raise ValueError("periodic_response_layout_not_outward_rounded")

    def as_mapping(self) -> dict[str, int]:
        """
        Return the declared physical layout without native group geometry.
        """

        return {
            "atom_lower_z_nm": self.atom_lower_z_nm,
            "atom_upper_z_nm": self.atom_upper_z_nm,
            "period_nm": self.period_nm,
            "reference_plane_offset_nm": self.reference_plane_offset_nm,
            "reflection_plane_z_nm": self.reflection_plane_z_nm,
            "solver_lower_z_nm": self.solver_lower_z_nm,
            "solver_upper_z_nm": self.solver_upper_z_nm,
            "source_plane_z_nm": self.source_plane_z_nm,
            "substrate_height_nm": self.substrate_height_nm,
            "substrate_interface_z_nm": self.substrate_interface_z_nm,
            "transmission_plane_z_nm": self.transmission_plane_z_nm,
            "wavelength_nm": self.wavelength_nm,
        }


@dataclass(frozen=True, slots=True)
class ConstructionManifest:
    """
    Compare declared construction with exact solver read-back.
    """

    template: str
    expected: dict[str, dict[str, object]]
    observed: dict[str, dict[str, object]]
    mismatches: tuple[str, ...]

    def as_mapping(self) -> dict[str, object]:
        """
        Return expected values, observations, and mismatches.
        """

        return {
            "expected": self.expected,
            "mismatches": self.mismatches,
            "observed": self.observed,
            "template": self.template,
        }


@dataclass(frozen=True, slots=True)
class PeriodicConstruction:
    """
    Prepare one route-neutral periodic construction for Lumerical.

    Callers record this value and ask it to build itself in a Session. Shape
    translation, response placement, and read-back remain hidden here.
    """

    cell_identity: str
    height_nm: int
    geometry: PeriodicCrossSection
    layout: _PeriodicResponseLayout
    atom_material: str
    substrate_material: str
    mesh_accuracy: int
    time_budget: PeriodicTimeBudget
    incident_axis: str

    def __post_init__(self) -> None:
        """
        Reject constructions that disagree with their physical layout.
        """

        if (
            type(self.cell_identity) is not str
            or not self.cell_identity.strip()
        ):
            raise ValueError("periodic_construction_identity_required")
        if self.height_nm != self.layout.atom_upper_z_nm:
            raise ValueError("periodic_construction_height_mismatch")
        expected_layout = _periodic_response_layout(
            wavelength_nm=self.layout.wavelength_nm,
            atom_height_nm=self.height_nm,
            period_nm=self.layout.period_nm,
        )
        if self.layout != expected_layout:
            raise ValueError("periodic_construction_layout_mismatch")
        if (
            type(self.atom_material) is not str
            or not self.atom_material.strip()
            or type(self.substrate_material) is not str
            or not self.substrate_material.strip()
        ):
            raise ValueError("periodic_construction_material_required")
        if self.incident_axis not in {"x", "y"}:
            raise ValueError("periodic_construction_incident_axis_invalid")
        if type(self.mesh_accuracy) is not int or self.mesh_accuracy <= 0:
            raise ValueError("periodic_construction_mesh_accuracy_invalid")
        if type(self.time_budget) is not PeriodicTimeBudget:
            raise TypeError("periodic_construction_time_budget_invalid")
        if not isinstance(
            self.geometry,
            (
                CircularCrossSection,
                SquareCrossSection,
                RectangularCrossSection,
                EllipticalCrossSection,
            ),
        ):
            raise TypeError("periodic_construction_geometry_invalid")

    @property
    def period_nm(self) -> int:
        """
        Return the physical lattice period.
        """

        return self.layout.period_nm

    @property
    def wavelength_nm(self) -> int:
        """
        Return the single operating wavelength.
        """

        return self.layout.wavelength_nm

    @property
    def transmission_plane_z_nm(self) -> int:
        """
        Return the declared world-coordinate transmission plane.
        """

        return self.layout.transmission_plane_z_nm

    def as_mapping(self) -> dict[str, object]:
        """
        Return the traceable construction input.
        """

        return {
            "atom_material": self.atom_material,
            "candidate": periodic_cell_mapping(
                cell_identity=self.cell_identity,
                height_nm=self.height_nm,
                geometry=self.geometry,
            ),
            "incident_axis": self.incident_axis,
            "layout": self.layout.as_mapping(),
            "mesh_accuracy": self.mesh_accuracy,
            "substrate_material": self.substrate_material,
            "time_budget": self.time_budget.as_mapping(),
        }

    def build_in(self, session: Session) -> ConstructionManifest:
        """
        Build and read back this periodic construction in one Session.
        """

        return _build(session, self)


@dataclass(frozen=True, slots=True)
class QualificationConstructions:
    """
    Hold the three explicit periodic qualification constructions.
    """

    transmission: PeriodicConstruction
    polarization: tuple[PeriodicConstruction, PeriodicConstruction]


@dataclass(frozen=True, slots=True)
class _NativeGratingPlacement:
    """
    Hold the native analysis-group placement derived from world planes.
    """

    meta_atom_center_nm: int | float
    meta_atom_span_nm: int
    source_offset_nm: int
    position_z_nm: int
    span_z_nm: int


def prepare_periodic_construction(work: PeriodicWork) -> PeriodicConstruction:
    """
    Prepare one exact Lumerical construction from route-neutral work.
    """

    geometry = work.geometry
    if isinstance(geometry, (CircularCrossSection, SquareCrossSection)):
        if work.output_basis != "transverse linear":
            raise ValueError("periodic_transmission_output_basis_invalid")
    elif isinstance(geometry, (RectangularCrossSection, EllipticalCrossSection)):
        if work.output_basis != "cartesian":
            raise ValueError("periodic_polarization_output_basis_invalid")
    else:
        raise TypeError("periodic_construction_geometry_invalid")
    return _prepare_construction(
        cell_identity=work.cell_identity,
        wavelength_nm=work.wavelength_nm,
        period_nm=work.period_nm,
        height_nm=work.height_nm,
        geometry=geometry,
        atom_material=work.materials.atom_native_identity,
        substrate_material=work.materials.substrate_native_identity,
        incident_axis=_linear_axis(work.input_basis),
        maximum_refractive_index=max(
            Decimal(1),
            work.materials.atom_refractive_index,
            work.materials.substrate_refractive_index,
        ),
    )


def prepare_qualification_constructions(
    *,
    atom_material: str,
    substrate_material: str,
) -> QualificationConstructions:
    """
    Prepare transmission and both polarization qualification fixtures.
    """

    wavelength_nm = 400
    period_nm = 660
    height_nm = 500
    transmission = _prepare_construction(
        cell_identity="circular-pillar-height-0500nm-diameter-0160nm",
        wavelength_nm=wavelength_nm,
        period_nm=period_nm,
        height_nm=height_nm,
        geometry=CircularCrossSection(diameter_nm=160),
        atom_material=atom_material,
        substrate_material=substrate_material,
        incident_axis="x",
        maximum_refractive_index=(
            _PERIODIC_TEMPLATE.qualification_refractive_index_guard
        ),
    )
    polarization = tuple(
        _prepare_construction(
            cell_identity=(
                "rectangular-fin-height-0500nm-length-0220nm-width-0100nm"
            ),
            wavelength_nm=wavelength_nm,
            period_nm=period_nm,
            height_nm=height_nm,
            geometry=RectangularCrossSection(
                long_side_nm=220,
                short_side_nm=100,
            ),
            atom_material=atom_material,
            substrate_material=substrate_material,
            incident_axis=incident_axis,
            maximum_refractive_index=(
                _PERIODIC_TEMPLATE.qualification_refractive_index_guard
            ),
        )
        for incident_axis in ("x", "y")
    )
    assert len(polarization) == 2
    return QualificationConstructions(
        transmission=transmission,
        polarization=(polarization[0], polarization[1]),
    )


def _prepare_construction(
    *,
    cell_identity: str,
    wavelength_nm: int,
    period_nm: int,
    height_nm: int,
    geometry: PeriodicCrossSection,
    atom_material: str,
    substrate_material: str,
    incident_axis: str,
    maximum_refractive_index: Decimal,
) -> PeriodicConstruction:
    layout = _periodic_response_layout(
        wavelength_nm=wavelength_nm,
        atom_height_nm=height_nm,
        period_nm=period_nm,
    )
    return PeriodicConstruction(
        cell_identity=cell_identity,
        height_nm=height_nm,
        geometry=geometry,
        layout=layout,
        atom_material=atom_material,
        substrate_material=substrate_material,
        mesh_accuracy=_PERIODIC_TEMPLATE.mesh_accuracy,
        time_budget=plan_periodic_time_budget(
            wavelength_nm=wavelength_nm,
            solver_span_nm=(
                layout.solver_upper_z_nm - layout.solver_lower_z_nm
            ),
            maximum_refractive_index=maximum_refractive_index,
        ),
        incident_axis=incident_axis,
    )


def _periodic_response_layout(
    *,
    wavelength_nm: int,
    atom_height_nm: int,
    period_nm: int,
) -> _PeriodicResponseLayout:
    """
    Calculate the approved outward-rounded world-coordinate layout.
    """

    for value, finding in (
        (wavelength_nm, "periodic_wavelength_invalid"),
        (atom_height_nm, "periodic_height_invalid"),
        (period_nm, "periodic_period_invalid"),
    ):
        if type(value) is not int or value <= 0:
            raise ValueError(finding)
    substrate_height_nm = max(
        _PERIODIC_TEMPLATE.minimum_substrate_height_nm,
        _ceil_ratio_to_placement_step(wavelength_nm, 1),
    )
    source_depth_nm = _ceil_ratio_to_placement_step(
        substrate_height_nm,
        2,
    )
    source_plane_z_nm = -source_depth_nm
    solver_upper_z_nm = _ceil_ratio_to_placement_step(
        2 * atom_height_nm + wavelength_nm,
        2,
    )
    offset_nm = _PERIODIC_TEMPLATE.reference_plane_offset_nm
    return _PeriodicResponseLayout(
        wavelength_nm=wavelength_nm,
        period_nm=period_nm,
        substrate_height_nm=substrate_height_nm,
        substrate_interface_z_nm=0,
        atom_lower_z_nm=0,
        atom_upper_z_nm=atom_height_nm,
        solver_lower_z_nm=source_plane_z_nm - offset_nm,
        source_plane_z_nm=source_plane_z_nm,
        reflection_plane_z_nm=source_plane_z_nm + offset_nm,
        transmission_plane_z_nm=solver_upper_z_nm - offset_nm,
        solver_upper_z_nm=solver_upper_z_nm,
        reference_plane_offset_nm=offset_nm,
    )


def _ceil_ratio_to_placement_step(numerator: int, denominator: int) -> int:
    """
    Round one exact positive rational nanometre value outward to the grid.
    """

    if type(numerator) is not int or numerator <= 0:
        raise ValueError("periodic_placement_numerator_invalid")
    if type(denominator) is not int or denominator <= 0:
        raise ValueError("periodic_placement_denominator_invalid")
    scaled_step = denominator * _PERIODIC_TEMPLATE.placement_step_nm
    return (
        (numerator + scaled_step - 1)
        // scaled_step
        * _PERIODIC_TEMPLATE.placement_step_nm
    )


def _linear_axis(input_basis: str) -> str:
    """
    Translate the shared physical basis into the native construction axis.
    """

    if input_basis == "x linear":
        return "x"
    if input_basis == "y linear":
        return "y"
    raise ValueError("periodic_linear_input_basis_required")


def _native_grating_placement(
    construction: PeriodicConstruction,
) -> _NativeGratingPlacement:
    """
    Derive the relative native container from declared world coordinates.
    """

    layout = construction.layout
    group_lower_z_nm = layout.solver_lower_z_nm
    group_upper_z_nm = layout.transmission_plane_z_nm
    span_z_nm = group_upper_z_nm - group_lower_z_nm
    if span_z_nm % 2:
        raise ValueError("periodic_native_placement_center_not_integral_nm")
    return _NativeGratingPlacement(
        meta_atom_center_nm=(
            construction.height_nm // 2
            if construction.height_nm % 2 == 0
            else construction.height_nm / 2
        ),
        meta_atom_span_nm=construction.height_nm,
        source_offset_nm=layout.reference_plane_offset_nm,
        position_z_nm=group_lower_z_nm + span_z_nm // 2,
        span_z_nm=span_z_nm,
    )


def _build(
    session: Session,
    construction: PeriodicConstruction,
) -> ConstructionManifest:
    """
    Build one periodic structure and compare exact physical read-back.
    """

    atom_kind, atom_properties, template = _native_atom(construction)
    layout = construction.layout
    grating_placement = _native_grating_placement(construction)
    objects: dict[str, tuple[str, dict[str, object]]] = {
        "solver": (
            "fdtd",
            {
                "span_x_nm": layout.period_nm,
                "span_y_nm": layout.period_nm,
                "lower_z_nm": layout.solver_lower_z_nm,
                "upper_z_nm": layout.solver_upper_z_nm,
                "lower_x_boundary": "periodic",
                "upper_x_boundary": "periodic",
                "lower_y_boundary": "periodic",
                "upper_y_boundary": "periodic",
                "lower_z_boundary": "absorbing",
                "upper_z_boundary": "absorbing",
                "mesh_accuracy": construction.mesh_accuracy,
                "simulation_time_fs": (
                    construction.time_budget.ordinary_maximum_fs
                ),
                "autoshutoff_threshold": (
                    construction.time_budget.autoshutoff_threshold
                ),
            },
        ),
        "substrate": (
            "rectangle",
            {
                "material": construction.substrate_material,
                "span_x_nm": layout.period_nm,
                "span_y_nm": layout.period_nm,
                "lower_z_nm": -layout.substrate_height_nm,
                "upper_z_nm": layout.substrate_interface_z_nm,
            },
        ),
        "meta_atom": (atom_kind, atom_properties),
        "grating_response": (
            "grating_response",
            {
                "azimuth_degrees": 0,
                "polar_angle_degrees": 0,
                "meta_atom_center_nm": (
                    grating_placement.meta_atom_center_nm
                ),
                "meta_atom_span_nm": grating_placement.meta_atom_span_nm,
                "polarization_angle_degrees": (
                    0 if construction.incident_axis == "x" else 90
                ),
                "propagation_axis": "z",
                "propagation_direction": "positive",
                "source_offset_nm": grating_placement.source_offset_nm,
                "source_shape": "plane wave",
                "start_wavelength_nm": layout.wavelength_nm,
                "stop_wavelength_nm": layout.wavelength_nm,
                "warnings_suppressed": True,
                "target_transmission_order": 0,
                "relative_coordinates": True,
                "span_x_nm": layout.period_nm,
                "span_y_nm": layout.period_nm,
                "position_z_nm": grating_placement.position_z_nm,
                "span_z_nm": grating_placement.span_z_nm,
            },
        ),
    }
    expected: dict[str, dict[str, object]] = {}
    observed: dict[str, dict[str, object]] = {}
    mismatches: list[str] = []
    observed_group: dict[str, object] = {}
    for name, (kind, properties) in objects.items():
        session.create(kind, name, properties)
        read_back = dict(session.read(name, tuple(properties)))
        if name == "grating_response":
            observed_group = read_back
        else:
            expected[name] = properties
            observed[name] = read_back
        for property_name, expected_value in properties.items():
            if read_back.get(property_name) != expected_value:
                mismatch = (
                    "grating_response.translation"
                    if name == "grating_response"
                    else f"{name}.{property_name}"
                )
                if mismatch not in mismatches:
                    mismatches.append(mismatch)
    observed_planes = session.prepare_grating_response("grating_response")
    expected_response = _expected_response(construction)
    observed_response = _observed_response(
        observed_group,
        observed["solver"],
        observed_planes,
    )
    expected["grating_response"] = expected_response
    observed["grating_response"] = observed_response
    for name, expected_value in expected_response.items():
        if observed_response.get(name) != expected_value:
            mismatches.append(f"grating_response.{name}")
    return ConstructionManifest(
        template=template,
        expected=expected,
        observed=observed,
        mismatches=tuple(mismatches),
    )


def _native_atom(
    construction: PeriodicConstruction,
) -> tuple[str, dict[str, object], str]:
    common: dict[str, object] = {
        "material": construction.atom_material,
        "position_x_nm": 0,
        "position_y_nm": 0,
        "lower_z_nm": construction.layout.atom_lower_z_nm,
        "upper_z_nm": construction.layout.atom_upper_z_nm,
    }
    geometry = construction.geometry
    if isinstance(geometry, CircularCrossSection):
        return (
            "circle",
            {"diameter_nm": geometry.diameter_nm, **common},
            "periodic_transmission",
        )
    if isinstance(geometry, SquareCrossSection):
        return (
            "rectangle",
            {
                **common,
                "span_x_nm": geometry.width_nm,
                "span_y_nm": geometry.width_nm,
            },
            "periodic_transmission",
        )
    if isinstance(geometry, RectangularCrossSection):
        return (
            "rectangle",
            {
                **common,
                "span_x_nm": geometry.long_side_nm,
                "span_y_nm": geometry.short_side_nm,
            },
            "periodic_jones",
        )
    if isinstance(geometry, EllipticalCrossSection):
        return (
            "ellipse",
            {
                **common,
                "major_axis_nm": geometry.major_axis_nm,
                "minor_axis_nm": geometry.minor_axis_nm,
            },
            "periodic_jones",
        )
    raise TypeError("periodic_construction_geometry_invalid")


def _expected_response(
    construction: PeriodicConstruction,
) -> dict[str, object]:
    layout = construction.layout
    return {
        "azimuth_degrees": 0,
        "incident_axis": construction.incident_axis,
        "polar_angle_degrees": 0,
        "propagation_axis": "z",
        "propagation_direction": "positive",
        "reflection_plane_offset_nm": layout.reference_plane_offset_nm,
        "reflection_plane_z_nm": layout.reflection_plane_z_nm,
        "source_plane_z_nm": layout.source_plane_z_nm,
        "target_order": 0,
        "transmission_plane_offset_nm": layout.reference_plane_offset_nm,
        "transmission_plane_z_nm": layout.transmission_plane_z_nm,
        "wavelength_nm": layout.wavelength_nm,
        "span_x_nm": layout.period_nm,
        "span_y_nm": layout.period_nm,
    }


def _observed_response(
    observed_group: dict[str, object],
    observed_solver: dict[str, object],
    planes: _GratingResponsePlanes,
) -> dict[str, object]:
    wavelength_nm = _integer(observed_group, "start_wavelength_nm")
    source_plane_z_nm = planes.source_plane_z_nm
    reflection_plane_z_nm = planes.reflection_plane_z_nm
    transmission_plane_z_nm = planes.transmission_plane_z_nm
    solver_upper_z_nm = _integer(observed_solver, "upper_z_nm")
    return {
        "azimuth_degrees": observed_group["azimuth_degrees"],
        "incident_axis": (
            "x"
            if _integer(observed_group, "polarization_angle_degrees") == 0
            else "y"
        ),
        "polar_angle_degrees": observed_group["polar_angle_degrees"],
        "propagation_axis": observed_group["propagation_axis"],
        "propagation_direction": observed_group["propagation_direction"],
        "reflection_plane_offset_nm": (
            reflection_plane_z_nm - source_plane_z_nm
        ),
        "reflection_plane_z_nm": reflection_plane_z_nm,
        "source_plane_z_nm": source_plane_z_nm,
        "target_order": observed_group["target_transmission_order"],
        "transmission_plane_offset_nm": (
            solver_upper_z_nm - transmission_plane_z_nm
        ),
        "transmission_plane_z_nm": transmission_plane_z_nm,
        "wavelength_nm": wavelength_nm,
        "span_x_nm": observed_group["span_x_nm"],
        "span_y_nm": observed_group["span_y_nm"],
    }


def _integer(values: dict[str, object], name: str) -> int:
    """
    Decode one discrete read-back without accepting lossy coercion.
    """

    value = values[name]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"observed_integer_required:{name}")
    if isinstance(value, float) and not value.is_integer():
        raise ValueError(f"observed_integer_not_discrete:{name}")
    return int(value)
