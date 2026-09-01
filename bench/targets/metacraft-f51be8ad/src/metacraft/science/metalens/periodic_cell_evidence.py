from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import hashlib
import math

from ...authority import Document, Reference
from ...canonical import encode_bytes
from ...external_activity import ExternalActivityOrigin
from ..periodic_response import (
    AdmittedPeriodicPolarization,
    AdmittedPeriodicTransmission,
    CircularCrossSection,
    EllipticalCrossSection,
    ObservedPeriodicPolarization,
    ObservedPeriodicTransmission,
    PeriodicCrossSection,
    PeriodicCellObservation,
    PeriodicComplexValue,
    PeriodicPolarizationRequest,
    PeriodicTransmissionRequest,
    PeriodicWork,
    RectangularCrossSection,
    SquareCrossSection,
    periodic_observation_mapping,
)
from ..phase import phase_from_float
from ..result import EvidenceOrigin
from ..study import Study

from .aperture import (
    Cell,
    Circle,
    Ellipse,
    Geometry,
    Material,
    Rectangle,
    Square,
)
from .brief import ControlStrategy
from .cell_study import CellStudyPlan, CellStudyRoute
from .design import require_metalens_design
from .geometric_phase import (
    ComplexCoefficient,
    JonesCell,
    JonesLibrary,
    JonesResponse,
    PolarizationConvention,
    project_circular_channels,
)
from .height import HeightChoice, validate_height_choice
from .periodic_request import periodic_feature_grid
from .periodic_request import PeriodicCellCandidate as _PeriodicCellCandidate
from .propagation_phase import (
    PropagationCellLibrary,
    PropagationResponse,
)


@dataclass(frozen=True, slots=True)
class PropagationEvidenceBatch:
    """
    Interpret one complete physical transmission batch as metalens evidence.
    """

    request: PeriodicTransmissionRequest
    observed: ObservedPeriodicTransmission

    def __post_init__(self) -> None:
        """
        Require a complete batch with one consistent phase-plane contract.
        """

        validate_observed_batch(self.request, self.observed)
        phase_planes = {item.observation.phase_planes for item in self.observed.items}
        if len(phase_planes) != 1:
            raise ValueError("phase_planes_mismatch")

    @property
    def binding_reference(self) -> Reference:
        """
        Return the one solver binding shared by this batch.
        """

        return _batch_binding(tuple(self.request.items))

    @property
    def body_references(self) -> tuple[Reference, ...]:
        """
        Return every admitted transmission observation reference.
        """

        return tuple(item.body_reference for item in self.observed.items)

    def as_mapping(self) -> dict[str, object]:
        """
        Form the stable canonical aggregate response document.
        """

        return {
            "binding_reference": self.binding_reference.as_mapping(),
            "observations": {
                work.cell_identity: {
                    "reference": item.body_reference.as_mapping(),
                    "response": periodic_observation_mapping(item),
                }
                for work, item in zip(
                    self.request.items,
                    self.observed.items,
                    strict=True,
                )
            },
        }

    def cell_library_document(
        self,
        study: Study,
        height: HeightChoice,
        *,
        height_choice_reference: Reference,
    ) -> Document:
        """
        Interpret the complete batch as a fixed propagation library document.
        """

        responses = self._responses(
            study,
            height,
            height_choice_reference=height_choice_reference,
        )
        return PropagationCellLibrary.document_from(
            binding_reference=self.binding_reference,
            height_choice_reference=height_choice_reference,
            phase_planes=responses[0].phase_planes,
            responses=responses,
        )

    def as_fixed_library(
        self,
        study: Study,
        height: HeightChoice,
        *,
        height_choice_reference: Reference,
        evidence_reference: Reference,
    ) -> PropagationCellLibrary:
        """
        Interpret this batch as one admitted fixed propagation library.
        """

        responses = self._responses(
            study,
            height,
            height_choice_reference=height_choice_reference,
        )
        return PropagationCellLibrary(
            binding_reference=self.binding_reference,
            height_choice_reference=height_choice_reference,
            evidence_reference=evidence_reference,
            phase_planes=responses[0].phase_planes,
            responses=responses,
        )

    def _responses(
        self,
        study: Study,
        height: HeightChoice,
        *,
        height_choice_reference: Reference,
    ) -> tuple[PropagationResponse, ...]:
        validate_height_choice(
            study,
            height,
            choice_reference=height_choice_reference,
        )
        planned = {
            _propagation_geometry_key(work): (work, item)
            for work, item in zip(
                self.request.items,
                self.observed.items,
                strict=True,
            )
        }
        if len(planned) != len(self.request.items):
            raise ValueError("propagation_library_geometry_duplicate")
        if set(planned) != _expected_propagation_geometry_keys(
            study,
            height,
        ):
            raise ValueError("propagation_library_grid_incomplete")
        return tuple(
            _propagation_response(
                study,
                height,
                work,
                item,
                binding_reference=self.binding_reference,
                height_choice_reference=height_choice_reference,
            )
            for _, (work, item) in sorted(planned.items())
        )


@dataclass(frozen=True, slots=True)
class JonesEvidenceBatch:
    """
    Pair linear basis observations and own the circular Jones projection.
    """

    request: PeriodicPolarizationRequest
    observed: ObservedPeriodicPolarization
    convention: PolarizationConvention

    def __post_init__(self) -> None:
        """
        Require one complete independent x/y response pair per cell.
        """

        validate_observed_batch(self.request, self.observed)
        by_cell: dict[str, set[str]] = {}
        for work, item in zip(
            self.request.items,
            self.observed.items,
            strict=True,
        ):
            basis = item.observation.input_basis
            if basis != _linear_axis(work.input_basis):
                raise ValueError("periodic_polarization_basis_mismatch")
            by_cell.setdefault(work.cell_identity, set()).add(basis)
        if any(bases != {"x", "y"} for bases in by_cell.values()):
            raise ValueError("jones_library_basis_incomplete")

    @property
    def binding_reference(self) -> Reference:
        """
        Return the one solver binding shared by this batch.
        """

        return _batch_binding(tuple(self.request.items))

    @property
    def body_references(self) -> tuple[Reference, ...]:
        """
        Return every admitted polarization observation reference.
        """

        return tuple(item.body_reference for item in self.observed.items)

    def document(
        self,
        study: Study,
        height: HeightChoice,
        *,
        height_choice_reference: Reference,
        convention_reference: Reference,
    ) -> Document:
        """
        Interpret paired linear responses as one Jones-library document.
        """

        validate_height_choice(
            study,
            height,
            choice_reference=height_choice_reference,
        )
        cells = self._cells(study, height)
        return JonesLibrary.document_from(
            cells=cells,
            binding_reference=self.binding_reference,
            height_choice_reference=height_choice_reference,
            convention=self.convention,
            convention_reference=convention_reference,
            source_references=tuple(
                reference for cell in cells for reference in cell.source_references
            ),
        )

    def as_library(
        self,
        study: Study,
        height: HeightChoice,
        evidence_reference: Reference,
        *,
        height_choice_reference: Reference,
        convention_reference: Reference,
    ) -> JonesLibrary:
        """
        Interpret paired linear responses as one admitted Jones library.
        """

        validate_height_choice(
            study,
            height,
            choice_reference=height_choice_reference,
        )
        cells = self._cells(study, height)
        return JonesLibrary(
            cells=cells,
            binding_reference=self.binding_reference,
            height_choice_reference=height_choice_reference,
            convention=self.convention,
            convention_reference=convention_reference,
            evidence_reference=evidence_reference,
            source_references=tuple(
                reference for cell in cells for reference in cell.source_references
            ),
        )

    def _cells(
        self,
        study: Study,
        height: HeightChoice,
    ) -> tuple[JonesCell, ...]:
        if any(work.height_nm != height.height_nm for work in self.request.items):
            raise ValueError("jones_library_height_mismatch")
        paired = _polarization_pairs(self.request, self.observed)
        observed_geometry = {
            _geometric_geometry_key(from_x[0]) for from_x, _from_y in paired
        }
        if len(observed_geometry) != len(
            paired
        ) or observed_geometry != _expected_geometric_geometry_keys(study, height):
            raise ValueError("jones_library_grid_incomplete")
        return tuple(
            _jones_cell(
                study,
                height,
                from_x,
                from_y,
                convention=self.convention,
            )
            for from_x, from_y in paired
        )


def validate_observed_batch(
    request: PeriodicTransmissionRequest | PeriodicPolarizationRequest,
    observed: ObservedPeriodicTransmission | ObservedPeriodicPolarization,
) -> None:
    """
    Require one outcome to match the request identity and exact work order.
    """

    if request.request_identity != observed.request_identity:
        raise ValueError("periodic_response_request_identity_mismatch")
    if len(request.items) != len(observed.items):
        raise ValueError("periodic_response_batch_incomplete")
    if tuple(item.work_identity for item in request.items) != tuple(
        item.work_identity for item in observed.items
    ):
        raise ValueError("periodic_response_work_mismatch")
    for work, item in zip(request.items, observed.items, strict=True):
        _validate_candidate_observation(work, item.observation.cell)
        reference_surface = item.observation.reference_surface
        if (
            reference_surface is not None
            and not math.isclose(
                float(reference_surface.wavelength_m),
                work.wavelength_nm * 1e-9,
                rel_tol=1e-12,
                abs_tol=0,
            )
        ):
            raise ValueError("periodic_response_wavelength_mismatch")


def validate_cell_study_batch(
    plan: CellStudyPlan,
    request: PeriodicTransmissionRequest | PeriodicPolarizationRequest,
    observed: ObservedPeriodicTransmission | ObservedPeriodicPolarization,
) -> None:
    """Validate response completeness against plan-owned work only.

    The new lifecycle compares the exact request and plan contexts; it does
    not call the legacy complete-grid helper or infer missing candidates.
    """

    if isinstance(request, PeriodicTransmissionRequest):
        if not isinstance(observed, ObservedPeriodicTransmission):
            raise ValueError("cell_study_response_route_mismatch")
    elif not isinstance(observed, ObservedPeriodicPolarization):
        raise ValueError("cell_study_response_route_mismatch")

    if len(request.items) != plan.work_count:
        raise ValueError("cell_study_response_work_count_mismatch")
    validate_observed_batch(request, observed)
    expected_bases = tuple(
        "x linear" if item.input_basis.value == "x_linear" else "y linear"
        for item in plan.work
    )
    if tuple(item.input_basis for item in request.items) != expected_bases:
        raise ValueError("cell_study_response_basis_mismatch")
    if any(
        item.height_nm != plan.height_nm or item.period_nm != plan.period_nm
        for item in request.items
    ):
        raise ValueError("cell_study_response_context_mismatch")
    for planned, work in zip(plan.work, request.items, strict=True):
        expected_geometry = _plan_periodic_geometry(planned.geometry)
        expected_name = _PeriodicCellCandidate(
            plan.height_nm,
            expected_geometry,
        ).name
        if work.geometry != expected_geometry or work.cell_identity != expected_name:
            raise ValueError("cell_study_response_candidate_mismatch")
    expected_route = (
        CellStudyRoute.PROPAGATION_PHASE
        if isinstance(request, PeriodicTransmissionRequest)
        else CellStudyRoute.LOCAL_PB
    )
    if any(item.route is not expected_route for item in plan.work):
        raise ValueError("cell_study_response_route_mismatch")


def _plan_periodic_geometry(geometry: Geometry) -> PeriodicCrossSection:
    if isinstance(geometry, Circle):
        return CircularCrossSection(geometry.diameter_nm)
    if isinstance(geometry, Square):
        return SquareCrossSection(geometry.width_nm)
    if isinstance(geometry, Rectangle):
        return RectangularCrossSection(
            geometry.short_side_nm,
            geometry.long_side_nm,
        )
    if isinstance(geometry, Ellipse):
        return EllipticalCrossSection(
            geometry.minor_axis_nm,
            geometry.major_axis_nm,
        )
    raise ValueError("cell_study_geometry_invalid")


def _batch_binding(items: tuple[PeriodicWork, ...]) -> Reference:
    bindings = {item.binding_reference for item in items}
    if len(bindings) != 1:
        raise ValueError("periodic_response_binding_mixed")
    return next(iter(bindings))


def _validate_candidate_observation(
    work: PeriodicWork,
    cell: PeriodicCellObservation,
) -> None:
    if cell != PeriodicCellObservation(
        work.cell_identity,
        work.height_nm,
        work.geometry,
    ):
        raise ValueError("periodic_response_candidate_mismatch")


def _science_geometry(geometry: PeriodicCrossSection) -> Geometry:
    if isinstance(geometry, CircularCrossSection):
        return Circle(geometry.diameter_nm)
    if isinstance(geometry, SquareCrossSection):
        return Square(geometry.width_nm)
    if isinstance(geometry, RectangularCrossSection):
        return Rectangle(geometry.short_side_nm, geometry.long_side_nm)
    if isinstance(geometry, EllipticalCrossSection):
        return Ellipse(geometry.minor_axis_nm, geometry.major_axis_nm)
    raise TypeError("periodic_cell_geometry_unsupported")


def _materials(study: Study) -> tuple[Material, Material]:
    design = require_metalens_design(study)
    return (
        Material(design.atom.material.family, design.atom.material.source),
        Material(design.substrate.family, design.substrate.source),
    )


def _propagation_cell(
    study: Study,
    height: HeightChoice,
    work: PeriodicWork,
    *,
    source_reference: Reference,
) -> Cell:
    geometry = _science_geometry(work.geometry)
    if not isinstance(geometry, (Circle, Square)):
        raise TypeError("propagation_candidate_type_invalid")
    atom, substrate = _materials(study)
    identity = encode_bytes(
        {
            "atom": atom.as_mapping(),
            "geometry": geometry.as_mapping(),
            "height_nm": height.height_nm,
            "period_nm": height.period_nm,
            "shape": geometry.shape,
            "substrate": substrate.as_mapping(),
        }
    )
    return Cell(
        identity="sha256:" + hashlib.sha256(identity).hexdigest(),
        atom=atom,
        substrate=substrate,
        period_nm=height.period_nm,
        height_nm=height.height_nm,
        geometry=geometry,
        source=source_reference,
    )


def _propagation_geometry_key(work: PeriodicWork) -> tuple[str, int]:
    geometry = _science_geometry(work.geometry)
    if not isinstance(geometry, (Circle, Square)):
        raise TypeError("propagation_candidate_type_invalid")
    return geometry.shape, geometry.span_nm


def _expected_propagation_geometry_keys(
    study: Study,
    height: HeightChoice,
) -> set[tuple[str, int]]:
    design = require_metalens_design(study)
    if design.control_strategy is not ControlStrategy.PROPAGATION_PHASE:
        raise ValueError("propagation_study_required")
    if design.atom.shape not in {"circular pillar", "square pillar"}:
        raise ValueError("propagation_atom_shape_unsupported")
    return {(design.atom.shape, feature) for feature in periodic_feature_grid(height)}


def _geometric_geometry_key(
    work: PeriodicWork,
) -> tuple[str, int, int]:
    geometry = _science_geometry(work.geometry)
    if not isinstance(geometry, (Rectangle, Ellipse)):
        raise TypeError("geometric_candidate_type_invalid")
    if isinstance(geometry, Rectangle):
        return geometry.shape, geometry.long_side_nm, geometry.short_side_nm
    return geometry.shape, geometry.major_axis_nm, geometry.minor_axis_nm


def _expected_geometric_geometry_keys(
    study: Study,
    height: HeightChoice,
) -> set[tuple[str, int, int]]:
    design = require_metalens_design(study)
    if design.control_strategy is not ControlStrategy.GEOMETRIC_PHASE:
        raise ValueError("geometric_study_required")
    if design.atom.shape not in {
        "rectangular fin",
        "elliptical pillar",
    }:
        raise ValueError("geometric_atom_shape_unsupported")
    features = periodic_feature_grid(height)
    return {
        (design.atom.shape, long_dimension, short_dimension)
        for long_dimension in features
        for short_dimension in features
        if long_dimension > short_dimension
    }


def _propagation_response(
    study: Study,
    height: HeightChoice,
    work: PeriodicWork,
    item: AdmittedPeriodicTransmission,
    *,
    binding_reference: Reference,
    height_choice_reference: Reference,
) -> PropagationResponse:
    observation = item.observation
    return PropagationResponse(
        binding_reference=binding_reference,
        height_choice_reference=height_choice_reference,
        phase_planes=observation.phase_planes,
        cell=_propagation_cell(
            study,
            height,
            work,
            source_reference=item.body_reference,
        ),
        transmission_real=observation.transmission.real_part,
        transmission_imaginary=observation.transmission.imaginary_part,
        realized_phase=observation.realized_phase,
        useful_power=observation.useful_power,
        leakage_power=observation.leakage_power,
        solver_status="complete",
        warnings=observation.warnings,
        is_construction_valid=True,
        execution_origin=_evidence_origin(item.execution_origin),
        source_reference=item.body_reference,
    )


def _polarization_pairs(
    request: PeriodicPolarizationRequest,
    observed: ObservedPeriodicPolarization,
) -> tuple[
    tuple[
        tuple[PeriodicWork, AdmittedPeriodicPolarization],
        tuple[PeriodicWork, AdmittedPeriodicPolarization],
    ],
    ...,
]:
    by_cell: dict[
        str,
        dict[str, tuple[PeriodicWork, AdmittedPeriodicPolarization]],
    ] = {}
    cell_order: list[str] = []
    for work, item in zip(request.items, observed.items, strict=True):
        if work.cell_identity not in by_cell:
            by_cell[work.cell_identity] = {}
            cell_order.append(work.cell_identity)
        basis = _linear_axis(work.input_basis)
        if basis in by_cell[work.cell_identity]:
            raise ValueError("jones_library_basis_duplicate")
        by_cell[work.cell_identity][basis] = (work, item)
    if any(set(values) != {"x", "y"} for values in by_cell.values()):
        raise ValueError("jones_library_basis_incomplete")
    return tuple((by_cell[cell]["x"], by_cell[cell]["y"]) for cell in cell_order)


def _jones_cell(
    study: Study,
    height: HeightChoice,
    from_x: tuple[PeriodicWork, AdmittedPeriodicPolarization],
    from_y: tuple[PeriodicWork, AdmittedPeriodicPolarization],
    *,
    convention: PolarizationConvention,
) -> JonesCell:
    work_x, admitted_x = from_x
    work_y, admitted_y = from_y
    if (
        work_x.cell_identity != work_y.cell_identity
        or work_x.geometry != work_y.geometry
    ):
        raise ValueError("jones_library_candidate_mismatch")
    observation_x = admitted_x.observation
    observation_y = admitted_y.observation
    if observation_x.phase_planes != observation_y.phase_planes:
        raise ValueError("phase_planes_mismatch")
    output_x_from_x = _complex_value(observation_x.output_x)
    output_y_from_x = _complex_value(observation_x.output_y)
    output_x_from_y = _complex_value(observation_y.output_x)
    output_y_from_y = _complex_value(observation_y.output_y)
    converted, retained = _circular_channels(
        output_x_from_x,
        output_y_from_x,
        output_x_from_y,
        output_y_from_y,
        convention=convention,
    )
    geometry = _science_geometry(work_x.geometry)
    if not isinstance(geometry, (Rectangle, Ellipse)):
        raise TypeError("geometric_candidate_type_invalid")
    atom, substrate = _materials(study)
    cell_identity = encode_bytes(
        {
            "atom": atom.as_mapping(),
            "geometry": geometry.as_mapping(),
            "height_nm": height.height_nm,
            "period_nm": height.period_nm,
            "shape": geometry.shape,
            "source": admitted_x.body_reference,
            "substrate": substrate.as_mapping(),
        }
    )
    cell = Cell(
        identity="sha256:" + hashlib.sha256(cell_identity).hexdigest(),
        atom=atom,
        substrate=substrate,
        period_nm=height.period_nm,
        height_nm=height.height_nm,
        geometry=geometry,
        source=admitted_x.body_reference,
    )
    return JonesCell(
        cell=cell,
        jones=JonesResponse(
            output_x_from_input_x=_coefficient(output_x_from_x),
            output_y_from_input_x=_coefficient(output_y_from_x),
            output_x_from_input_y=_coefficient(output_x_from_y),
            output_y_from_input_y=_coefficient(output_y_from_y),
        ),
        converted=_coefficient(converted),
        converted_phase=phase_from_float(math.atan2(converted.imag, converted.real)),
        converted_power=Decimal(str(abs(converted) ** 2)),
        retained=_coefficient(retained),
        retained_phase=phase_from_float(math.atan2(retained.imag, retained.real)),
        retained_power=Decimal(str(abs(retained) ** 2)),
        source_references=(
            admitted_x.body_reference,
            admitted_y.body_reference,
        ),
        execution_origin=(
            EvidenceOrigin.NATIVE
            if (
                admitted_x.execution_origin is ExternalActivityOrigin.NATIVE
                and admitted_y.execution_origin is ExternalActivityOrigin.NATIVE
            )
            else EvidenceOrigin.SYNTHETIC
        ),
    )


def _circular_channels(
    output_x_from_x: complex,
    output_y_from_x: complex,
    output_x_from_y: complex,
    output_y_from_y: complex,
    *,
    convention: PolarizationConvention,
) -> tuple[complex, complex]:
    converted, retained = project_circular_channels(
        JonesResponse(
            output_x_from_input_x=_coefficient(output_x_from_x),
            output_y_from_input_x=_coefficient(output_y_from_x),
            output_x_from_input_y=_coefficient(output_x_from_y),
            output_y_from_input_y=_coefficient(output_y_from_y),
        ),
        convention,
    )
    return converted.complex_value(), retained.complex_value()


def _complex_value(value: PeriodicComplexValue) -> complex:
    return complex(
        float(value.real_part),
        float(value.imaginary_part),
    )


def _coefficient(value: complex) -> ComplexCoefficient:
    return ComplexCoefficient(
        Decimal(str(value.real)),
        Decimal(str(value.imag)),
    )


def _evidence_origin(value: ExternalActivityOrigin) -> EvidenceOrigin:
    return (
        EvidenceOrigin.NATIVE
        if value is ExternalActivityOrigin.NATIVE
        else EvidenceOrigin.SYNTHETIC
    )


def _linear_axis(value: str) -> str:
    if value == "x linear":
        return "x"
    if value == "y linear":
        return "y"
    raise ValueError("periodic_linear_input_required")
