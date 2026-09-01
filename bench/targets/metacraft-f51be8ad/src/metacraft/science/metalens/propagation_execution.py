from __future__ import annotations

from collections.abc import Mapping

from metacraft.authority import Document, Reference
from metacraft.external_activity import ExternalActivityClosure
from metacraft.field import ComponentBasis
from metacraft.science.metalens import field_execution
from metacraft.science.metalens.aperture import (
    Aperture,
    aperture_document,
)
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.design import require_metalens_design
from metacraft.science.metalens.evidence import MetalensEvidence
from metacraft.science.metalens.height import HeightChoice
from metacraft.science.metalens.periodic_request import (
    plan_periodic_transmission_request,
)
from metacraft.science.metalens.periodic_cell_evidence import (
    PropagationEvidenceBatch,
)
from metacraft.science.metalens.reference_surface_evidence import (
    admit_reference_surfaces,
)
from metacraft.science.metalens.pointwise import (
    CellSurface,
    CellSurfaceTable,
    assign_pointwise_cells,
    form_pointwise_surface_field,
)
from metacraft.science.metalens.propagation_phase import (
    PhaseSet,
    PropagationCellLibrary,
    assess_phase_sets,
)
from metacraft.science.metalens.propagation_phase import (
    assign_aperture as assign_phase_aperture,
)
from metacraft.science.periodic_response import (
    AdmittedPeriodicTransmission,
    ObservedPeriodicTransmission,
    PeriodicTransmissionIncomplete,
    PeriodicResponse,
    PeriodicResponseClosure,
    PeriodicResponseUnavailable,
    PeriodicTransmissionObservation,
    PeriodicTransmissionRequest,
    form_admitted_periodic_transmission,
    decode_periodic_transmission,
)
from metacraft.science.study import Finding, FindingKind, Study, Task


def observe_periodic_transmission(
    evidence: MetalensEvidence,
    periodic_response: PeriodicResponse,
    study: Study,
    task: Task,
) -> Study:
    """
    Observe periodic transmission at the chosen height.
    """

    choice = evidence.height_choice(study)
    choice_reference = evidence.fact(study, "height_choice").reference
    request = plan_periodic_transmission_request(
        study,
        choice,
        task=task,
        height_choice_reference=choice_reference,
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
    if isinstance(observed, PeriodicTransmissionIncomplete):
        return _record_incomplete(
            evidence,
            study,
            task,
            observed,
            request_identity=request.request_identity,
        )
    if not isinstance(observed, ObservedPeriodicTransmission):
        raise RuntimeError("periodic_transmission_response_mismatch")
    batch = PropagationEvidenceBatch(request, observed)
    for source in batch.body_references:
        evidence.observe_admitted(source)
    document = Document(task.schema, batch.as_mapping())
    reference = evidence.admit_task(
        task,
        document,
        sources=(
            batch.binding_reference,
            *batch.body_references,
        ),
    )
    return evidence.with_fact(study, task, reference)


def gather_cell_surfaces(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Admit every sampled cell patch returned by the periodic response.
    """

    _batch, request, observed, _choice, _response_study = _restore_response_batch(
        evidence,
        study,
    )

    def admit_surface_document(
        document: Document,
        *,
        references: tuple[Reference, ...],
    ) -> Reference:
        """
        Admit one decoded surface document with all exact component sources.
        """

        return evidence.admit_document(document, sources=references)

    admitted_surfaces = admit_reference_surfaces(
        request,
        observed,
        admit_object=evidence.admit_object,
        admit_document=admit_surface_document,
    )
    library = _restore_cell_library(evidence, study)
    by_source = {
        item.body_reference: admitted
        for item, admitted in zip(
            observed.items,
            admitted_surfaces,
            strict=True,
        )
    }
    admitted = {
        response.cell.identity: by_source[response.source_reference]
        for response in library.responses
    }
    expected = tuple(response.cell.identity for response in library.responses)
    if set(admitted) != set(expected):
        raise RuntimeError("cell_surface_table_incomplete")
    table = CellSurfaceTable(
        library.evidence_reference,
        tuple(CellSurface(identity, admitted[identity]) for identity in expected),
    )
    reference = evidence.admit_task(
        task,
        table.document(),
        sources=(
            library.evidence_reference,
            *(item.reference for item in admitted.values()),
        ),
    )
    return evidence.with_fact(study, task, reference)


def form_cell_library(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Form the propagation cell library from solver evidence.
    """

    (
        batch,
        _request,
        _observed,
        choice,
        response_study,
    ) = _restore_response_batch(evidence, study)
    choice_reference = evidence.fact(study, "height_choice").reference
    document = batch.cell_library_document(
        response_study,
        choice,
        height_choice_reference=choice_reference,
    )
    reference = evidence.admit_task(
        task,
        document,
        sources=(
            batch.binding_reference,
            choice_reference,
            *batch.body_references,
        ),
    )
    return evidence.with_fact(study, task, reference)


def form_phase_set(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> tuple[Study, ...]:
    """
    Form every admissible propagation phase-set branch.

    The complete formation report (delivered levels and every refused
    quantization with its exact reason) rides with the branches as
    diagnostic data. A refused quantization is reported in that data but is
    never fabricated as a scientific branch: only the successful phase sets
    become branches, ordered by ``PhaseSet.levels`` ascending; when none form
    the single honest refusal branch is the sole content.
    """

    library = _restore_cell_library(evidence, study)
    formation = assess_phase_sets(library)
    branches = []
    for phase_set in sorted(formation.phase_sets, key=lambda item: item.levels):
        reference = evidence.admit_task(
            task,
            phase_set.document(),
            sources=phase_set.references(),
        )
        branches.append(evidence.with_fact(study, task, reference))
    if branches:
        return tuple(branches)
    refusal = ",".join(f"{item.levels}:{item.reason}" for item in formation.refusals)
    branch = evidence.with_refusal(
        study,
        "phase_set",
        f"quantization_refused:{refusal}",
    )
    return (branch,)


def assign_aperture(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Assign the selected propagation states across the aperture.
    """

    library = _restore_cell_library(evidence, study)
    phase_set = _restore_phase_set(evidence, study, library)
    phase_reference = evidence.fact(study, "phase_set").reference
    lattice = evidence.physical_lattice(study)
    lattice_reference = evidence.fact(study, "physical_lattice").reference
    aperture = assign_phase_aperture(
        study,
        library,
        phase_set,
        phase_reference,
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
    Form the explicit transverse-linear aperture field.
    """

    return field_execution.admit_formed_field(
        evidence,
        study,
        task,
        basis=ComponentBasis.TRANSVERSE_LINEAR,
        component_channels={
            "x": "transmission",
            "y": None,
        },
    )


def propagate_field(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Propagate the admitted component field into a focal region.
    """

    return field_execution.admit_propagated_field(
        evidence,
        study,
        task,
        components=("x",),
    )


def evaluate_focus(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Evaluate the transmitted component without propagating again.
    """

    return field_execution.admit_evaluated_focus(evidence, study, task)


def assign_pointwise_aperture(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    """
    Assign the complete admitted library without manufactured phase levels.
    """

    library = _restore_cell_library(evidence, study)
    surfaces = _restore_surface_table(evidence, study)
    surfaces_reference = evidence.fact(
        study,
        "cell_surface_table",
    ).reference
    aperture = assign_pointwise_cells(
        require_metalens_design(study),
        library,
        surfaces,
        surfaces_reference=surfaces_reference,
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
    Form one transverse boundary from admitted sampled cell surfaces.
    """

    aperture_reference = evidence.fact(study, "aperture").reference
    aperture = Aperture.from_document(
        Document.from_bytes(evidence.fetch(aperture_reference))
    )
    field = form_pointwise_surface_field(
        aperture,
        _restore_surface_table(evidence, study),
        aperture_reference=aperture_reference,
    )
    reference = evidence.admit_field(task, field)
    return evidence.with_fact(study, task, reference)


def _restore_response_batch(
    evidence: MetalensEvidence,
    study: Study,
) -> tuple[
    PropagationEvidenceBatch,
    PeriodicTransmissionRequest,
    ObservedPeriodicTransmission,
    HeightChoice,
    Study,
]:
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
                "phase_envelope",
                "height_choice",
            }
        ),
        capabilities=study.capabilities,
        bindings=study.bindings,
    )
    choice = evidence.height_choice(response_study)
    task = _ready_task(response_study, "periodic_transmission")
    request = plan_periodic_transmission_request(
        response_study,
        choice,
        task=task,
        height_choice_reference=evidence.fact(
            response_study,
            "height_choice",
        ).reference,
        material_binding=evidence.material_binding(response_study),
    )
    observed = _restore_periodic_transmission(
        evidence,
        study,
        request,
    )
    batch = PropagationEvidenceBatch(request, observed)
    response_fact = evidence.fact(study, "periodic_transmission")
    restored_document = Document(response_fact.schema, batch.as_mapping())
    if restored_document.to_bytes() != evidence.fetch(response_fact.reference):
        raise ValueError("periodic_transmission_evidence_mismatch")
    return (
        batch,
        request,
        observed,
        choice,
        response_study,
    )


def _restore_periodic_transmission(
    evidence: MetalensEvidence,
    study: Study,
    request: PeriodicTransmissionRequest,
) -> ObservedPeriodicTransmission:
    """
    Restore admitted solver observations without repeating solver work.
    """

    response_reference = evidence.fact(
        study,
        "periodic_transmission",
    ).reference
    response_document = Document.from_bytes(evidence.fetch(response_reference))
    response_values = _mapping(
        response_document.values,
        "periodic_transmission_document_invalid",
    )
    encoded_observations = _mapping(
        response_values.get("observations"),
        "periodic_transmission_observations_invalid",
    )
    admitted = []
    for work in request.items:
        encoded = _mapping(
            encoded_observations.get(work.cell_identity),
            "periodic_transmission_observations_invalid",
        )
        source_reference = Reference.from_mapping(
            _mapping(
                encoded.get("reference"),
                "periodic_transmission_reference_invalid",
            )
        )
        recorded_observation = decode_periodic_transmission(
            _mapping(
                encoded.get("response"),
                "periodic_transmission_observation_invalid",
            )
        )
        observation_document = Document.from_bytes(evidence.fetch(source_reference))
        if observation_document.schema_identifier != work.observation_schema:
            raise ValueError("periodic_transmission_observation_schema_mismatch")
        observation = decode_periodic_transmission(observation_document.values)
        if observation.as_mapping() != recorded_observation.as_mapping():
            raise ValueError("periodic_transmission_evidence_mismatch")
        admitted.append(
            form_admitted_periodic_transmission(
                work.work_identity,
                observation,
                source_reference,
                source_reference,
            )
        )
    return ObservedPeriodicTransmission(
        request_identity=request.request_identity,
        items=tuple(admitted),
        closure=PeriodicResponseClosure(
            request.request_identity,
            ExternalActivityClosure.recorded(),
            ExternalActivityClosure.recorded(),
        ),
    )


def _restore_cell_library(
    evidence: MetalensEvidence,
    study: Study,
) -> PropagationCellLibrary:
    library_fact = evidence.fact(study, "cell_library")
    reference = library_fact.reference
    response_fact = evidence.fact(study, "periodic_transmission")
    if response_fact.binding_reference is None:
        raise RuntimeError("periodic_transmission_binding_missing")
    document = Document.from_bytes(evidence.fetch(reference))
    return PropagationCellLibrary.from_document(
        document,
        evidence_reference=reference,
        binding_reference=response_fact.binding_reference,
        height_choice_reference=evidence.fact(
            study,
            "height_choice",
        ).reference,
    )


def _restore_phase_set(
    evidence: MetalensEvidence,
    study: Study,
    library: PropagationCellLibrary,
) -> PhaseSet:
    reference = evidence.fact(study, "phase_set").reference
    phase_set = PhaseSet.from_document(Document.from_bytes(evidence.fetch(reference)))
    if (
        not phase_set.reference_matches(reference)
        or phase_set.library_reference != library.evidence_reference
    ):
        raise RuntimeError("phase_set_evidence_mismatch")
    return phase_set


def _restore_surface_table(
    evidence: MetalensEvidence,
    study: Study,
) -> CellSurfaceTable:
    reference = evidence.fact(study, "cell_surface_table").reference
    return CellSurfaceTable.from_document(
        Document.from_bytes(evidence.fetch(reference)),
        fetch=evidence.fetch,
    )


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
    incomplete: PeriodicTransmissionIncomplete,
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
