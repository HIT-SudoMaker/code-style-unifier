from __future__ import annotations

from collections.abc import Mapping

from ...authority import Document, Reference
from ...external_activity import ExternalActivityClosure
from ...field import ComponentBasis
from ...field.reference_surface import (
    RequestedInputBasis,
    restore_reference_surface,
)
from .aperture import (
    Aperture,
    aperture_document,
    assign_continuous_orientations,
)
from .compiler import compile_metalens
from .design import require_metalens_design
from .evidence import MetalensEvidence
from .geometric_phase import (
    CellChoice,
    JonesLibrary,
    OrientationSet,
    OrientationRelation,
    PolarizationConvention,
    assign_aperture as assign_geometric_aperture,
    choose_cell_by_legacy_ranking,
    derive_orientation_relation as derive_scientific_orientation_relation,
    form_orientation_sets,
)
from .height import HeightAdviceBasis, HeightChoice
from .periodic_request import (
    plan_periodic_polarization_request,
)
from .periodic_cell_evidence import JonesEvidenceBatch
from .reference_surface_evidence import (
    admit_reference_surfaces,
)
from .pointwise import (
    GeometricSurfaceTransform,
    form_geometric_surface_field,
    derive_geometric_surface_transform,
)
from ..periodic_response import (
    AdmittedPeriodicPolarization,
    ObservedPeriodicPolarization,
    PeriodicPolarizationIncomplete,
    PeriodicPolarizationObservation,
    PeriodicPolarizationRequest,
    PeriodicResponse,
    PeriodicResponseUnavailable,
    PeriodicResponseClosure,
    form_admitted_periodic_polarization,
    decode_periodic_polarization,
)
from ..study import Finding, FindingKind, Study, Task

from . import field_execution


def establish_polarization_convention(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Establish the circular-polarization convention.
    """

    handedness = require_metalens_design(study).incident_polarization.handedness
    if handedness not in {"left", "right"}:
        raise RuntimeError("geometric_handedness_invalid")
    convention = PolarizationConvention(circular_input=handedness)
    reference = evidence.admit_task(task, convention.document())
    return evidence.with_fact(study, task, reference)


def observe_periodic_polarization(
    evidence: MetalensEvidence,
    periodic_response: PeriodicResponse,
    study: Study,
    task: Task,
) -> Study:
    """
    Observe and interpret the Jones-response library at the chosen height.
    """

    height = evidence.height_choice(study)
    height_reference = evidence.fact(study, "height_choice").reference
    request = plan_periodic_polarization_request(
        study,
        height,
        task=task,
        height_choice_reference=height_reference,
        material_binding=evidence.material_binding(study),
    )
    observed = periodic_response.observe(request)
    if isinstance(observed, PeriodicResponseUnavailable):
        return _record_unavailable(
            evidence,
            study,
            task,
            observed,
            request_identity=request.request_identity,
        )
    if isinstance(observed, PeriodicPolarizationIncomplete):
        return _record_incomplete(
            evidence,
            study,
            task,
            observed,
            request_identity=request.request_identity,
        )
    if not isinstance(observed, ObservedPeriodicPolarization):
        raise RuntimeError("periodic_polarization_response_mismatch")
    handedness = require_metalens_design(study).incident_polarization.handedness
    if handedness not in {"left", "right"}:
        raise RuntimeError("geometric_handedness_invalid")
    batch = JonesEvidenceBatch(
        request,
        observed,
        PolarizationConvention(circular_input=handedness),
    )
    for source in batch.body_references:
        evidence.observe_admitted(source)
    convention_reference = evidence.fact(
        study,
        "polarization_convention",
    ).reference
    document = batch.document(
        study,
        height,
        height_choice_reference=height_reference,
        convention_reference=convention_reference,
    )
    reference = evidence.admit_task(
        task,
        document,
        sources=(
            batch.binding_reference,
            height_reference,
            convention_reference,
            *batch.body_references,
        ),
    )
    return evidence.with_fact(study, task, reference)


def gather_geometric_surface_transform(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Admit the selected cell's same-solve x/y patches and analytic transform.
    """

    _batch, request, observed, _height, _response_study = _restore_jones_batch(
        evidence,
        study,
    )
    choice = _restore_cell_choice(evidence, study)

    def admit_surface_document(
        document: Document,
        *,
        references: tuple[Reference, ...],
    ) -> Reference:
        """
        Admit one decoded surface document with all exact component sources.
        """

        return evidence.admit_document(document, sources=references)

    surfaces = admit_reference_surfaces(
        request,
        observed,
        cell_identity=choice.candidate,
        admit_object=evidence.admit_object,
        admit_document=admit_surface_document,
    )
    if len(surfaces) != 2:
        raise RuntimeError("geometric_surface_basis_incomplete")
    x_linear, y_linear = surfaces
    relation = _restore_orientation_relation(evidence, study)
    relation_reference = evidence.fact(
        study,
        "orientations",
    ).reference
    handedness = require_metalens_design(study).incident_polarization.handedness
    if handedness is None:
        raise RuntimeError("geometric_handedness_invalid")
    requested_input = {
        "right": RequestedInputBasis.RIGHT_CIRCULAR,
        "left": RequestedInputBasis.LEFT_CIRCULAR,
    }.get(handedness)
    if requested_input is None:
        raise RuntimeError("geometric_handedness_invalid")
    transform = derive_geometric_surface_transform(
        relation,
        x_linear,
        y_linear,
        relation_reference=relation_reference,
        requested_input_basis=requested_input,
    )
    reference = evidence.admit_task(
        task,
        transform.document(),
        sources=(
            relation_reference,
            x_linear.reference,
            y_linear.reference,
        ),
    )
    return evidence.with_fact(study, task, reference)


def choose_cell(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Choose one geometric-phase cell from admitted evidence.
    """

    library = _restore_jones_response_library(evidence, study)
    height = evidence.height_choice(study)
    height_reference = evidence.fact(study, "height_choice").reference
    choice = choose_cell_by_legacy_ranking(
        study,
        height,
        library,
        height_choice_reference=height_reference,
    )
    reference = evidence.admit_task(
        task,
        choice.document(),
        sources=(
            choice.binding_reference,
            choice.height_domain_reference,
            *(
                (choice.height_basis.advice_reference,)
                if isinstance(choice.height_basis, HeightAdviceBasis)
                else ()
            ),
            choice.height_choice_reference,
            choice.library_reference,
            choice.convention_reference,
            *choice.source_references,
        ),
    )
    return evidence.with_fact(study, task, reference)


def derive_orientation_relation(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Admit one continuous analytic orientation relation.
    """

    choice = _restore_cell_choice(evidence, study)
    choice_reference = evidence.fact(study, "cell_choice").reference
    relation = derive_scientific_orientation_relation(
        choice,
        choice_reference=choice_reference,
    )
    reference = evidence.admit_task(
        task,
        relation.document(),
        sources=(
            relation.binding_reference,
            relation.cell_choice_reference,
            relation.library_reference,
            relation.convention_reference,
            *relation.source_references,
        ),
    )
    return evidence.with_fact(study, task, reference)


def form_orientation_set(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> tuple[Study, ...]:
    """
    Branch one admitted analytic relation into three fabrication sets.
    """

    relation = _restore_orientation_relation(evidence, study)
    relation_reference = evidence.fact(
        study,
        "orientations",
    ).reference
    branches = []
    for orientation_set in form_orientation_sets(
        relation,
        relation_reference=relation_reference,
    ):
        reference = evidence.admit_task(
            task,
            orientation_set.document(),
            sources=orientation_set.references(),
        )
        branches.append(evidence.with_fact(study, task, reference))
    return tuple(branches)


def assign_aperture(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Assign physical converted and retained aperture channels.
    """

    choice = _restore_cell_choice(evidence, study)
    relation = _restore_orientation_relation(evidence, study)
    orientation_set = _restore_orientation_set(evidence, study)
    lattice = evidence.physical_lattice(study)
    lattice_reference = evidence.fact(study, "physical_lattice").reference
    aperture = assign_geometric_aperture(
        study,
        choice,
        relation,
        orientation_set,
        choice_reference=evidence.fact(
            study,
            "cell_choice",
        ).reference,
        relation_reference=evidence.fact(
            study,
            "orientations",
        ).reference,
        orientation_set_reference=evidence.fact(
            study,
            "orientation_set",
        ).reference,
        lattice=lattice,
        lattice_reference=lattice_reference,
    )
    return field_execution.admit_assigned_aperture(evidence, study, task, aperture)


def form_field(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Form the explicit circular-component aperture field.
    """

    incident = require_metalens_design(study).incident_polarization.handedness
    if incident not in {"right", "left"}:
        raise RuntimeError("circular_incident_polarization_required")
    component_channels = (
        {"right": "retained", "left": "converted"}
        if incident == "right"
        else {"right": "converted", "left": "retained"}
    )
    return field_execution.admit_formed_field(
        evidence,
        study,
        task,
        basis=ComponentBasis.CIRCULAR,
        component_channels=component_channels,
    )


def propagate_field(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Propagate the admitted component field into a focal region.
    """

    incident = require_metalens_design(study).incident_polarization.handedness
    converted_component = "left" if incident == "right" else "right"
    return field_execution.admit_propagated_field(
        evidence,
        study,
        task,
        components=(converted_component,),
    )


def evaluate_focus(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Evaluate the converted component without propagating again.
    """

    incident = require_metalens_design(study).incident_polarization.handedness
    return field_execution.admit_evaluated_focus(
        evidence,
        study,
        task,
        leakage_component=incident,
    )


def assign_pointwise_aperture(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Place one admitted cell through its continuous orientation relation.
    """

    choice = _restore_cell_choice(evidence, study)
    relation = _restore_orientation_relation(evidence, study)
    choice_reference = evidence.fact(study, "cell_choice").reference
    relation_reference = evidence.fact(study, "orientations").reference
    aperture = assign_continuous_orientations(
        require_metalens_design(study),
        spacing_nm=choice.cell.period_nm,
        choice=choice,
        orientation_relation=relation,
        choice_reference=choice_reference,
        orientation_relation_reference=relation_reference,
        lattice=evidence.physical_lattice(study),
        lattice_reference=evidence.fact(study, "physical_lattice").reference,
    )
    reference = evidence.admit_task(
        task,
        aperture_document(aperture),
        sources=aperture.evidence,
    )
    return evidence.with_fact(study, task, reference)


def form_pointwise_field(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Form one sampled geometric boundary from two admitted linear patches.
    """

    aperture_reference = evidence.fact(study, "aperture").reference
    aperture = Aperture.from_document(
        Document.from_bytes(evidence.fetch(aperture_reference))
    )
    relation = _restore_orientation_relation(evidence, study)
    transform_reference = evidence.fact(
        study,
        "geometric_surface_transform",
    ).reference
    transform = GeometricSurfaceTransform.from_document(
        Document.from_bytes(evidence.fetch(transform_reference))
    )
    x_linear = restore_reference_surface(
        transform.x_linear_response_reference,
        evidence.fetch,
    )
    y_linear = restore_reference_surface(
        transform.y_linear_response_reference,
        evidence.fetch,
    )
    field = form_geometric_surface_field(
        aperture,
        relation,
        x_linear,
        y_linear,
        transform,
        aperture_reference=aperture_reference,
        transform_reference=transform_reference,
    )
    reference = evidence.admit_field(task, field)
    return evidence.with_fact(study, task, reference)


def _restore_jones_response_library(
    evidence: MetalensEvidence,
    study: Study,
) -> JonesLibrary:
    (
        batch,
        _request,
        _observed,
        height,
        response_study,
    ) = _restore_jones_batch(evidence, study)
    height_reference = evidence.fact(study, "height_choice").reference
    return batch.as_library(
        response_study,
        height,
        evidence.fact(study, "jones_library").reference,
        height_choice_reference=height_reference,
        convention_reference=evidence.fact(
            study,
            "polarization_convention",
        ).reference,
    )


def _restore_jones_batch(
    evidence: MetalensEvidence,
    study: Study,
) -> tuple[
    JonesEvidenceBatch,
    PeriodicPolarizationRequest,
    ObservedPeriodicPolarization,
    HeightChoice,
    Study,
]:
    """
    Restore the Jones record against its exact response-ready frontier.
    """

    height_reference = evidence.fact(study, "height_choice").reference
    response_study = compile_metalens(
        study.brief,
        advice=study.advice,
        evidence=tuple(
            fact
            for fact in study.evidence
            if fact.claim
            in {
                "target_phase",
                "material_binding",
                "period_domain",
                "period_choice",
                "height_domain",
                "height_choice",
                "polarization_convention",
            }
        ),
        capabilities=study.capabilities,
        bindings=study.bindings,
    )
    height = evidence.height_choice(response_study)
    task = _ready_task(response_study, "jones_library")
    request = plan_periodic_polarization_request(
        response_study,
        height,
        task=task,
        height_choice_reference=height_reference,
        material_binding=evidence.material_binding(response_study),
    )
    observed = _restore_periodic_polarization(
        evidence,
        study,
        request,
    )
    handedness = require_metalens_design(
        response_study
    ).incident_polarization.handedness
    if handedness not in {"left", "right"}:
        raise RuntimeError("geometric_handedness_invalid")
    batch = JonesEvidenceBatch(
        request,
        observed,
        PolarizationConvention(circular_input=handedness),
    )
    library_reference = evidence.fact(study, "jones_library").reference
    convention_reference = evidence.fact(
        study,
        "polarization_convention",
    ).reference
    restored_document = batch.document(
        response_study,
        height,
        height_choice_reference=height_reference,
        convention_reference=convention_reference,
    )
    if restored_document.to_bytes() != evidence.fetch(library_reference):
        raise ValueError("jones_library_evidence_mismatch")
    return batch, request, observed, height, response_study


def _restore_periodic_polarization(
    evidence: MetalensEvidence,
    study: Study,
    request: PeriodicPolarizationRequest,
) -> ObservedPeriodicPolarization:
    """
    Restore admitted solver observations without repeating solver work.
    """

    library_reference = evidence.fact(study, "jones_library").reference
    library_document = Document.from_bytes(evidence.fetch(library_reference))
    library_values = _mapping(
        library_document.values,
        "jones_library_document_invalid",
    )
    encoded_sources = _mapping(
        library_values.get("source_references"),
        "jones_library_sources_invalid",
    )
    admitted = []
    for work in request.items:
        candidate_sources = _mapping(
            encoded_sources.get(work.cell_identity),
            "jones_library_sources_invalid",
        )
        basis = work.input_basis.removesuffix(" linear")
        source_reference = Reference.from_mapping(
            _mapping(
                candidate_sources.get(basis),
                "jones_library_sources_invalid",
            )
        )
        observation_document = Document.from_bytes(evidence.fetch(source_reference))
        if observation_document.schema_identifier != work.observation_schema:
            raise ValueError("periodic_polarization_observation_schema_mismatch")
        admitted.append(
            form_admitted_periodic_polarization(
                work.work_identity,
                decode_periodic_polarization(observation_document.values),
                source_reference,
                source_reference,
            )
        )
    return ObservedPeriodicPolarization(
        request_identity=request.request_identity,
        items=tuple(admitted),
        closure=PeriodicResponseClosure(
            request.request_identity,
            ExternalActivityClosure.recorded(),
            ExternalActivityClosure.recorded(),
        ),
    )


def _restore_cell_choice(
    evidence: MetalensEvidence,
    study: Study,
) -> CellChoice:
    return choose_cell_by_legacy_ranking(
        study,
        evidence.height_choice(study),
        _restore_jones_response_library(evidence, study),
        height_choice_reference=evidence.fact(
            study,
            "height_choice",
        ).reference,
    )


def _restore_orientation_relation(
    evidence: MetalensEvidence,
    study: Study,
) -> OrientationRelation:
    reference = evidence.fact(study, "orientations").reference
    relation = OrientationRelation.from_document(
        Document.from_bytes(evidence.fetch(reference))
    )
    if not relation.reference_matches(reference):
        raise RuntimeError("geometric_orientations_evidence_mismatch")
    return relation


def _restore_orientation_set(
    evidence: MetalensEvidence,
    study: Study,
) -> OrientationSet:
    reference = evidence.fact(study, "orientation_set").reference
    orientation_set = OrientationSet.from_document(
        Document.from_bytes(evidence.fetch(reference))
    )
    if (
        not orientation_set.reference_matches(reference)
        or orientation_set.orientation_relation_reference
        != evidence.fact(study, "orientations").reference
    ):
        raise RuntimeError("geometric_orientation_set_evidence_mismatch")
    return orientation_set


def _record_unavailable(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
    unavailable: PeriodicResponseUnavailable,
    *,
    request_identity: str,
) -> Study:
    if unavailable.request_identity != request_identity:
        raise ValueError("periodic_response_request_identity_mismatch")
    return evidence.with_unavailable(
        study,
        task,
        f"periodic_response_unavailable:{unavailable.reason.value}",
    )


def _record_incomplete(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
    incomplete: PeriodicPolarizationIncomplete,
    *,
    request_identity: str,
) -> Study:
    if incomplete.request_identity != request_identity:
        raise ValueError("periodic_response_request_identity_mismatch")
    for item in (*incomplete.items, *incomplete.incomplete_items):
        evidence.observe_admitted(item.body_reference)
    return evidence.with_finding(
        study,
        Finding(
            claim=task.claim,
            kind=FindingKind.INCOMPLETE,
            needs=("periodic_observation_incomplete",),
            record_references=tuple(
                item.body_reference for item in incomplete.incomplete_items
            ),
        ),
    )


def _mapping(value: object, reason: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(reason)
    return value


def _ready_task(study: Study, claim: str) -> Task:
    matches = tuple(task for task in study.ready_tasks if task.claim == claim)
    if len(matches) != 1:
        raise RuntimeError(f"{claim}_not_ready")
    return matches[0]
