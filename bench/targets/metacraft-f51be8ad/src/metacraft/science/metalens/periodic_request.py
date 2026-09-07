from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib

from ...authority import Reference
from ...canonical import encode_bytes
from ..periodic_response import (
    CircularCrossSection,
    EllipticalCrossSection,
    PeriodicCrossSection,
    PeriodicMaterials,
    PeriodicPolarizationRequest,
    PeriodicTransmissionRequest,
    PeriodicWork,
    RectangularCrossSection,
    SquareCrossSection,
    periodic_cell_mapping,
    periodic_request_identity,
)
from ..study import Study, Task

from .brief import ControlStrategy, require_monochromatic_wavelength
from .cell_study import CellInputBasis, CellResponseWork, CellStudyPlan, CellStudyRoute
from .design import require_metalens_design
from .height import HeightChoice, validate_height_choice
from .material import MaterialBinding

_PERIODIC_AUTHORITY_WORK_METHODS = {
    "observe_periodic_transmission": "gather_periodic_transmission",
    "observe_periodic_polarization": "gather_jones_library",
}


def _authority_work_task(task: Task) -> Task:
    """
    Project one application task into canonical Authority work bytes.
    """

    try:
        method = _PERIODIC_AUTHORITY_WORK_METHODS[task.method]
    except KeyError as error:
        raise ValueError("periodic_work_method_unsupported") from error
    return replace(task, method=method)


@dataclass(frozen=True, slots=True)
class PeriodicCellCandidate:
    """
    Name one metalens-owned cell before it becomes physical solver work.

    The mapping is the stable candidate protocol shared by work identity,
    artifact construction, and admitted receipt bytes.
    """

    height_nm: int
    geometry: PeriodicCrossSection

    @property
    def shape(self) -> str:
        """
        Return the domain shape name for this periodic candidate.
        """

        if isinstance(self.geometry, CircularCrossSection):
            return "circular pillar"
        if isinstance(self.geometry, SquareCrossSection):
            return "square pillar"
        if isinstance(self.geometry, RectangularCrossSection):
            return "rectangular fin"
        if isinstance(self.geometry, EllipticalCrossSection):
            return "elliptical pillar"
        raise TypeError("periodic_cell_geometry_unsupported")

    @property
    def name(self) -> str:
        """
        Return the canonical identity-bearing candidate name.
        """

        if isinstance(self.geometry, CircularCrossSection):
            dimensions = f"diameter-{self.geometry.diameter_nm:04d}nm"
        elif isinstance(self.geometry, SquareCrossSection):
            dimensions = f"width-{self.geometry.width_nm:04d}nm"
        elif isinstance(self.geometry, RectangularCrossSection):
            dimensions = (
                f"length-{self.geometry.long_side_nm:04d}nm-"
                f"width-{self.geometry.short_side_nm:04d}nm"
            )
        elif isinstance(self.geometry, EllipticalCrossSection):
            dimensions = (
                f"major-{self.geometry.major_axis_nm:04d}nm-"
                f"minor-{self.geometry.minor_axis_nm:04d}nm"
            )
        else:
            raise TypeError("periodic_cell_geometry_unsupported")
        return (
            f"{self.shape.replace(' ', '-')}-height-{self.height_nm:04d}nm-"
            f"{dimensions}"
        )

    @property
    def minimum_dimension_nm(self) -> int:
        """
        Return the candidate's smallest lateral dimension.
        """

        if isinstance(self.geometry, CircularCrossSection):
            return self.geometry.diameter_nm
        if isinstance(self.geometry, SquareCrossSection):
            return self.geometry.width_nm
        if isinstance(self.geometry, RectangularCrossSection):
            return self.geometry.short_side_nm
        if isinstance(self.geometry, EllipticalCrossSection):
            return self.geometry.minor_axis_nm
        raise TypeError("periodic_cell_geometry_unsupported")

    @property
    def maximum_dimension_nm(self) -> int:
        """
        Return the candidate's largest lateral dimension.
        """

        if isinstance(self.geometry, CircularCrossSection):
            return self.geometry.diameter_nm
        if isinstance(self.geometry, SquareCrossSection):
            return self.geometry.width_nm
        if isinstance(self.geometry, RectangularCrossSection):
            return self.geometry.long_side_nm
        if isinstance(self.geometry, EllipticalCrossSection):
            return self.geometry.major_axis_nm
        raise TypeError("periodic_cell_geometry_unsupported")

    def as_mapping(self) -> dict[str, object]:
        """
        Return the exact canonical periodic-cell value.
        """

        return periodic_cell_mapping(
            cell_identity=self.name,
            height_nm=self.height_nm,
            geometry=self.geometry,
        )


def periodic_cell_work_identity(
    task: Task,
    candidate: PeriodicCellCandidate,
    height_choice_reference: Reference,
) -> str:
    """
    Derive the stable protocol identity for one scalar response.
    """

    identity = encode_bytes(
        {
            "candidate": candidate.as_mapping(),
            "height_choice": height_choice_reference,
            "task": _authority_work_task(task),
        }
    )
    return "sha256:" + hashlib.sha256(identity).hexdigest()


def polarization_basis_work_identity(
    task: Task,
    candidate: PeriodicCellCandidate,
    basis: str,
    height_choice_reference: Reference,
) -> str:
    """
    Derive the stable protocol identity for one linear input basis.
    """

    if basis not in {"x", "y"}:
        raise ValueError("periodic_polarization_basis_invalid")
    identity = encode_bytes(
        {
            "basis": basis,
            "candidate": candidate.as_mapping(),
            "height_choice": height_choice_reference,
            "task": _authority_work_task(task),
        }
    )
    return "sha256:" + hashlib.sha256(identity).hexdigest()


def plan_periodic_transmission_request(
    study: Study,
    height: HeightChoice,
    *,
    task: Task,
    height_choice_reference: Reference,
    material_binding: MaterialBinding,
) -> PeriodicTransmissionRequest:
    """
    Translate one ready propagation claim into route-neutral physical work.
    """

    design = require_metalens_design(study)
    if design.control_strategy is not ControlStrategy.PROPAGATION_PHASE:
        raise ValueError("propagation_study_required")
    _validate_context(
        study,
        height,
        task=task,
        claim="periodic_transmission",
        height_choice_reference=height_choice_reference,
        material_binding=material_binding,
    )
    features = periodic_feature_grid(height)
    if design.atom.shape == "circular pillar":
        candidates = tuple(
            PeriodicCellCandidate(
                height.height_nm,
                CircularCrossSection(value),
            )
            for value in features
        )
    elif design.atom.shape == "square pillar":
        candidates = tuple(
            PeriodicCellCandidate(
                height.height_nm,
                SquareCrossSection(value),
            )
            for value in features
        )
    else:
        raise ValueError("propagation_atom_shape_unsupported")
    items = tuple(
        _build_periodic_work(
            candidate,
            study=study,
            height=height,
            task=task,
            height_choice_reference=height_choice_reference,
            material_binding=material_binding,
            work_identity=periodic_cell_work_identity(
                task,
                candidate,
                height_choice_reference,
            ),
            input_basis=(f"{design.incident_polarization.axis or 'x'} linear"),
            output_basis="transverse linear",
        )
        for candidate in candidates
    )
    return PeriodicTransmissionRequest(
        request_identity=periodic_request_identity(
            "transmission",
            tuple(item.work_identity for item in items),
        ),
        items=items,
    )


def plan_periodic_polarization_request(
    study: Study,
    height: HeightChoice,
    *,
    task: Task,
    height_choice_reference: Reference,
    material_binding: MaterialBinding,
) -> PeriodicPolarizationRequest:
    """
    Translate one ready geometric claim into paired physical basis work.
    """

    design = require_metalens_design(study)
    if design.control_strategy is not ControlStrategy.GEOMETRIC_PHASE:
        raise ValueError("geometric_study_required")
    _validate_context(
        study,
        height,
        task=task,
        claim="jones_library",
        height_choice_reference=height_choice_reference,
        material_binding=material_binding,
    )
    features = periodic_feature_grid(height)
    if design.atom.shape == "rectangular fin":
        cross_section_shape = "rectangular fin"
    elif design.atom.shape == "elliptical pillar":
        cross_section_shape = "elliptical pillar"
    else:
        raise ValueError("geometric_atom_shape_unsupported")
    candidates = tuple(
        PeriodicCellCandidate(
            height.height_nm,
            _anisotropic_cross_section(
                cross_section_shape,
                long_dimension_nm=long_dimension,
                short_dimension_nm=short_dimension,
            ),
        )
        for long_dimension in features
        for short_dimension in features
        if long_dimension > short_dimension
    )
    items = tuple(
        _build_periodic_work(
            candidate,
            study=study,
            height=height,
            task=task,
            height_choice_reference=height_choice_reference,
            material_binding=material_binding,
            work_identity=polarization_basis_work_identity(
                task,
                candidate,
                basis,
                height_choice_reference,
            ),
            input_basis=f"{basis} linear",
            output_basis="cartesian",
        )
        for candidate in candidates
        for basis in ("x", "y")
    )
    return PeriodicPolarizationRequest(
        request_identity=periodic_request_identity(
            "polarization",
            tuple(item.work_identity for item in items),
        ),
        items=items,
    )


def _validate_context(
    study: Study,
    height: HeightChoice,
    *,
    task: Task,
    claim: str,
    height_choice_reference: Reference,
    material_binding: MaterialBinding,
) -> None:
    validate_height_choice(
        study,
        height,
        choice_reference=height_choice_reference,
    )
    if task not in study.ready_tasks or task.claim != claim:
        raise ValueError(f"{claim}_not_ready")
    if task.binding_reference != material_binding.solver_binding_reference:
        raise ValueError("periodic_response_binding_mismatch")
    if height_choice_reference not in task.prerequisite_evidence:
        raise ValueError("height_choice_prerequisite_mismatch")
    if material_binding.brief_identity != study.brief_identity:
        raise ValueError("material_binding_brief_mismatch")
    design = require_metalens_design(study)
    wavelength_nm = require_monochromatic_wavelength(design.operating_spectrum)
    if material_binding.wavelength_nm != wavelength_nm:
        raise ValueError("material_binding_wavelength_mismatch")
    if material_binding.atom.family != design.atom.material.family:
        raise ValueError("material_binding_atom_mismatch")
    if material_binding.substrate.family != design.substrate.family:
        raise ValueError("material_binding_substrate_mismatch")
    if (
        material_binding.atom.native_name is None
        or material_binding.substrate.native_name is None
    ):
        raise ValueError("material_binding_native_name_missing")


def periodic_feature_grid(height: HeightChoice) -> tuple[int, ...]:
    """
    Return the complete legacy fabrication grid declared by one height choice.

    New cell-study plans never use this compatibility helper; they project
    their exact work through ``project_cell_study_work``.
    """

    if (
        height.dimension_step_nm <= 0
        or height.minimum_feature_nm <= 0
        or height.maximum_feature_nm < height.minimum_feature_nm
        or height.maximum_feature_nm >= height.period_nm
    ):
        raise ValueError("height_choice_fabrication_domain_invalid")
    values = tuple(
        range(
            height.minimum_feature_nm,
            height.maximum_feature_nm + 1,
            height.dimension_step_nm,
        )
    )
    if not values or values[-1] != height.maximum_feature_nm:
        raise ValueError("height_choice_fabrication_grid_invalid")
    return values


def project_cell_study_work(
    study: Study,
    plan: CellStudyPlan,
    *,
    task: Task,
    material_binding: MaterialBinding,
) -> PeriodicTransmissionRequest | PeriodicPolarizationRequest:
    """Project an admitted CellStudyPlan into solver-neutral periodic work.

    The plan is the source of every candidate and basis.  This path never
    calls ``periodic_feature_grid`` and therefore cannot silently expand a
    bounded study into a complete fabrication grid.
    """

    design = require_metalens_design(study)
    if plan.brief_identity != study.brief_identity:
        raise ValueError("cell_study_plan_brief_mismatch")
    if material_binding.brief_identity != study.brief_identity:
        raise ValueError("cell_study_plan_material_brief_mismatch")
    wavelength_nm = require_monochromatic_wavelength(design.operating_spectrum)
    if material_binding.wavelength_nm != wavelength_nm:
        raise ValueError("cell_study_plan_material_wavelength_mismatch")
    if material_binding.atom.family != design.atom.material.family:
        raise ValueError("cell_study_plan_material_atom_mismatch")
    if material_binding.substrate.family != design.substrate.family:
        raise ValueError("cell_study_plan_material_substrate_mismatch")
    if task.brief_identity != study.brief_identity:
        raise ValueError("cell_study_plan_task_brief_mismatch")
    if task.capacity_scope is None:
        raise ValueError("periodic_response_capacity_scope_missing")
    expected_route = (
        CellStudyRoute.PROPAGATION_PHASE
        if design.control_strategy is ControlStrategy.PROPAGATION_PHASE
        else CellStudyRoute.LOCAL_PB
    )
    if any(item.route is not expected_route for item in plan.work):
        raise ValueError("cell_study_plan_route_mismatch")
    if task.claim not in {"periodic_transmission", "jones_library"}:
        raise ValueError("cell_study_plan_task_claim_invalid")
    if expected_route is CellStudyRoute.PROPAGATION_PHASE:
        if task.claim != "periodic_transmission":
            raise ValueError("propagation_cell_study_claim_mismatch")
    elif task.claim != "jones_library":
        raise ValueError("pb_cell_study_claim_mismatch")
    works = tuple(
        _build_plan_periodic_work(
            item,
            study=study,
            plan=plan,
            task=task,
            material_binding=material_binding,
        )
        for item in plan.work
    )
    if len(works) != plan.work_count:
        raise ValueError("cell_study_plan_work_count_mismatch")
    if expected_route is CellStudyRoute.PROPAGATION_PHASE:
        return PeriodicTransmissionRequest(
            request_identity=periodic_request_identity(
                "transmission",
                tuple(item.work_identity for item in works),
            ),
            items=works,
        )
    return PeriodicPolarizationRequest(
        request_identity=periodic_request_identity(
            "polarization",
            tuple(item.work_identity for item in works),
        ),
        items=works,
    )


def _build_plan_periodic_work(
    item: CellResponseWork,
    *,
    study: Study,
    plan: CellStudyPlan,
    task: Task,
    material_binding: MaterialBinding,
) -> PeriodicWork:
    design = require_metalens_design(study)
    wavelength_nm = require_monochromatic_wavelength(design.operating_spectrum)
    if task.capacity_scope is None:
        raise ValueError("periodic_response_capacity_scope_missing")
    if (
        material_binding.atom.native_name is None
        or material_binding.substrate.native_name is None
    ):
        raise ValueError("material_binding_native_name_missing")
    if task.binding_reference != material_binding.solver_binding_reference:
        raise ValueError("periodic_response_binding_mismatch")
    geometry = _plan_cross_section(item)
    input_basis = (
        "x linear" if item.input_basis is CellInputBasis.X_LINEAR else "y linear"
    )
    if item.route is CellStudyRoute.PROPAGATION_PHASE:
        output_basis = "transverse linear"
    else:
        output_basis = "cartesian"
    identity = encode_bytes(
        {
            "cell_study_plan": plan.option_identity,
            "task": _authority_work_task(task),
            "work": item.identity,
        }
    )
    return PeriodicWork(
        cell_identity=PeriodicCellCandidate(plan.height_nm, geometry).name,
        work_identity="sha256:" + hashlib.sha256(identity).hexdigest(),
        observation_schema=task.schema,
        wavelength_nm=wavelength_nm,
        period_nm=plan.period_nm,
        height_nm=plan.height_nm,
        geometry=geometry,
        materials=PeriodicMaterials(
            atom_native_identity=material_binding.atom.native_name,
            atom_refractive_index=material_binding.atom.refractive_index,
            atom_source_reference=material_binding.sample_reference,
            substrate_native_identity=material_binding.substrate.native_name,
            substrate_refractive_index=(material_binding.substrate.refractive_index),
            substrate_source_reference=material_binding.sample_reference,
        ),
        source_references=tuple(
            dict.fromkeys(
                (
                    material_binding.evidence_reference,
                    material_binding.sample_reference,
                    *task.prerequisite_evidence,
                    *task.consultations,
                )
            )
        ),
        binding_reference=material_binding.solver_binding_reference,
        capacity_scope=task.capacity_scope,
        input_basis=input_basis,
        output_basis=output_basis,
        order_regime=plan.order_regime,
    )


def _plan_cross_section(item: CellResponseWork) -> PeriodicCrossSection:
    geometry = item.geometry
    from .aperture import Circle, Ellipse, Rectangle, Square

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
    raise ValueError("cell_study_geometry_unsupported")


# Keep the execution seam discoverable without adding another lifecycle.
plan_periodic_work = project_cell_study_work


def _build_periodic_work(
    candidate: PeriodicCellCandidate,
    *,
    study: Study,
    height: HeightChoice,
    task: Task,
    height_choice_reference: Reference,
    material_binding: MaterialBinding,
    work_identity: str,
    input_basis: str,
    output_basis: str,
) -> PeriodicWork:
    design = require_metalens_design(study)
    if task.capacity_scope is None:
        raise ValueError("periodic_response_capacity_scope_missing")
    atom_native_identity = material_binding.atom.native_name
    substrate_native_identity = material_binding.substrate.native_name
    if atom_native_identity is None or substrate_native_identity is None:
        raise ValueError("material_binding_native_name_missing")
    return PeriodicWork(
        cell_identity=candidate.name,
        work_identity=work_identity,
        observation_schema=task.schema,
        wavelength_nm=require_monochromatic_wavelength(design.operating_spectrum),
        period_nm=height.period_nm,
        height_nm=height.height_nm,
        geometry=candidate.geometry,
        materials=PeriodicMaterials(
            atom_native_identity=atom_native_identity,
            atom_refractive_index=material_binding.atom.refractive_index,
            atom_source_reference=material_binding.sample_reference,
            substrate_native_identity=substrate_native_identity,
            substrate_refractive_index=(material_binding.substrate.refractive_index),
            substrate_source_reference=material_binding.sample_reference,
        ),
        source_references=tuple(
            dict.fromkeys(
                (
                    material_binding.evidence_reference,
                    material_binding.sample_reference,
                    height_choice_reference,
                    *task.prerequisite_evidence,
                    *task.consultations,
                )
            )
        ),
        binding_reference=material_binding.solver_binding_reference,
        capacity_scope=task.capacity_scope,
        input_basis=input_basis,
        output_basis=output_basis,
        order_regime=height.order_regime,
    )


def _anisotropic_cross_section(
    shape: str,
    *,
    long_dimension_nm: int,
    short_dimension_nm: int,
) -> PeriodicCrossSection:
    if shape == "rectangular fin":
        return RectangularCrossSection(
            short_dimension_nm,
            long_dimension_nm,
        )
    if shape == "elliptical pillar":
        return EllipticalCrossSection(
            short_dimension_nm,
            long_dimension_nm,
        )
    raise ValueError("geometric_atom_shape_unsupported")
