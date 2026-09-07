from __future__ import annotations

from ...authority import Document, Reference
from ...authority.reference import reference_for
from ...authority.session import AuthoritySession
from ...field.angular_spectrum import (
    FieldMemoryUnavailable,
    observe_angular_spectrum,
    qualify_angular_spectrum,
)
from ...field.debye_qualification import (
    aplanatic_reference_binding,
    qualify_aplanatic_reference,
    qualify_czt_debye,
    qualify_fft_debye,
)
from ...field.fast_debye import observe_czt_debye, observe_fft_debye
from ...field.vector_angular_spectrum import (
    observe_vector_angular_spectrum,
    qualify_vector_angular_spectrum,
    vector_angular_spectrum_binding,
)
from ...materials import (
    MaterialObservationRequest,
    MaterialResponse,
    MaterialUnavailable,
)
from ..brief import Brief
from ..consultation import ConsultationAnswer, ConsultationRequest
from ..periodic_response import PeriodicResponse, PeriodicResponseKind
from ..study import (
    Advice,
    Binding,
    Capability,
    Evidence,
    Finding,
    FindingKind,
    Study,
    Task,
)
from . import (
    _aplanatic_reference,
    _continuous_achromatic,
    field_execution,
    geometric_execution,
    propagation_execution,
)
from . import aperture as aperture_science
from .brief import ControlStrategy, MetalensBrief, require_monochromatic_wavelength
from .compiler import compile_metalens, restore_metalens_inputs
from .consultation import (
    accept_height_consultation_answer,
    accept_period_consultation_answer,
    form_height_consultation_request,
    form_period_consultation_request,
)
from .design import TargetPhase, require_metalens_design
from .evidence import MetalensEvidence
from .geometric_phase import PolarizationConvention
from .height import (
    HeightChoice,
    HeightDomain,
    derive_height_domain,
    resolve_height_choice,
)
from .height_advice import HeightAdvice
from .material import (
    BoundMaterial,
    MaterialBinding,
    validate_material_observation,
)
from .period import (
    PeriodChoice,
    PeriodDomain,
    derive_period_domain,
    resolve_period_choice,
)
from .period_advice import PeriodAdvice
from .propagation_envelope import (
    OpticalContrast,
    PhaseEnvelope,
    estimate_phase_envelope,
)


def _admit_binding(
    session: AuthoritySession,
    capability: str,
    operations: tuple[str, ...],
) -> Reference:
    """
    Admit one local implementation binding at composition time.
    """

    return session.admit_document(
        Document(
            f"metacraft.binding.{capability}",
            {
                "capability": capability,
                "operations": list(operations),
            },
        )
    )


def _assign_aperture(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    claims = {claim.name for claim in study.proof.claims}
    if "cell_surface_table" in claims:
        return propagation_execution.assign_pointwise_aperture(
            evidence,
            study,
            task,
        )
    if "geometric_surface_transform" in claims:
        return geometric_execution.assign_pointwise_aperture(
            evidence,
            study,
            task,
        )
    if (
        require_metalens_design(study).control_strategy
        is ControlStrategy.PROPAGATION_PHASE
    ):
        return propagation_execution.assign_aperture(
            evidence,
            study,
            task,
        )
    if (
        require_metalens_design(study).control_strategy
        is ControlStrategy.GEOMETRIC_PHASE
    ):
        return geometric_execution.assign_aperture(
            evidence,
            study,
            task,
        )
    return study


def _form_field(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    claims = {fact.claim for fact in study.evidence}
    if "cell_surface_table" in claims:
        return propagation_execution.form_pointwise_field(
            evidence,
            study,
            task,
        )
    if "geometric_surface_transform" in claims:
        return geometric_execution.form_pointwise_field(
            evidence,
            study,
            task,
        )
    if (
        require_metalens_design(study).control_strategy
        is ControlStrategy.PROPAGATION_PHASE
    ):
        return propagation_execution.form_field(
            evidence,
            study,
            task,
        )
    if (
        require_metalens_design(study).control_strategy
        is ControlStrategy.GEOMETRIC_PHASE
    ):
        return geometric_execution.form_field(
            evidence,
            study,
            task,
        )
    return study


def _propagate_field(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    if any(
        binding.capability == "vector_angular_spectrum_propagation"
        and binding.reference == task.binding_reference
        for binding in study.bindings
    ):
        return field_execution.admit_vector_focal_region(
            evidence,
            study,
            task,
        )
    try:
        if (
            require_metalens_design(study).control_strategy
            is ControlStrategy.PROPAGATION_PHASE
        ):
            return propagation_execution.propagate_field(
                evidence,
                study,
                task,
            )
        if (
            require_metalens_design(study).control_strategy
            is ControlStrategy.GEOMETRIC_PHASE
        ):
            return geometric_execution.propagate_field(
                evidence,
                study,
                task,
            )
    except FieldMemoryUnavailable:
        return evidence.with_refusal(
            study,
            task.claim,
            "field_memory_unavailable",
        )
    return study


def _required_reference(
    reference: Reference | None,
    reason: str,
) -> Reference:
    if reference is None:
        raise RuntimeError(reason)
    return reference


def _evaluate_focus(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    if (
        task.binding_reference is not None
        and any(
            binding.capability == "vector_angular_spectrum_propagation"
            for binding in study.bindings
        )
        and any(fact.claim == "focal_comparison" for fact in study.evidence)
    ):
        return field_execution.admit_vector_focus(
            evidence,
            study,
            task,
        )
    if (
        require_metalens_design(study).control_strategy
        is ControlStrategy.PROPAGATION_PHASE
    ):
        return propagation_execution.evaluate_focus(
            evidence,
            study,
            task,
        )
    if (
        require_metalens_design(study).control_strategy
        is ControlStrategy.GEOMETRIC_PHASE
    ):
        return geometric_execution.evaluate_focus(
            evidence,
            study,
            task,
        )
    return study


def _derive_target_phase(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    document = TargetPhase.from_design(require_metalens_design(study)).document()
    return evidence.with_fact(
        study,
        task,
        evidence.admit_task(task, document),
    )


def _bind_material(
    evidence: MetalensEvidence,
    materials: MaterialResponse,
    study: Study,
    task: Task,
) -> Study:
    brief = _require_metalens(study.brief)
    wavelength_nm = require_monochromatic_wavelength(brief.operating_spectrum)
    request = MaterialObservationRequest(
        families=(
            brief.atom.material.family,
            brief.substrate.family,
        ),
        wavelength_nm=wavelength_nm,
    )
    outcome = materials.observe(request)
    if isinstance(outcome, MaterialUnavailable):
        if outcome.request_identity != request.identity:
            raise RuntimeError("material_outcome_request_mismatch")
        suffix = f":{outcome.native_name}" if outcome.native_name is not None else ""
        return evidence.with_unavailable(
            study,
            task,
            (
                "material_unavailable:"
                f"{outcome.reason.value}:{outcome.family}{suffix}"
            ),
        )
    validate_material_observation(
        request,
        outcome,
        expected_binding_reference=_required_reference(
            task.binding_reference,
            "task_binding_missing",
        ),
    )
    for selection in outcome.selections:
        evidence.observe_admitted(selection.reference)
    evidence.observe_admitted(outcome.solver_binding_reference)
    evidence.observe_admitted(outcome.sample_reference)
    by_family = {material.family: material for material in outcome.materials}
    atom = by_family[brief.atom.material.family]
    substrate = by_family[brief.substrate.family]
    binding = MaterialBinding(
        brief_identity=study.brief_identity,
        wavelength_nm=wavelength_nm,
        atom=BoundMaterial(
            family=atom.family,
            source=brief.atom.material.source,
            native_name=atom.native_name,
            refractive_index=atom.refractive_index,
            extinction_coefficient=atom.extinction_coefficient,
        ),
        substrate=BoundMaterial(
            family=substrate.family,
            source=brief.substrate.source,
            native_name=substrate.native_name,
            refractive_index=substrate.refractive_index,
            extinction_coefficient=substrate.extinction_coefficient,
        ),
        solver_binding_reference=outcome.solver_binding_reference,
        sample_reference=outcome.sample_reference,
        evidence_reference=outcome.solver_binding_reference,
    )
    reference = evidence.admit_task(
        task,
        binding.document(),
        sources=binding.references(),
    )
    return evidence.with_fact(study, task, reference)


def _derive_period_domain(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    binding = evidence.material_binding(study)
    domain = derive_period_domain(study, binding)
    reference = evidence.admit_task(
        task,
        domain.document(),
        sources=(binding.evidence_reference, binding.sample_reference),
    )
    return evidence.with_fact(study, task, reference)


def _resolve_period_choice(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    domain = evidence.period_domain(study)
    period_records = tuple(
        item for item in study.advice if isinstance(item, PeriodAdvice)
    )
    brief = _require_metalens(study.brief)
    period_advice = (
        None
        if brief.cell_period_nm is not None
        else (period_records[0] if len(period_records) == 1 else None)
    )
    choice = resolve_period_choice(
        study,
        domain,
        period_advice=period_advice,
    )
    if isinstance(choice, Finding):
        return evidence.with_finding(study, choice)
    reference = evidence.admit_task(
        task,
        choice.document(),
        sources=choice.references(),
    )
    return evidence.with_fact(study, task, reference)


def _derive_height_domain(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    binding = evidence.material_binding(study)
    period_choice = evidence.period_choice(study)
    domain = derive_height_domain(study, period_choice, binding)
    if isinstance(domain, Finding):
        return evidence.with_finding(study, domain)
    assert period_choice.evidence_reference is not None
    reference = evidence.admit_task(
        task,
        domain.document(),
        sources=(
            binding.evidence_reference,
            binding.sample_reference,
            period_choice.evidence_reference,
        ),
    )
    return evidence.with_fact(study, task, reference)


def _resolve_physical_lattice(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    period_choice = evidence.period_choice(study)
    period_reference = evidence.fact(study, "period_choice").reference
    resolved = aperture_science.resolve_lattice(
        require_metalens_design(study),
        spacing_nm=period_choice.period_nm,
        spacing_source_reference=period_reference,
    )
    if isinstance(resolved, aperture_science.ApertureIntentMismatch):
        return evidence.with_finding(
            study,
            Finding(
                claim=task.claim,
                kind=FindingKind.REFUSAL,
                needs=(resolved.reason,),
                record_references=(period_reference,),
            ),
        )
    reference = evidence.admit_task(
        task,
        resolved.document(),
        sources=(period_reference,),
    )
    return evidence.with_fact(study, task, reference)


def _estimate_phase_envelope(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    binding = evidence.material_binding(study)
    domain = evidence.height_domain(study)
    envelope = estimate_phase_envelope(
        domain,
        OpticalContrast.from_binding(binding),
    )
    reference = evidence.admit_task(
        task,
        envelope.document(),
        sources=tuple(
            dict.fromkeys(
                (
                    *task.prerequisite_evidence,
                    *envelope.source_references,
                )
            )
        ),
    )
    return evidence.with_fact(study, task, reference)


def _resolve_height_choice(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
) -> Study:
    domain = evidence.height_domain(study)
    advice = tuple(item for item in study.advice if isinstance(item, HeightAdvice))
    recommendation = None if not advice else advice[0]
    if len(advice) > 1:
        raise ValueError("height_advice_duplicate")
    choice = resolve_height_choice(
        study,
        domain,
        recommendation,
        envelope=(
            _restore_phase_envelope(evidence, study)
            if (
                require_metalens_design(study).control_strategy
                is ControlStrategy.PROPAGATION_PHASE
            )
            else None
        ),
    )
    if isinstance(choice, Finding):
        return evidence.with_finding(study, choice)
    reference = evidence.admit_task(
        task,
        choice.document(),
        sources=choice.references(),
    )
    return evidence.with_fact(study, task, reference)


def _admit_consultation(
    evidence: MetalensEvidence,
    document: Document,
    *,
    sources: tuple[Reference, ...],
) -> Reference:
    """
    Admit one consultation before exposing its immutable advice record.
    """

    expected = reference_for(document.to_bytes())
    admitted = evidence.admit_document(
        document,
        sources=sources,
    )
    if admitted != expected:
        raise RuntimeError("advice_admission_reference_mismatch")
    return admitted


def _require_metalens(brief: Brief) -> MetalensBrief:
    if not isinstance(brief, MetalensBrief):
        raise RuntimeError("local_metalens_required")
    return brief


def _restore_phase_envelope(
    evidence: MetalensEvidence,
    study: Study,
) -> PhaseEnvelope:
    fact = evidence.fact(study, "phase_envelope")
    return PhaseEnvelope.from_document(
        Document.from_bytes(evidence.fetch(fact.reference)),
        evidence_reference=fact.reference,
    )


def required_metalens_consultation(
    study: Study,
    *,
    session: AuthoritySession,
) -> ConsultationRequest | None:
    """
    Derive the first exact consultation request from one admitted Study.
    """

    evidence = MetalensEvidence(session)
    if any(
        finding.claim == "period_choice"
        and finding.kind is FindingKind.ADVICE
        and finding.needs == ("period",)
        for finding in study.findings
    ):
        return form_period_consultation_request(
            _require_metalens(study.brief),
            evidence.period_domain(study),
        )
    if any(
        finding.claim == "height_choice"
        and finding.kind is FindingKind.ADVICE
        and finding.needs == ("height",)
        for finding in study.findings
    ):
        domain = evidence.height_domain(study)
        envelope = (
            _restore_phase_envelope(evidence, study)
            if (
                require_metalens_design(study).control_strategy
                is ControlStrategy.PROPAGATION_PHASE
            )
            else None
        )
        return form_height_consultation_request(
            _require_metalens(study.brief),
            domain,
            envelope=envelope,
        )
    return None


def accept_metalens_consultation(
    study: Study,
    answer: ConsultationAnswer,
    *,
    session: AuthoritySession,
) -> Study:
    """
    Validate, admit, and retain the answer to this Study's exact request.
    """

    evidence = MetalensEvidence(session)
    request = required_metalens_consultation(study, session=session)
    if request is None:
        raise ValueError("consultation_answer_not_required")
    if request.question_kind.value == "period":
        domain = evidence.period_domain(study)
        advice = accept_period_consultation_answer(
            _require_metalens(study.brief),
            domain,
            request,
            answer,
        )
        assert domain.evidence_reference is not None
        sources = (domain.evidence_reference,)
    else:
        domain = evidence.height_domain(study)
        envelope = (
            _restore_phase_envelope(evidence, study)
            if (
                require_metalens_design(study).control_strategy
                is ControlStrategy.PROPAGATION_PHASE
            )
            else None
        )
        advice = accept_height_consultation_answer(
            _require_metalens(study.brief),
            domain,
            request,
            answer,
            envelope=envelope,
        )
        assert domain.evidence_reference is not None
        sources = tuple(
            reference
            for reference in (
                domain.evidence_reference,
                None if envelope is None else envelope.evidence_reference,
            )
            if reference is not None
        )
    _admit_consultation(evidence, advice.document(), sources=sources)
    return evidence.recompile(study, advice=(*study.advice, advice))


def prepare_metalens_study(
    study: Study,
    *,
    session: AuthoritySession,
    periodic_response: PeriodicResponse | None,
    materials: MaterialResponse | None,
) -> Study:
    """
    Bind one fresh metalens Study to exact local and response realizations.

    The generic lifecycle chooses the aim; this aim-owned composition owns
    every metalens capability name and operation-bearing binding document.
    """

    if _continuous_achromatic.owns(study):
        return _continuous_achromatic.prepare(
            study,
            evidence=MetalensEvidence(session),
            session=session,
            periodic_response=periodic_response,
            materials=materials,
        )

    required = {
        claim.capability for claim in study.proof.claims if claim.capability is not None
    }
    selected_by_capability = {
        binding.capability: binding
        for binding in study.bindings
        if binding.capability in required
    }
    missing = required - set(selected_by_capability)
    if not missing:
        return study

    claim_capabilities = {
        claim.name: claim.capability
        for claim in study.proof.claims
        if claim.capability is not None
    }
    required_operations: dict[str, set[str]] = {}
    for choice in study.proof.route.choices:
        capability = claim_capabilities.get(choice.claim)
        if capability is not None:
            required_operations.setdefault(capability, set()).add(choice.method)

    bindings: list[Binding] = []
    local_operations = {
        "fabrication_constraint": (
            "derive_period_domain",
            "derive_height_domain",
        ),
        "deterministic_selection": (
            "assign_aperture",
            "choose_cell",
            "resolve_period_choice",
            "resolve_height_choice",
        ),
        "cell_library": ("form_cell_library",),
        "focus_evaluation": ("evaluate_focus",),
        "polarization_convention": ("establish_polarization_convention",),
    }
    for capability in sorted(missing & set(local_operations)):
        if not (
            required_operations.get(capability, set())
            & set(local_operations[capability])
        ):
            continue
        bindings.append(
            Binding(
                capability,
                _admit_binding(
                    session,
                    capability,
                    local_operations[capability],
                ),
            )
        )
    if (
        "angular_spectrum_propagation" in missing
        and "propagate_field"
        in required_operations.get("angular_spectrum_propagation", set())
    ):
        propagation = observe_angular_spectrum()
        propagation_qualification = qualify_angular_spectrum(propagation)
    else:
        propagation = None
        propagation_qualification = None
    if (
        propagation is not None
        and propagation_qualification is not None
        and propagation_qualification.is_qualified
    ):
        bindings.append(
            Binding(
                "angular_spectrum_propagation",
                session.admit_document(
                    Document(
                        "metacraft.binding.angular_spectrum_propagation",
                        {
                            "operations": ["propagate_field"],
                            "qualification": (propagation_qualification.as_mapping()),
                            "qualified": True,
                            "realization": propagation.as_mapping(),
                        },
                    )
                ),
            )
        )
    if (
        "vector_angular_spectrum_propagation" in missing
        and "propagate_field"
        in required_operations.get("vector_angular_spectrum_propagation", set())
    ):
        vector_qualification = qualify_vector_angular_spectrum(
            observe_vector_angular_spectrum()
        )
        if vector_qualification.is_qualified:
            bindings.append(
                Binding(
                    "vector_angular_spectrum_propagation",
                    session.admit_document(
                        vector_angular_spectrum_binding(vector_qualification)
                    ),
                )
            )
    if (
        "aplanatic_reference_formation" in missing
        and "form_aplanatic_reference"
        in required_operations.get("aplanatic_reference_formation", set())
    ):
        fft_qualification = qualify_fft_debye(observe_fft_debye())
        czt_qualification = qualify_czt_debye(observe_czt_debye())
        if fft_qualification.is_qualified and czt_qualification.is_qualified:
            fft_reference = session.admit_document(fft_qualification.document())
            czt_reference = session.admit_document(czt_qualification.document())
            joint_qualification = qualify_aplanatic_reference(
                fft_qualification,
                czt_qualification,
                fft_qualification_reference=fft_reference,
                czt_qualification_reference=czt_reference,
            )
            if joint_qualification.is_qualified:
                joint_reference = session.admit_document(
                    joint_qualification.document(),
                    references=(fft_reference, czt_reference),
                )
                bindings.append(
                    Binding(
                        "aplanatic_reference_formation",
                        session.admit_document(
                            aplanatic_reference_binding(
                                joint_qualification,
                                joint_qualification_reference=joint_reference,
                            ),
                            references=(
                                fft_reference,
                                czt_reference,
                                joint_reference,
                            ),
                        ),
                    )
                )
    periodic_missing = missing & {kind.value for kind in PeriodicResponseKind}
    if periodic_missing and periodic_response is not None:
        response_context = periodic_response.context
        session.observe_admitted(response_context.binding_reference)
        bindings.extend(
            Binding(
                kind.value,
                response_context.binding_reference,
                response_context.capacity_scope,
            )
            for kind in response_context.response_kinds
            if kind.value in periodic_missing
        )
    if "optical_material" in missing and materials is not None:
        material_context = materials.context
        session.observe_admitted(material_context.binding_reference)
        bindings.append(
            Binding(
                "optical_material",
                material_context.binding_reference,
                material_context.capacity_scope,
            )
        )
    qualified_by_capability = {
        binding.capability: binding
        for binding in bindings
        if binding.capability in required
    }
    for capability, binding in qualified_by_capability.items():
        selected_by_capability.setdefault(capability, binding)
    if not qualified_by_capability:
        return study
    selected_bindings = tuple(
        selected_by_capability[name] for name in sorted(selected_by_capability)
    )
    capabilities = tuple(Capability(name) for name in sorted(selected_by_capability))
    return MetalensEvidence(session).recompile(
        study,
        capabilities=capabilities,
        bindings=selected_bindings,
    )


def advance_metalens(
    study: Study,
    *,
    session: AuthoritySession,
    periodic_response: PeriodicResponse | None,
    materials: MaterialResponse | None,
) -> tuple[Study, ...]:
    """
    Advance one immutable metalens Study by at most one scientific operation.

    Frontier ownership, checkpointing, and result admission stay in the
    application-level conduct module. This aim-owned operation sees only one
    Study and explicit external seams.
    """

    evidence = MetalensEvidence(session)
    waiting_study: Study | None = None
    if not study.ready_tasks:
        retrying = _retry_waiting_finding(evidence, study)
        if retrying is not None:
            waiting_study = study
            study = retrying
    if not study.ready_tasks:
        return ()
    task = study.ready_tasks[0]
    evolved = _advance_task(
        evidence,
        study,
        task,
        periodic_response=periodic_response,
        materials=materials,
    )
    branches = evolved if isinstance(evolved, tuple) else (evolved,)
    if waiting_study is not None:
        waiting_claims = {
            finding.claim
            for finding in waiting_study.findings
            if finding.kind is FindingKind.UNAVAILABLE
        }
        if not any(
            any(fact.claim in waiting_claims for fact in branch.evidence)
            for branch in branches
        ):
            return ()
    return branches


def _advance_task(
    evidence: MetalensEvidence,
    study: Study,
    task: Task,
    *,
    periodic_response: PeriodicResponse | None,
    materials: MaterialResponse | None,
) -> Study | tuple[Study, ...]:
    """
    Bind the closed metalens method vocabulary without a registry.
    """

    if _continuous_achromatic.owns(study):
        return _continuous_achromatic.advance(
            evidence,
            study,
            task,
            periodic_response=periodic_response,
            materials=materials,
        )

    match task.method:
        case "assign_aperture":
            return _assign_aperture(evidence, study, task)
        case "bind_material":
            if materials is None:
                return study
            return _bind_material(
                evidence,
                materials,
                study,
                task,
            )
        case "choose_cell":
            return geometric_execution.choose_cell(evidence, study, task)
        case "resolve_height_choice":
            return _resolve_height_choice(evidence, study, task)
        case "resolve_period_choice":
            return _resolve_period_choice(evidence, study, task)
        case "resolve_physical_lattice":
            return _resolve_physical_lattice(evidence, study, task)
        case "derive_height_domain":
            return _derive_height_domain(evidence, study, task)
        case "derive_orientations":
            return geometric_execution.derive_orientation_relation(
                evidence,
                study,
                task,
            )
        case "derive_period_domain":
            return _derive_period_domain(evidence, study, task)
        case "derive_target_phase":
            return _derive_target_phase(evidence, study, task)
        case "establish_polarization_convention":
            return geometric_execution.establish_polarization_convention(
                evidence,
                study,
                task,
            )
        case "evaluate_focus":
            return _evaluate_focus(evidence, study, task)
        case "estimate_phase_envelope":
            return _estimate_phase_envelope(evidence, study, task)
        case "form_aplanatic_reference":
            return _aplanatic_reference.admit_aplanatic_reference(
                evidence,
                study,
                task,
            )
        case "form_cell_library":
            return propagation_execution.form_cell_library(evidence, study, task)
        case "form_field":
            return _form_field(evidence, study, task)
        case "form_orientation_set":
            return geometric_execution.form_orientation_set(
                evidence,
                study,
                task,
            )
        case "form_phase_set":
            return propagation_execution.form_phase_set(evidence, study, task)
        case "observe_periodic_polarization":
            if periodic_response is None:
                return study
            return geometric_execution.observe_periodic_polarization(
                evidence,
                periodic_response,
                study,
                task,
            )
        case "gather_cell_surfaces":
            return propagation_execution.gather_cell_surfaces(
                evidence,
                study,
                task,
            )
        case "gather_geometric_surface_transform":
            return geometric_execution.gather_geometric_surface_transform(
                evidence,
                study,
                task,
            )
        case "observe_periodic_transmission":
            if periodic_response is None:
                return study
            return propagation_execution.observe_periodic_transmission(
                evidence,
                periodic_response,
                study,
                task,
            )
        case "propagate_field":
            return _propagate_field(evidence, study, task)
        case "compare_focal_field":
            return field_execution.admit_focal_field_comparison(
                evidence,
                study,
                task,
            )
        case _:
            raise RuntimeError(f"method_unbound:{task.method}")


def _retry_waiting_finding(
    evidence: MetalensEvidence,
    study: Study,
) -> Study | None:
    _advice, reported = restore_metalens_inputs(study)
    retryable = tuple(
        finding for finding in reported if finding.kind is FindingKind.UNAVAILABLE
    )
    if not retryable:
        return None
    retryable_claims = {finding.claim for finding in retryable}
    return evidence.recompile(
        study,
        reported_findings=tuple(
            finding for finding in reported if finding.claim not in retryable_claims
        ),
    )
