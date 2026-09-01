from __future__ import annotations

import math
from dataclasses import dataclass, replace
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from typing import TypeVar

import numpy

from metacraft.authority import Authority, Document, Reference
from metacraft.authority.session import AuthoritySession
from metacraft.field.evidence import FIELD_SCHEMA
from metacraft.field.reference_surface import (
    AdmittedReferenceSurface,
    ReferenceSurfaceResponse,
    RequestedInputBasis,
    admit_response_components,
    reference_surface_document,
)
from metacraft.field.sample import (
    ComponentBasis,
    CoordinateFrame,
    Field,
    FieldComponent,
    Medium,
    PlaneSurface,
)
from metacraft.science.metalens.aperture import (
    APERTURE_SCHEMA,
    Cell,
    Circle,
    Geometry,
    Material,
    Rectangle,
    aperture_document,
    assign_continuous_orientations,
)
from metacraft.science.metalens.brief import MetalensBrief
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.design import require_metalens_design
from metacraft.science.metalens.brief import require_monochromatic_wavelength
from metacraft.science.metalens.focal_field_comparison import FocalFieldComparison
from metacraft.science.metalens.focus import (
    FOCAL_REGION_SCHEMA,
    Focus,
    FocusConvergence,
    HalfMaximum,
    Leakage,
    focus_document,
)
from metacraft.science.metalens.geometric_phase import (
    CELL_CHOICE_SCHEMA,
    JONES_LIBRARY_SCHEMA,
    LEGACY_PB_RESPONSE_RANKING,
    ORIENTATION_RELATION_SCHEMA,
    ORIENTATION_SET_SCHEMA,
    CellChoice,
    ComplexCoefficient,
    JonesResponse,
    OrientationRelation,
    OrientationSet,
    PolarizationConvention,
)
from metacraft.science.metalens.geometric_phase import (
    assign_aperture as assign_oriented_aperture,
)
from metacraft.science.metalens.geometric_phase import (
    derive_orientation_relation,
    form_orientation_sets,
)
from metacraft.science.metalens.height import (
    FabricationRange,
    HeightConstraintBasis,
    HeightDomain,
)
from metacraft.science.metalens.height_advice import HeightAdvice, HeightRecommendation
from metacraft.science.metalens.material import MaterialBinding
from metacraft.science.metalens.period import (
    PeriodChoice,
    PeriodDomain,
    derive_period_domain,
    resolve_period_choice,
)
from metacraft.science.metalens.period_advice import PeriodAdvice
from metacraft.science.metalens.pointwise import (
    CellSurface,
    CellSurfaceTable,
    assign_pointwise_cells,
    derive_geometric_surface_transform,
)
from metacraft.science.metalens.propagation_envelope import (
    OpticalContrast,
    PhaseEnvelope,
    estimate_phase_envelope,
)
from metacraft.science.metalens.propagation_phase import (
    CELL_LIBRARY_SCHEMA,
    PERIODIC_TRANSMISSION_SCHEMA,
    PHASE_SET_SCHEMA,
    PropagationCellLibrary,
    PropagationResponse,
)
from metacraft.science.metalens.propagation_phase import (
    assign_aperture as assign_quantized_aperture,
)
from metacraft.science.metalens.propagation_phase import form_phase_sets
from metacraft.science.metalens.result import MetalensResult, conclude
from metacraft.science.phase import FULL_TURN
from metacraft.science.result import (
    BoundDocument,
    EvidenceOrigin,
    ResultClosure,
    brief_document,
    design_document,
    study_document,
)
from metacraft.science.study import Advice, Binding, Capability, Evidence, Study, Task
from tests.brief_fixtures import geometric_brief, propagation_brief
from tests.domain_fixtures import height_advice as fixture_height_advice
from tests.domain_fixtures import material_binding as fixture_material_binding
from tests.domain_fixtures import period_advice as fixture_period_advice

AdviceValue = TypeVar("AdviceValue", bound=Advice)


@dataclass(frozen=True, slots=True)
class RecordedResult:
    authority: Authority
    session: AuthoritySession
    study: Study
    closure: ResultClosure
    conclusion: MetalensResult


def propagation_result(
    root: Path,
    levels: int,
    *,
    brief: MetalensBrief | None = None,
    period_nm: int | None = None,
    height_nm: int | None = None,
) -> RecordedResult:
    """
    Record one complete propagation proof without invoking a solver or ASM.
    """

    return propagation_results(
        root,
        (levels,),
        brief=brief,
        period_nm=period_nm,
        height_nm=height_nm,
    )[0]


def propagation_results(
    root: Path,
    levels: tuple[int, ...] = (8, 12, 16),
    *,
    brief: MetalensBrief | None = None,
    period_nm: int | None = None,
    height_nm: int | None = None,
) -> tuple[RecordedResult, ...]:
    """
    Branch several quantizations from one admitted propagation prefix.
    """

    if not levels or len(set(levels)) != len(levels):
        raise ValueError("fixture_phase_levels_invalid")
    root.mkdir(parents=True, exist_ok=True)
    authority = Authority(root / "authority")
    admission = AuthoritySession(authority)
    if brief is None:
        brief = replace(
            propagation_brief(),
            cell_period_nm=200,
            atom_height_nm=600,
            focal_length_um=Decimal("2"),
            numerical_aperture=Decimal("0.1"),
        )
    selected_period = period_nm or brief.cell_period_nm
    selected_height = height_nm or brief.atom_height_nm
    if selected_period is None or selected_height is None:
        raise ValueError("propagation_fixture_cell_missing")
    initial = compile_metalens(brief)
    capabilities = tuple(
        Capability(name)
        for name in dict.fromkeys(
            obligation.capability
            for obligation in initial.proof.claims
            if obligation.capability is not None
        )
    )
    bindings = tuple(
        Binding(
            capability.name,
            admission.admit_document(
                Document(
                    "fixture.binding",
                    {"capability": capability.name},
                ),
            ),
        )
        for capability in capabilities
    )
    evidence: tuple[Evidence, ...] = ()
    advice: tuple[Advice, ...] = ()
    responses: tuple[PropagationResponse, ...] | None = None
    while True:
        advice = _fixture_advice(
            brief,
            evidence,
            advice,
            admission,
            period_nm=selected_period,
            height_nm=selected_height,
        )
        study = compile_metalens(
            brief,
            advice=advice,
            evidence=evidence,
            capabilities=capabilities,
            bindings=bindings,
        )
        task = study.ready_tasks[0]
        if task.claim == "phase_set":
            break
        facts = {fact.claim: fact for fact in evidence}
        foundation = _foundation_document(
            task,
            facts,
            admission,
            study,
            brief,
            advice,
            period_nm=selected_period,
            height_nm=selected_height,
        )
        if foundation is not None:
            document = foundation
        elif task.claim == "periodic_transmission":
            responses = _propagation_responses(
                admission,
                levels=max(levels),
                binding_reference=_required(task.binding_reference),
                height_reference=facts["height_choice"].reference,
                period_nm=selected_period,
                height_nm=selected_height,
                atom_material=brief.atom.material.family,
                substrate_material=brief.substrate.family,
            )
            document = Document(
                PERIODIC_TRANSMISSION_SCHEMA,
                {"responses": len(responses)},
            )
        elif task.claim == "cell_library":
            if responses is None:
                raise AssertionError("fixture responses missing")
            document = PropagationCellLibrary.document_from(
                binding_reference=_required(
                    facts["periodic_transmission"].binding_reference
                ),
                height_choice_reference=facts["height_choice"].reference,
                phase_planes="substrate-to-superstrate",
                responses=responses,
            )
        else:
            document = _evaluation_document(
                task,
                facts,
                geometric=False,
            )
        evidence = _append_fact(
            evidence,
            task,
            admission.admit_document(document),
        )

    facts = {fact.claim: fact for fact in evidence}
    library = _propagation_library(authority, facts)
    available_sets = {
        phase_set.levels: phase_set for phase_set in form_phase_sets(library)
    }
    if not set(levels) <= set(available_sets):
        raise AssertionError("fixture phase set missing")
    brief_record, design_record = _bind_design(admission, study)
    recorded = []
    for level in levels:
        branch = evidence
        phase_set = available_sets[level]
        while True:
            study = compile_metalens(
                brief,
                advice=advice,
                evidence=branch,
                capabilities=capabilities,
                bindings=bindings,
            )
            if not study.ready_tasks:
                if study.findings:
                    raise AssertionError(study.findings)
                break
            task = study.ready_tasks[0]
            facts = {fact.claim: fact for fact in branch}
            if task.claim == "phase_set":
                document = phase_set.document()
            elif task.claim == "aperture":
                aperture = assign_quantized_aperture(
                    study,
                    library,
                    phase_set,
                    facts["phase_set"].reference,
                )
                document = aperture_document(aperture)
            else:
                document = _evaluation_document(
                    task,
                    facts,
                    geometric=False,
                )
            branch = _append_fact(
                branch,
                task,
                admission.admit_document(document),
            )
        closure = _bind_recorded_study(
            admission,
            study,
            brief=brief_record,
            design=design_record,
        )
        recorded.append(
            RecordedResult(
                authority,
                admission,
                study,
                closure,
                conclude(
                    study,
                    closure,
                    fetch=authority.fetch,
                ),
            )
        )
    return tuple(recorded)


def geometric_result(root: Path) -> RecordedResult:
    """
    Record one complete geometric proof with eight orientations.
    """

    return geometric_results(root, (8,))[0]


def geometric_results(
    root: Path,
    counts: tuple[int, ...] = (8, 12, 16),
    *,
    brief: MetalensBrief | None = None,
    period_nm: int | None = None,
    height_nm: int | None = None,
    cell_geometry: Geometry | None = None,
) -> tuple[RecordedResult, ...]:
    """
    Branch several orientation sets from one admitted geometric prefix.
    """

    if not counts or len(set(counts)) != len(counts):
        raise ValueError("fixture_orientation_counts_invalid")
    root.mkdir(parents=True, exist_ok=True)
    authority = Authority(root / "authority")
    admission = AuthoritySession(authority)
    if brief is None:
        brief = replace(
            geometric_brief(),
            cell_period_nm=200,
            atom_height_nm=600,
            focal_length_um=Decimal("2"),
            numerical_aperture=Decimal("0.1"),
        )
    selected_period = period_nm or brief.cell_period_nm
    selected_height = height_nm or brief.atom_height_nm
    if selected_period is None or selected_height is None:
        raise ValueError("geometric_fixture_cell_missing")
    state: dict[str, object] = {}
    initial = compile_metalens(brief)
    capabilities = tuple(
        Capability(name)
        for name in dict.fromkeys(
            obligation.capability
            for obligation in initial.proof.claims
            if obligation.capability is not None
        )
    )
    bindings = tuple(
        Binding(
            capability.name,
            admission.admit_document(
                Document(
                    "fixture.binding",
                    {"capability": capability.name},
                ),
            ),
        )
        for capability in capabilities
    )
    evidence: tuple[Evidence, ...] = ()
    advice: tuple[Advice, ...] = ()
    while True:
        advice = _fixture_advice(
            brief,
            evidence,
            advice,
            admission,
            period_nm=selected_period,
            height_nm=selected_height,
        )
        study = compile_metalens(
            brief,
            advice=advice,
            evidence=evidence,
            capabilities=capabilities,
            bindings=bindings,
        )
        task = study.ready_tasks[0]
        if task.claim == "orientation_set":
            break
        facts = {fact.claim: fact for fact in evidence}
        foundation = _foundation_document(
            task,
            facts,
            admission,
            study,
            brief,
            advice,
            period_nm=selected_period,
            height_nm=selected_height,
        )
        if foundation is not None:
            document = foundation
        elif task.claim == "polarization_convention":
            convention = PolarizationConvention(circular_input="right")
            state["convention"] = convention
            document = convention.document()
        elif task.claim == "jones_library":
            document = Document(JONES_LIBRARY_SCHEMA, {"recorded": True})
        elif task.claim == "cell_choice":
            choice = _cell_choice(
                admission,
                facts,
                state,
                period_nm=selected_period,
                height_nm=selected_height,
                atom_material=brief.atom.material.family,
                substrate_material=brief.substrate.family,
                geometry=cell_geometry,
            )
            state["choice"] = choice
            document = choice.document()
        elif task.claim == "orientations":
            choice = _choice(state)
            orientations = derive_orientation_relation(
                choice,
                choice_reference=facts["cell_choice"].reference,
            )
            state["orientations"] = orientations
            document = orientations.document()
        else:
            document = _evaluation_document(task, facts, geometric=True)
        evidence = _append_fact(
            evidence,
            task,
            admission.admit_document(document),
        )

    facts = {fact.claim: fact for fact in evidence}
    available_sets = {
        orientation_set.count: orientation_set
        for orientation_set in form_orientation_sets(
            _orientations(state),
            relation_reference=facts["orientations"].reference,
        )
    }
    if not set(counts) <= set(available_sets):
        raise AssertionError("fixture orientation set missing")
    brief_record, design_record = _bind_design(admission, study)
    recorded = []
    for count in counts:
        branch = evidence
        orientation_set = available_sets[count]
        while True:
            study = compile_metalens(
                brief,
                advice=advice,
                evidence=branch,
                capabilities=capabilities,
                bindings=bindings,
            )
            if not study.ready_tasks:
                if study.findings:
                    raise AssertionError(study.findings)
                break
            task = study.ready_tasks[0]
            facts = {fact.claim: fact for fact in branch}
            if task.claim == "orientation_set":
                document = orientation_set.document()
            elif task.claim == "aperture":
                aperture = assign_oriented_aperture(
                    study,
                    _choice(state),
                    _orientations(state),
                    orientation_set,
                    choice_reference=facts["cell_choice"].reference,
                    relation_reference=facts["orientations"].reference,
                    orientation_set_reference=facts["orientation_set"].reference,
                )
                document = aperture_document(aperture)
            else:
                document = _evaluation_document(
                    task,
                    facts,
                    geometric=True,
                )
            branch = _append_fact(
                branch,
                task,
                admission.admit_document(document),
            )
        closure = _bind_recorded_study(
            admission,
            study,
            brief=brief_record,
            design=design_record,
        )
        recorded.append(
            RecordedResult(
                authority,
                admission,
                study,
                closure,
                conclude(
                    study,
                    closure,
                    fetch=authority.fetch,
                ),
            )
        )
    return tuple(recorded)


def pointwise_propagation_result(
    root: Path,
    brief: MetalensBrief,
    *,
    period_nm: int,
    height_nm: int,
) -> RecordedResult:
    """
    Record one complete high-aperture propagation proof through its real DAG.
    """

    authority, admission = _recording_workspace(root)
    capabilities, bindings = _execution_contract(
        compile_metalens(brief),
        admission,
    )
    evidence: tuple[Evidence, ...] = ()
    advice: tuple[Advice, ...] = ()
    selected_height_nm = height_nm
    library: PropagationCellLibrary | None = None
    surfaces: CellSurfaceTable | None = None
    while True:
        advice = _fixture_advice(
            brief,
            evidence,
            advice,
            admission,
            period_nm=period_nm,
            height_nm=selected_height_nm,
        )
        selected_height_nm = _fixture_recommended_height_nm(
            advice,
            fallback_height_nm=selected_height_nm,
        )
        study = compile_metalens(
            brief,
            advice=advice,
            evidence=evidence,
            capabilities=capabilities,
            bindings=bindings,
        )
        if not study.ready_tasks:
            if study.findings:
                raise AssertionError(study.findings)
            break
        task = study.ready_tasks[0]
        facts = {fact.claim: fact for fact in evidence}
        foundation = _foundation_document(
            task,
            facts,
            admission,
            study,
            brief,
            advice,
            period_nm=period_nm,
            height_nm=selected_height_nm,
        )
        if foundation is not None:
            document = foundation
        elif task.claim == "periodic_transmission":
            responses = _propagation_responses(
                admission,
                levels=16,
                binding_reference=_required(task.binding_reference),
                height_reference=facts["height_choice"].reference,
                period_nm=period_nm,
                height_nm=selected_height_nm,
                atom_material=brief.atom.material.family,
                substrate_material=brief.substrate.family,
            )
            document = Document(
                PERIODIC_TRANSMISSION_SCHEMA,
                {"responses": len(responses)},
            )
        elif task.claim == "cell_library":
            document = PropagationCellLibrary.document_from(
                binding_reference=_required(
                    facts["periodic_transmission"].binding_reference
                ),
                height_choice_reference=facts["height_choice"].reference,
                phase_planes="substrate-to-superstrate",
                responses=responses,
            )
        elif task.claim == "cell_surface_table":
            library_reference = facts["cell_library"].reference
            library = PropagationCellLibrary.from_document(
                Document.from_bytes(authority.fetch(library_reference)),
                evidence_reference=library_reference,
                binding_reference=_required(
                    facts["periodic_transmission"].binding_reference
                ),
                height_choice_reference=facts["height_choice"].reference,
            )
            surfaces = CellSurfaceTable(
                library_reference,
                tuple(
                    CellSurface(
                        response.cell.identity,
                        _admit_reference_surface(
                            admission,
                            response.cell.identity,
                            RequestedInputBasis.X_LINEAR,
                            period_nm=period_nm,
                        ),
                    )
                    for response in library.responses
                ),
            )
            document = surfaces.document()
        elif task.claim == "aperture":
            if library is None or surfaces is None:
                raise AssertionError("pointwise propagation basis missing")
            surfaces_reference = facts["cell_surface_table"].reference
            document = aperture_document(
                assign_pointwise_cells(
                    require_metalens_design(study),
                    library,
                    surfaces,
                    surfaces_reference=surfaces_reference,
                    device="cpu",
                    maximum_sites_per_chunk=65_536,
                )
            )
        elif task.claim == "focal_comparison":
            document = _focal_comparison(
                facts["focal_region"].reference,
                facts["aplanatic_reference"].reference,
                _required(facts["focal_region"].binding_reference),
                _required(facts["aplanatic_reference"].binding_reference),
            ).document()
        else:
            document = _pointwise_evaluation_document(task, facts)
        evidence = _append_fact(
            evidence,
            task,
            admission.admit_document(document),
        )
    closure = _bind_recorded_study(admission, study)
    return RecordedResult(
        authority,
        admission,
        study,
        closure,
        conclude(
            study,
            closure,
            fetch=authority.fetch,
        ),
    )


def pointwise_geometric_result(
    root: Path,
    brief: MetalensBrief,
    *,
    period_nm: int,
    height_nm: int,
) -> RecordedResult:
    """
    Record one complete high-aperture geometric proof through its real DAG.
    """

    authority, admission = _recording_workspace(root)
    capabilities, bindings = _execution_contract(
        compile_metalens(brief),
        admission,
    )
    evidence: tuple[Evidence, ...] = ()
    advice: tuple[Advice, ...] = ()
    state: dict[str, object] = {}
    while True:
        advice = _fixture_advice(
            brief,
            evidence,
            advice,
            admission,
            period_nm=period_nm,
            height_nm=height_nm,
        )
        study = compile_metalens(
            brief,
            advice=advice,
            evidence=evidence,
            capabilities=capabilities,
            bindings=bindings,
        )
        if not study.ready_tasks:
            if study.findings:
                raise AssertionError(study.findings)
            break
        task = study.ready_tasks[0]
        facts = {fact.claim: fact for fact in evidence}
        foundation = _foundation_document(
            task,
            facts,
            admission,
            study,
            brief,
            advice,
            period_nm=period_nm,
            height_nm=height_nm,
        )
        if foundation is not None:
            document = foundation
        elif task.claim == "polarization_convention":
            convention = PolarizationConvention(
                circular_input=brief.incident_polarization.handedness,
            )
            state["convention"] = convention
            document = convention.document()
        elif task.claim == "jones_library":
            document = Document(JONES_LIBRARY_SCHEMA, {"recorded": True})
        elif task.claim == "cell_choice":
            choice = _cell_choice(
                admission,
                facts,
                state,
                period_nm=period_nm,
                height_nm=height_nm,
                atom_material=brief.atom.material.family,
                substrate_material=brief.substrate.family,
            )
            state["choice"] = choice
            document = choice.document()
        elif task.claim == "orientations":
            choice = _choice(state)
            orientations = derive_orientation_relation(
                choice,
                choice_reference=facts["cell_choice"].reference,
            )
            state["orientations"] = orientations
            document = orientations.document()
        elif task.claim == "aperture":
            choice = _choice(state)
            document = aperture_document(
                assign_continuous_orientations(
                    require_metalens_design(study),
                    spacing_nm=period_nm,
                    choice=choice,
                    orientation_relation=_orientations(state),
                    choice_reference=facts["cell_choice"].reference,
                    orientation_relation_reference=facts["orientations"].reference,
                )
            )
        elif task.claim == "geometric_surface_transform":
            orientations = _orientations(state)
            x_linear = _admit_reference_surface(
                admission,
                "geometric-x",
                RequestedInputBasis.X_LINEAR,
                period_nm=period_nm,
            )
            y_linear = _admit_reference_surface(
                admission,
                "geometric-y",
                RequestedInputBasis.Y_LINEAR,
                period_nm=period_nm,
            )
            document = derive_geometric_surface_transform(
                orientations,
                x_linear,
                y_linear,
                relation_reference=facts["orientations"].reference,
                requested_input_basis=RequestedInputBasis.RIGHT_CIRCULAR,
            ).document()
        elif task.claim == "focal_comparison":
            document = _focal_comparison(
                facts["focal_region"].reference,
                facts["aplanatic_reference"].reference,
                _required(facts["focal_region"].binding_reference),
                _required(facts["aplanatic_reference"].binding_reference),
            ).document()
        else:
            document = _pointwise_evaluation_document(task, facts)
        evidence = _append_fact(
            evidence,
            task,
            admission.admit_document(document),
        )
    closure = _bind_recorded_study(admission, study)
    return RecordedResult(
        authority,
        admission,
        study,
        closure,
        conclude(
            study,
            closure,
            fetch=authority.fetch,
        ),
    )


def admit_result(recorded: RecordedResult) -> Reference:
    """
    Admit one conclusion with exactly the references encoded by its document.
    """

    return recorded.session.admit_document(
        recorded.conclusion.document(),
        references=recorded.conclusion.references(),
    )


def _recording_workspace(
    root: Path,
) -> tuple[Authority, AuthoritySession]:
    root.mkdir(parents=True, exist_ok=True)
    authority = Authority(root / "authority")
    return authority, AuthoritySession(authority)


def _execution_contract(
    initial: Study,
    admission: AuthoritySession,
) -> tuple[tuple[Capability, ...], tuple[Binding, ...]]:
    capabilities = tuple(
        Capability(name)
        for name in dict.fromkeys(
            obligation.capability
            for obligation in initial.proof.claims
            if obligation.capability is not None
        )
    )
    bindings = tuple(
        Binding(
            capability.name,
            admission.admit_document(
                Document(
                    "fixture.binding",
                    {"capability": capability.name},
                )
            ),
        )
        for capability in capabilities
    )
    return capabilities, bindings


def _foundation_document(
    task: Task,
    facts: dict[str, Evidence],
    admission: AuthoritySession,
    study: Study,
    brief: MetalensBrief,
    advice: tuple[Advice, ...],
    *,
    period_nm: int,
    height_nm: int,
) -> Document | None:
    """Build exact consultation grounds through their production owners."""

    if brief.cell_period_nm is not None and brief.atom_height_nm is not None:
        return None
    if task.claim == "material_binding":
        return fixture_material_binding(
            study,
            atom_index=_fixture_atom_index(brief),
        ).document()
    if task.claim == "period_domain":
        binding = _material_binding_from(facts, admission)
        return derive_period_domain(study, binding).document()
    if task.claim == "period_choice":
        domain = _period_domain_from(facts, admission)
        period_record = (
            None
            if brief.cell_period_nm is not None
            else _sole_advice(advice, PeriodAdvice)
        )
        choice = resolve_period_choice(
            study,
            domain,
            period_advice=period_record,
        )
        if not isinstance(choice, PeriodChoice):
            raise AssertionError(choice)
        return choice.document()
    if task.claim == "height_domain":
        binding = _material_binding_from(facts, admission)
        choice = _period_choice_from(facts, admission)
        if choice.period_nm != period_nm:
            raise AssertionError("fixture_period_choice_mismatch")
        return _recorded_height_domain(
            study,
            choice,
            binding,
            height_nm=height_nm,
        ).document()
    if task.claim == "phase_envelope":
        binding = _material_binding_from(facts, admission)
        domain = _height_domain_from(facts, admission)
        return estimate_phase_envelope(
            domain,
            OpticalContrast.from_binding(binding),
        ).document()
    return None


def _fixture_atom_index(brief: MetalensBrief) -> str:
    """Keep recorded forecasts representative of the named atom family."""

    return {
        "silicon": "3.5",
        "titanium dioxide": "2.4",
    }.get(brief.atom.material.family, "2.05")


def _recorded_height_domain(
    study: Study,
    choice: PeriodChoice,
    binding: MaterialBinding,
    *,
    height_nm: int,
) -> HeightDomain:
    """Record one exact fixture domain while preserving its chosen cell."""

    design = require_metalens_design(study)
    assert choice.evidence_reference is not None
    if not isinstance(study.brief, MetalensBrief):
        raise AssertionError("fixture_metalens_brief_required")
    step_nm = study.brief.dimension_step_nm
    if step_nm is None:
        raise AssertionError("fixture_dimension_step_missing")
    raw_feature_nm = Decimal(height_nm) / Decimal(design.aspect_limit)
    minimum_feature_nm = (
        int(
            (raw_feature_nm / Decimal(step_nm)).to_integral_value(
                rounding=ROUND_CEILING
            )
        )
        * step_nm
    )
    maximum_feature_nm = choice.period_nm - minimum_feature_nm
    candidate_count = (
        0
        if maximum_feature_nm < minimum_feature_nm
        else (maximum_feature_nm - minimum_feature_nm) // step_nm + 1
    )
    return HeightDomain(
        brief_identity=study.brief_identity,
        wavelength_nm=require_monochromatic_wavelength(design.operating_spectrum),
        period_nm=choice.period_nm,
        period_choice_reference=choice.evidence_reference,
        order_regime=choice.order_regime,
        heights_nm=(height_nm,),
        fabrication_ranges=(
            FabricationRange(
                height_nm=height_nm,
                minimum_feature_nm=minimum_feature_nm,
                maximum_feature_nm=maximum_feature_nm,
                candidate_count=candidate_count,
            ),
        ),
        aspect_limit=design.aspect_limit,
        dimension_step_nm=step_nm,
        atom=design.atom,
        substrate=design.substrate,
        material_binding_reference=binding.evidence_reference,
        material_sample_reference=binding.sample_reference,
    )


def _material_binding_from(
    facts: dict[str, Evidence],
    admission: AuthoritySession,
) -> MaterialBinding:
    reference = facts["material_binding"].reference
    return MaterialBinding.from_document(
        Document.from_bytes(admission.fetch(reference)),
        evidence_reference=reference,
    )


def _period_domain_from(
    facts: dict[str, Evidence],
    admission: AuthoritySession,
) -> PeriodDomain:
    reference = facts["period_domain"].reference
    return PeriodDomain.from_document(
        Document.from_bytes(admission.fetch(reference)),
        evidence_reference=reference,
    )


def _period_choice_from(
    facts: dict[str, Evidence],
    admission: AuthoritySession,
) -> PeriodChoice:
    reference = facts["period_choice"].reference
    return PeriodChoice.from_document(
        Document.from_bytes(admission.fetch(reference))
    ).bind_evidence(reference)


def _height_domain_from(
    facts: dict[str, Evidence],
    admission: AuthoritySession,
) -> HeightDomain:
    reference = facts["height_domain"].reference
    return HeightDomain.from_document(
        Document.from_bytes(admission.fetch(reference)),
        evidence_reference=reference,
    )


def _phase_envelope_from(
    facts: dict[str, Evidence],
    admission: AuthoritySession,
) -> PhaseEnvelope:
    reference = facts["phase_envelope"].reference
    return PhaseEnvelope.from_document(
        Document.from_bytes(admission.fetch(reference)),
        evidence_reference=reference,
    )


def _sole_advice(
    advice: tuple[Advice, ...],
    kind: type[AdviceValue],
) -> AdviceValue:
    matches = tuple(item for item in advice if isinstance(item, kind))
    if len(matches) != 1:
        raise AssertionError(f"fixture_advice_missing:{kind.__name__}")
    return matches[0]


def _fixture_recommended_height_nm(
    advice: tuple[Advice, ...],
    *,
    fallback_height_nm: int,
) -> int:
    recommendations = tuple(
        item.conclusion.height_nm
        for item in advice
        if isinstance(item, HeightAdvice)
        and isinstance(item.conclusion, HeightRecommendation)
    )
    if not recommendations:
        return fallback_height_nm
    if len(recommendations) != 1:
        raise AssertionError("fixture_height_advice_ambiguous")
    return recommendations[0]


def _fixture_advice(
    brief: MetalensBrief,
    evidence: tuple[Evidence, ...],
    advice: tuple[Advice, ...],
    admission: AuthoritySession,
    *,
    period_nm: int,
    height_nm: int,
) -> tuple[Advice, ...]:
    """
    Admit deterministic consultations without changing the blind brief.
    """

    facts = {fact.claim: fact for fact in evidence}
    known_types = {type(item) for item in advice}
    if (
        PeriodAdvice not in known_types
        and "period_domain" in facts
        and brief.cell_period_nm is None
    ):
        domain_reference = facts["period_domain"].reference
        domain = PeriodDomain.from_document(
            Document.from_bytes(admission.fetch(domain_reference)),
            evidence_reference=domain_reference,
        )
        period = fixture_period_advice(
            compile_metalens(brief),
            domain,
            period_nm=period_nm,
        )
        admission.admit_document(period.document())
        advice = (*advice, period)
    height_requires = {"height_domain"}
    if brief.control_strategy.value == "propagation phase":
        height_requires.add("phase_envelope")
    if (
        HeightAdvice not in known_types
        and height_requires <= set(facts)
        and brief.atom_height_nm is None
    ):
        domain_reference = facts["height_domain"].reference
        domain = HeightDomain.from_document(
            Document.from_bytes(admission.fetch(domain_reference)),
            evidence_reference=domain_reference,
        )
        envelope = None
        if "phase_envelope" in facts:
            envelope_reference = facts["phase_envelope"].reference
            envelope = PhaseEnvelope.from_document(
                Document.from_bytes(admission.fetch(envelope_reference)),
                evidence_reference=envelope_reference,
            )
        height = fixture_height_advice(
            brief,
            domain,
            envelope=envelope,
            height_nm=height_nm,
        )
        admission.admit_document(height.document())
        advice = (*advice, height)
    return advice


def _pointwise_evaluation_document(
    task: Task,
    facts: dict[str, Evidence],
) -> Document:
    if task.claim in {"field", "aplanatic_reference"}:
        return Document(FIELD_SCHEMA, {"recorded": task.claim})
    if task.claim == "focal_region":
        return Document(FOCAL_REGION_SCHEMA, {"recorded": True})
    if task.claim == "focus":
        return focus_document(
            focal_region_reference=facts["focal_region"].reference,
            focus=_focus(geometric=False),
        )
    return Document(task.schema, {"obligation": task.claim})


def _focal_comparison(
    focal_region_reference: Reference,
    ideal_field_reference: Reference,
    actual_binding_reference: Reference,
    ideal_binding_reference: Reference,
) -> FocalFieldComparison:
    return FocalFieldComparison(
        observed_field_reference=focal_region_reference,
        ideal_field_reference=ideal_field_reference,
        observed_binding_reference=actual_binding_reference,
        ideal_binding_reference=ideal_binding_reference,
        observed_method="qualified vector angular spectrum",
        ideal_method="qualified CZT Richards--Wolf",
        aligned_complex_error=0.1,
        unit_integral_intensity_error=0.05,
        observed_to_ideal_scale=0.9 + 0.1j,
        input_longitudinal_power_w=1,
        output_longitudinal_power_w=0.99,
    )


def _admit_reference_surface(
    admission: AuthoritySession,
    identity: str,
    requested_basis: RequestedInputBasis,
    *,
    period_nm: int,
) -> AdmittedReferenceSurface:
    source = admission.admit_document(
        Document("fixture.surface_source", {"identity": identity})
    )
    electric_x = numpy.ones((2, 2), dtype=numpy.complex128)
    electric_zero = numpy.zeros_like(electric_x)
    electric_x.setflags(write=False)
    electric_zero.setflags(write=False)
    response = ReferenceSurfaceResponse(
        Field(
            wavelength_m=800e-9,
            surface=PlaneSurface(
                600e-9,
                period_nm * 1e-9 / 2,
                (2, 2),
            ),
            frame=CoordinateFrame(),
            medium=Medium("air"),
            basis=ComponentBasis.CARTESIAN,
            electric_components=(
                FieldComponent("x", electric_x),
                FieldComponent("y", electric_zero),
                FieldComponent("z", electric_zero),
            ),
            source_references=(source,),
            incident_reference_power=1,
        ),
        requested_basis,
        "multi order",
        0.8,
    )
    electric, magnetic = admit_response_components(
        response,
        admission.admit_object,
    )
    document = reference_surface_document(
        response,
        electric,
        magnetic_references=magnetic,
    )
    reference = admission.admit_document(
        document,
        references=(
            source,
            *electric.values(),
            *magnetic.values(),
        ),
    )
    return AdmittedReferenceSurface(response, reference)


def _append_fact(
    evidence: tuple[Evidence, ...],
    task: Task,
    reference: Reference,
) -> tuple[Evidence, ...]:
    return (
        *evidence,
        Evidence(
            task_identity=task.identity,
            claim=task.claim,
            schema=task.schema,
            reference=reference,
            binding_reference=task.binding_reference,
            consultations=task.consultations,
        ),
    )


def _bind_design(
    admission: AuthoritySession,
    study: Study,
) -> tuple[BoundDocument, BoundDocument]:
    brief = brief_document(study.brief)
    brief_reference = admission.admit_document(brief)
    design = design_document(study, brief_reference)
    design_reference = admission.admit_document(
        design,
        references=(brief_reference,),
    )
    return (
        BoundDocument(brief_reference, brief),
        BoundDocument(design_reference, design),
    )


def _bind_recorded_study(
    admission: AuthoritySession,
    study: Study,
    *,
    brief: BoundDocument | None = None,
    design: BoundDocument | None = None,
) -> ResultClosure:
    if (brief is None) != (design is None):
        raise AssertionError("fixture closure basis incomplete")
    if brief is None or design is None:
        brief, design = _bind_design(admission, study)
    compiled = study_document(
        study,
        brief.reference,
        design.reference,
    )
    references = tuple(
        dict.fromkeys(
            (
                brief.reference,
                design.reference,
                *study.direct_references(),
            )
        )
    )
    study_reference = admission.admit_document(
        compiled,
        references=references,
    )
    return ResultClosure.bind(
        study,
        brief=brief,
        design=design,
        study=BoundDocument(study_reference, compiled),
    )


def _evaluation_document(
    task: Task,
    facts: dict[str, Evidence],
    *,
    geometric: bool,
) -> Document:
    if task.claim == "field":
        return Document(FIELD_SCHEMA, {"recorded": True})
    if task.claim == "focal_region":
        return Document(FOCAL_REGION_SCHEMA, {"recorded": True})
    if task.claim == "focus":
        focus = _focus(geometric=geometric)
        return focus_document(
            focal_region_reference=facts["focal_region"].reference,
            focus=focus,
        )
    return Document(task.schema, {"obligation": task.claim})


def _propagation_responses(
    admission: AuthoritySession,
    *,
    levels: int,
    binding_reference: Reference,
    height_reference: Reference,
    period_nm: int = 200,
    height_nm: int = 600,
    atom_material: str = "silicon nitride",
    substrate_material: str = "silica",
) -> tuple[PropagationResponse, ...]:
    responses = []
    atom = Material(atom_material, "solver native")
    substrate = Material(substrate_material, "solver native")
    for level in range(levels):
        phase = FULL_TURN * Decimal(level) / Decimal(levels)
        source = admission.admit_document(
            Document("fixture.propagation_response", {"level": level}),
        )
        cell = Cell(
            identity=f"cell-{levels:02d}-{level:02d}",
            atom=atom,
            substrate=substrate,
            period_nm=period_nm,
            height_nm=height_nm,
            geometry=Circle(
                max(10, period_nm // 8) + level * max(1, period_nm // (4 * levels))
            ),
            source=source,
        )
        responses.append(
            PropagationResponse(
                binding_reference=binding_reference,
                height_choice_reference=height_reference,
                phase_planes="substrate-to-superstrate",
                cell=cell,
                transmission_real=Decimal(str(math.cos(float(phase)))),
                transmission_imaginary=Decimal(str(math.sin(float(phase)))),
                realized_phase=phase,
                useful_power=Decimal("0.8"),
                leakage_power=Decimal("0.05"),
                solver_status="complete",
                warnings=(),
                is_construction_valid=True,
                execution_origin=EvidenceOrigin.SYNTHETIC,
                source_reference=source,
            )
        )
    return tuple(responses)


def _propagation_library(
    authority: Authority,
    facts: dict[str, Evidence],
) -> PropagationCellLibrary:
    reference = facts["cell_library"].reference
    return PropagationCellLibrary.from_document(
        Document.from_bytes(authority.fetch(reference)),
        evidence_reference=reference,
        binding_reference=_required(facts["periodic_transmission"].binding_reference),
        height_choice_reference=facts["height_choice"].reference,
    )


def _cell_choice(
    admission: AuthoritySession,
    facts: dict[str, Evidence],
    state: dict[str, object],
    *,
    period_nm: int = 200,
    height_nm: int = 600,
    atom_material: str = "silicon nitride",
    substrate_material: str = "silica",
    geometry: Geometry | None = None,
) -> CellChoice:
    source_x = admission.admit_document(
        Document("fixture.jones_response", {"basis": "x"}),
    )
    source_y = admission.admit_document(
        Document("fixture.jones_response", {"basis": "y"}),
    )
    zero = ComplexCoefficient(Decimal(0), Decimal(0))
    one = ComplexCoefficient(Decimal(1), Decimal(0))
    cell = Cell(
        identity="geometric-cell",
        atom=Material(atom_material, "solver native"),
        substrate=Material(substrate_material, "solver native"),
        period_nm=period_nm,
        height_nm=height_nm,
        geometry=(
            Rectangle(
                max(10, period_nm // 4),
                max(20, period_nm // 2),
            )
            if geometry is None
            else geometry
        ),
        source=source_x,
    )
    return CellChoice(
        cell=cell,
        jones=JonesResponse(one, zero, zero, one),
        converted=one,
        converted_phase=Decimal(0),
        retained=zero,
        retained_phase=Decimal(0),
        useful_power=Decimal("0.8"),
        leakage_power=Decimal("0.1"),
        loss=Decimal("-0.7"),
        binding_reference=_required(facts["jones_library"].binding_reference),
        height_domain_reference=facts["height_domain"].reference,
        height_basis=HeightConstraintBasis(),
        height_choice_reference=facts["height_choice"].reference,
        library_reference=facts["jones_library"].reference,
        convention=_convention(state),
        convention_reference=facts["polarization_convention"].reference,
        source_references=(source_x, source_y),
        cautions=(),
        execution_origin=EvidenceOrigin.SYNTHETIC,
        selection_contract=LEGACY_PB_RESPONSE_RANKING,
    )


def _focus(*, geometric: bool) -> Focus:
    axial_distances = (1.6e-6, 2e-6, 2.4e-6)
    axial_peaks = (0.2, 1.0, 0.2)
    half = HalfMaximum(1.9e-6, 2.1e-6, 0.2e-6, True)
    leakage = (
        Leakage(
            channel="retained",
            role="leakage",
            observed_distance_m=2e-6,
            transmitted_fraction=0.1,
            peak_intensity=0.1,
            integrated_intensity=0.2,
            axial_distances_m=axial_distances,
            axial_peak_intensities=(0.1, 0.2, 0.1),
        )
        if geometric
        else None
    )
    return Focus(
        expected_focus_m=2e-6,
        found_focus_m=2e-6,
        focal_shift_m=0.0,
        x_half_maximum=half,
        y_half_maximum=half,
        depth_of_focus=half,
        transmitted_fraction=0.8,
        focused_fraction=0.7,
        focus_efficiency=0.56,
        peak_intensity=1.0,
        airy_radius_m=1e-6,
        is_focus_bracketed=True,
        observed_components=(("left",) if geometric else ("x",)),
        convergence=FocusConvergence(3, 0.4e-6, False),
        axial_distances_m=axial_distances,
        axial_peak_intensities=axial_peaks,
        leakage=leakage,
    )


def _required(reference: Reference | None) -> Reference:
    if reference is None:
        raise AssertionError("fixture binding missing")
    return reference


def _choice(state: dict[str, object]) -> CellChoice:
    value = state["choice"]
    if not isinstance(value, CellChoice):
        raise AssertionError("fixture cell choice missing")
    return value


def _orientations(state: dict[str, object]) -> OrientationRelation:
    value = state["orientations"]
    if not isinstance(value, OrientationRelation):
        raise AssertionError("fixture orientations missing")
    return value


def _orientation_set(state: dict[str, object]) -> OrientationSet:
    value = state["orientation_set"]
    if not isinstance(value, OrientationSet):
        raise AssertionError("fixture orientation set missing")
    return value


def _convention(state: dict[str, object]) -> PolarizationConvention:
    value = state["convention"]
    if not isinstance(value, PolarizationConvention):
        raise AssertionError("fixture convention missing")
    return value
