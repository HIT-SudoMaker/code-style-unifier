from __future__ import annotations

from dataclasses import replace
from decimal import ROUND_CEILING, Decimal
import hashlib

from metacraft.authority.protocol import Reference
from metacraft.authority.reference import reference_for
from metacraft.science.consultation import (
    ConsultationAnswer,
    EvidenceRequired,
    Recommendation,
    ResearchMode,
)
from metacraft.science.metalens.consultation import (
    accept_height_consultation_answer,
    accept_period_consultation_answer,
    form_height_consultation_request,
    form_period_consultation_request,
)
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.brief import require_monochromatic_wavelength
from metacraft.science.metalens.design import require_metalens_design
from metacraft.science.metalens.height import (
    HeightChoice,
    HeightConstraintBasis,
    HeightDomain,
    derive_height_domain,
)
from metacraft.science.metalens.material import (
    BoundMaterial,
    MaterialBinding,
)
from metacraft.science.metalens.period import (
    PeriodAdviceBasis,
    PeriodConstraintBasis,
    PeriodChoice,
    PeriodDomain,
    derive_period_domain,
    derive_period_limits,
)
from metacraft.science.metalens.period_advice import PeriodAdvice
from metacraft.science.metalens.height_advice import HeightAdvice
from metacraft.science.metalens.propagation_envelope import (
    OpticalContrast,
    PhaseEnvelope,
    estimate_phase_envelope,
)
from metacraft.science.study import (
    Binding,
    Capability,
    Evidence,
    Study,
)


def evidence_fact_for(
    brief,
    obligation: str,
    reference,
    *,
    advice=(),
    evidence=(),
    capabilities=(),
    bindings=(),
) -> Evidence:
    """
    Build one Evidence with the task_identity the compiler will recompute.

    Pre-compiles the brief with the same inputs to obtain the ready task for
    ``obligation``, then attaches the supplied reference. Suitable for tests
    that admit evidence for obligations whose prerequisites are already met.
    """

    pre = compile_metalens(
        brief,
        advice=advice,
        evidence=evidence,
        capabilities=capabilities,
        bindings=bindings,
    )
    matching = tuple(task for task in pre.ready_tasks if task.claim == obligation)
    if len(matching) != 1:
        raise RuntimeError(f"obligation_not_ready:{obligation}")
    task = matching[0]
    return Evidence(
        task_identity=task.identity,
        claim=obligation,
        schema=task.schema,
        reference=reference,
        binding_reference=task.binding_reference,
        consultations=task.consultations,
    )


def compile_with_facts(
    brief,
    references: dict,
    *,
    advice=(),
    capabilities=(),
    bindings=(),
    extra_evidence=(),
) -> tuple:
    """
    Iteratively compile one brief while admitting references as evidence.

    For each obligation in proof order, the next ready task is paired with
    its supplied reference and added to evidence; the brief is recompiled
    so that downstream task identities see the prerequisite references.
    Returns the final compiled Study and the constructed facts by name.
    """

    facts: dict = {}
    pre_evidence = tuple(extra_evidence)
    while True:
        study = compile_metalens(
            brief,
            advice=advice,
            evidence=(*pre_evidence, *facts.values()),
            capabilities=capabilities,
            bindings=bindings,
        )
        next_task = None
        for task in study.ready_tasks:
            if task.claim in references and task.claim not in facts:
                next_task = task
                break
        if next_task is None:
            return study, facts
        facts[next_task.claim] = Evidence(
            task_identity=next_task.identity,
            claim=next_task.claim,
            schema=next_task.schema,
            reference=references[next_task.claim],
            binding_reference=next_task.binding_reference,
            consultations=next_task.consultations,
        )


def material_binding(
    study: Study,
    *,
    atom_index: str = "2.05",
    substrate_index: str = "1.48",
) -> MaterialBinding:
    """
    Build one byte-exact solver-native material fixture.
    """

    design = require_metalens_design(study)
    provisional = MaterialBinding(
        brief_identity=study.brief_identity,
        wavelength_nm=require_monochromatic_wavelength(design.operating_spectrum),
        atom=BoundMaterial(
            family=design.atom.material.family,
            source=design.atom.material.source,
            native_name="fixture atom",
            refractive_index=Decimal(atom_index),
            extinction_coefficient=Decimal(0),
        ),
        substrate=BoundMaterial(
            family=design.substrate.family,
            source=design.substrate.source,
            native_name="fixture substrate",
            refractive_index=Decimal(substrate_index),
            extinction_coefficient=Decimal(0),
        ),
        solver_binding_reference=reference_for(b"fixture solver"),
        sample_reference=reference_for(b"fixture material sample"),
        evidence_reference=reference_for(b"provisional material binding"),
    )
    return replace(
        provisional,
        evidence_reference=reference_for(provisional.document().to_bytes()),
    )


def period_domain(
    study: Study,
    *,
    atom_index: str = "2.05",
    substrate_index: str = "1.48",
) -> PeriodDomain:
    """
    Build one byte-exact admitted period-domain fixture.
    """

    binding = material_binding(
        study,
        atom_index=atom_index,
        substrate_index=substrate_index,
    )
    domain = derive_period_domain(study, binding)
    return domain.bind_evidence(reference_for(domain.document().to_bytes()))


def select_fixture_period_nm(
    brief,
    *,
    preferred_period_nm: int,
) -> int:
    """Select the largest admitted period candidate at or below a test preference."""

    if not isinstance(preferred_period_nm, int) or preferred_period_nm <= 0:
        raise ValueError("fixture_period_preference_invalid")
    domain = period_domain(compile_metalens(brief))
    request = form_period_consultation_request(
        brief,
        domain,
        research_mode=ResearchMode.CLOSED_BOOK,
    )
    eligible = tuple(
        int(candidate.quantity)
        for candidate in request.candidates
        if candidate.quantity <= preferred_period_nm
    )
    if not eligible:
        raise ValueError("fixture_period_candidate_missing")
    return eligible[-1]


def period_choice(
    study: Study,
    *,
    atom_index: str = "2.05",
    substrate_index: str = "1.48",
) -> PeriodChoice:
    """
    Build one byte-exact admitted period-choice fixture value.

    When the brief leaves the period open, the fixture mints the same period
    advice the previous shared fixture emitted so byte-exact compat is kept.
    The value is constructed directly so it can be admitted into one compiled
    study without first requiring an admitted period domain in the bare study.
    """

    binding = material_binding(
        study,
        atom_index=atom_index,
        substrate_index=substrate_index,
    )
    domain = period_domain(
        study,
        atom_index=atom_index,
        substrate_index=substrate_index,
    )
    if getattr(study.brief, "cell_period_nm", None) is not None:
        choice = PeriodChoice(
            brief_identity=study.brief_identity,
            period_nm=study.brief.cell_period_nm,
            order_regime=(
                "zeroth order"
                if Decimal(study.brief.cell_period_nm) < domain.order_ceiling_nm
                else "multi order"
            ),
            basis=PeriodConstraintBasis(),
            domain_reference=domain.evidence_reference,
            reason="period stated by brief",
        )
    else:
        _sampling, order, limit = derive_period_limits(study, binding)
        zeroth_order_limit = int(
            (
                (order / Decimal(10)).to_integral_value(rounding=ROUND_CEILING)
                - Decimal(1)
            )
            * Decimal(10)
        )
        fixture_period_nm = min(limit, zeroth_order_limit)
        advice = period_advice(
            study,
            domain,
            period_nm=fixture_period_nm,
        )
        advice_reference = reference_for(advice.document().to_bytes())
        choice = PeriodChoice(
            brief_identity=study.brief_identity,
            period_nm=fixture_period_nm,
            order_regime=(
                "zeroth order"
                if Decimal(fixture_period_nm) < domain.order_ceiling_nm
                else "multi order"
            ),
            basis=PeriodAdviceBasis(advice_reference),
            domain_reference=domain.evidence_reference,
            reason="fixture period",
        )
    return choice.bind_evidence(reference_for(choice.document().to_bytes()))


def height_domain(
    study: Study,
    *,
    atom_index: str = "2.05",
    substrate_index: str = "1.48",
) -> HeightDomain:
    """
    Build one byte-exact admitted height-domain fixture.
    """

    binding = material_binding(
        study,
        atom_index=atom_index,
        substrate_index=substrate_index,
    )
    choice = period_choice(
        study,
        atom_index=atom_index,
        substrate_index=substrate_index,
    )
    domain = period_domain(
        study,
        atom_index=atom_index,
        substrate_index=substrate_index,
    )
    advice = ()
    if isinstance(choice.basis, PeriodAdviceBasis):
        period_record = period_advice(
            study,
            domain,
            period_nm=choice.period_nm,
        )
        advice = (period_record,)
    current, _facts = compile_with_facts(
        study.brief,
        {
            "target_phase": reference_for(b"fixture target phase"),
            "material_binding": binding.evidence_reference,
            "period_domain": domain.evidence_reference,
            "period_choice": choice.evidence_reference,
        },
        advice=advice,
        capabilities=(
            Capability("optical_material"),
            Capability("fabrication_constraint"),
            Capability("deterministic_selection"),
        ),
        bindings=(
            Binding(
                "optical_material",
                reference_for(b"fixture optical material"),
            ),
            Binding(
                "fabrication_constraint",
                reference_for(b"fixture fabrication"),
            ),
            Binding(
                "deterministic_selection",
                reference_for(b"fixture selection"),
            ),
        ),
    )
    domain = derive_height_domain(current, choice, binding)
    return domain.bind_evidence(reference_for(domain.document().to_bytes()))


def height_choice(
    domain: HeightDomain,
    *,
    height_nm: int | None = None,
) -> tuple[HeightChoice, Reference]:
    """Build one exact height choice and its content reference."""

    if domain.evidence_reference is None:
        raise ValueError("fixture_height_domain_not_admitted")
    selected_height_nm = domain.heights_nm[-1] if height_nm is None else height_nm
    fabrication = domain.resolve_fabrication_range(selected_height_nm)
    choice = HeightChoice(
        brief_identity=domain.brief_identity,
        height_nm=selected_height_nm,
        period_nm=domain.period_nm,
        order_regime=domain.order_regime,
        minimum_feature_nm=fabrication.minimum_feature_nm,
        maximum_feature_nm=fabrication.maximum_feature_nm,
        dimension_step_nm=domain.dimension_step_nm,
        domain_reference=domain.evidence_reference,
        basis=HeightConstraintBasis(),
        reason="fixture height",
    )
    return choice, reference_for(choice.document().to_bytes())


def phase_envelope(
    study: Study,
    domain: HeightDomain,
    *,
    atom_index: str = "2.05",
    substrate_index: str = "1.48",
) -> PhaseEnvelope:
    """
    Build one byte-exact admitted propagation envelope fixture.
    """

    binding = material_binding(
        study,
        atom_index=atom_index,
        substrate_index=substrate_index,
    )
    if binding.evidence_reference != domain.material_binding_reference:
        raise ValueError("fixture_material_binding_mismatch")
    envelope = estimate_phase_envelope(
        domain,
        OpticalContrast.from_binding(binding),
    )
    return envelope.admitted(reference_for(envelope.document().to_bytes()))


def _identity(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def period_advice(
    study: Study,
    domain: PeriodDomain,
    *,
    period_nm: int,
) -> PeriodAdvice:
    request = form_period_consultation_request(
        study.brief,
        domain,
        research_mode=ResearchMode.CLOSED_BOOK,
    )
    candidate = next(
        candidate
        for candidate in request.candidates
        if candidate.quantity == Decimal(period_nm)
    )
    return accept_period_consultation_answer(
        study.brief,
        domain,
        request,
        ConsultationAnswer(
            request_identity=request.identity,
            conclusion=Recommendation(
                candidate_identity=candidate.identity,
                reason="fixture period",
                decisive_ground_identities=(request.grounds[-1].identity,),
                external_claim_identities=(),
            ),
            external_claims=(),
        ),
    )


def height_advice(
    brief,
    domain: HeightDomain,
    *,
    envelope: PhaseEnvelope | None = None,
    height_nm: int | None = None,
) -> HeightAdvice:
    """Build one exact height advice through the production consultation seam."""

    request = form_height_consultation_request(
        brief,
        domain,
        envelope=envelope,
        research_mode=ResearchMode.CLOSED_BOOK,
    )
    preferred_height_nm = domain.heights_nm[-1] if height_nm is None else height_nm
    selected_height_nm = select_fixture_height_nm(
        domain,
        envelope=envelope,
        preferred_height_nm=preferred_height_nm,
    )
    candidate = next(
        item
        for item in request.candidates
        if item.quantity == Decimal(selected_height_nm)
    )
    return accept_height_consultation_answer(
        brief,
        domain,
        request,
        ConsultationAnswer(
            request_identity=request.identity,
            conclusion=Recommendation(
                candidate_identity=candidate.identity,
                reason="fixture height",
                decisive_ground_identities=(request.grounds[0].identity,),
                external_claim_identities=(),
            ),
            external_claims=(),
        ),
        envelope=envelope,
    )


def select_fixture_height_nm(
    domain: HeightDomain,
    *,
    envelope: PhaseEnvelope | None,
    preferred_height_nm: int,
) -> int:
    """Select the nearest legal fixture height that evidence has not ruled out."""

    if not isinstance(preferred_height_nm, int) or preferred_height_nm <= 0:
        raise ValueError("fixture_height_preference_invalid")
    candidates = tuple(
        height_nm
        for height_nm in domain.heights_nm
        if envelope is None
        or not all(
            standing.standing == "ruled out"
            for standing in envelope.reach_for(height_nm).standings
        )
    )
    if not candidates:
        raise ValueError("fixture_height_candidate_missing")
    return min(
        candidates,
        key=lambda height_nm: (
            abs(height_nm - preferred_height_nm),
            height_nm > preferred_height_nm,
            height_nm,
        ),
    )


def height_evidence_required(
    brief,
    domain: HeightDomain,
    *,
    envelope: PhaseEnvelope | None = None,
) -> HeightAdvice:
    """Build one honest height wait through the production consultation seam."""

    request = form_height_consultation_request(
        brief,
        domain,
        envelope=envelope,
        research_mode=ResearchMode.CLOSED_BOOK,
    )
    return accept_height_consultation_answer(
        brief,
        domain,
        request,
        ConsultationAnswer(
            request_identity=request.identity,
            conclusion=EvidenceRequired(
                missing_fact="height evidence",
                reason="fixture grounds do not justify one height",
            ),
            external_claims=(),
        ),
        envelope=envelope,
    )
