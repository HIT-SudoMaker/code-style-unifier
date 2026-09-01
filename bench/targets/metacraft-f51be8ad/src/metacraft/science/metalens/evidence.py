from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from ...authority import Document, Reference
from ...authority.reference import reference_for
from ...authority.session import AuthoritySession
from ..brief import Brief
from ..consultation import (
    ConsultationAnswer,
    ConsultationCandidate,
    ConsultationRequest,
    EvidenceRequired,
    Recommendation,
    ResearchMode,
    QuestionKind,
)
from ...field import Field
from ...field.evidence import (
    FIELD_SCHEMA,
    admit_components,
    field_document,
    restore_field,
)
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

from .brief import ControlStrategy, MetalensBrief
from .aperture import Lattice
from .compiler import (
    DOMAIN_OWNED_FINDING_CLAIMS,
    compile_metalens,
    restore_metalens_inputs,
)
from .consultation import (
    InvalidMetalensConsultationAnswer,
    accept_height_consultation_answer,
    accept_period_consultation_answer,
    form_height_consultation_request,
    form_period_consultation_request,
)
from .design import require_metalens_design
from .focus import (
    FOCUS_SURVEY_SCHEMA,
    FocalRegion,
    Focus,
    FocusSurvey,
    focus_document,
)
from .focus_evidence import (
    LONGITUDINAL_POWER_MEDIA_TYPE,
    focal_region_document,
    longitudinal_power_bytes,
    longitudinal_power_metadata,
    restore_focal_region,
)
from .height import (
    HeightChoice,
    HeightDomain,
    validate_height_choice_finding,
    validate_height_domain_finding,
)
from .height_advice import HeightAdvice, HeightRecommendation
from .material import MaterialBinding
from .period import (
    PeriodChoice,
    PeriodDomain,
    validate_period_choice_finding,
)
from .period_advice import PeriodAdvice, PeriodRecommendation
from .propagation_envelope import PhaseEnvelope

@dataclass(frozen=True, slots=True)
class MetalensEvidence:
    """
    Admit and restore the evidence of one metalens study.

    This seam deliberately owns no lifecycle and no external scientific port.
    It translates between immutable studies and Authority records only.
    """

    _session: AuthoritySession

    def admit_task(
        self,
        task: Task,
        document: Document,
        *,
        sources: tuple[Reference, ...] = (),
    ) -> Reference:
        """
        Admit one task-shaped scientific document and its sources.
        """

        if document.schema_identifier != task.schema:
            raise RuntimeError("task_observation_schema_mismatch")
        return self._session.admit_document(
            document,
            references=tuple(dict.fromkeys(sources)),
        )

    def admit_field(self, task: Task, field: Field) -> Reference:
        """
        Admit one field and every component array it owns.
        """

        electric, magnetic = admit_components(
            field.electric_components,
            field.magnetic_components,
            self._session.admit_object,
        )
        return self.admit_task(
            task,
            field_document(
                task.schema,
                field,
                electric,
                magnetic_component_references=magnetic,
            ),
            sources=(
                *field.source_references,
                *electric.values(),
                *magnetic.values(),
            ),
        )

    def admit_scientific_field(self, field: Field) -> Reference:
        """Admit one child Field that belongs to a compound scientific claim."""

        electric, magnetic = admit_components(
            field.electric_components,
            field.magnetic_components,
            self._session.admit_object,
        )
        return self.admit_document(
            field_document(
                FIELD_SCHEMA,
                field,
                electric,
                magnetic_component_references=magnetic,
            ),
            sources=(
                *field.source_references,
                *electric.values(),
                *magnetic.values(),
            ),
        )

    def restore_field(self, study: Study) -> Field:
        """
        Restore the sole admitted field fact from a Study.
        """

        reference = self.fact(study, "field").reference
        return restore_field(
            Document.from_bytes(self.fetch(reference)),
            self.fetch,
        )

    def admit_focal_region(
        self,
        task: Task,
        region: FocalRegion,
        *,
        field_reference: Reference,
    ) -> Reference:
        """
        Admit one focal region with its field, binding, and components.
        """

        binding_reference = _require_reference(
            task.binding_reference,
            "task_binding_missing",
        )
        electric, magnetic = admit_components(
            region.electric_components,
            region.magnetic_components,
            self._session.admit_object,
        )
        power_plane = region.longitudinal_power_plane
        power_reference = (
            None
            if power_plane is None
            else self._session.admit_object(
                longitudinal_power_bytes(power_plane),
                media_type=LONGITUDINAL_POWER_MEDIA_TYPE,
                descriptive_metadata=longitudinal_power_metadata(
                    power_plane.surface
                ),
            )
        )
        return self.admit_task(
            task,
            focal_region_document(
                region,
                electric,
                binding_reference=binding_reference,
                field_reference=field_reference,
                magnetic_component_references=magnetic,
                longitudinal_power_reference=power_reference,
            ),
            sources=(
                binding_reference,
                field_reference,
                *electric.values(),
                *magnetic.values(),
                *((power_reference,) if power_reference is not None else ()),
            ),
        )

    def admit_scientific_focal_region(
        self,
        region: FocalRegion,
        *,
        binding_reference: Reference,
        field_reference: Reference,
    ) -> Reference:
        """Admit one child focal region under a compound spectral claim."""

        electric, magnetic = admit_components(
            region.electric_components,
            region.magnetic_components,
            self._session.admit_object,
        )
        if region.longitudinal_power_plane is not None:
            raise ValueError("compound_vector_focal_region_unsupported")
        return self.admit_document(
            focal_region_document(
                region,
                electric,
                binding_reference=binding_reference,
                field_reference=field_reference,
                magnetic_component_references=magnetic,
            ),
            sources=(
                binding_reference,
                field_reference,
                *electric.values(),
                *magnetic.values(),
            ),
        )

    def admit_scientific_focus(
        self,
        focus: Focus,
        *,
        focal_region_reference: Reference,
    ) -> Reference:
        """Admit one complete child Focus under a compound spectral claim."""

        return self.admit_document(
            focus_document(
                focal_region_reference=focal_region_reference,
                focus=focus,
            ),
            sources=(focal_region_reference,),
        )

    def restore_focal_region(self, study: Study) -> FocalRegion:
        """
        Restore the sole admitted focal-region fact from a Study.
        """

        reference = self.fact(study, "focal_region").reference
        return restore_focal_region(
            Document.from_bytes(self.fetch(reference)),
            self.fetch,
        )

    def physical_lattice(self, study: Study) -> Lattice:
        """Restore the sole lattice and verify its exact period-choice source."""

        lattice_reference = self.fact(study, "physical_lattice").reference
        lattice = Lattice.from_document(
            Document.from_bytes(self.fetch(lattice_reference))
        )
        period_choice = self.period_choice(study)
        period_reference = self.fact(study, "period_choice").reference
        if (
            lattice.spacing_source_reference != period_reference
            or lattice.spacing_nm != period_choice.period_nm
        ):
            raise ValueError("physical_lattice_period_choice_mismatch")
        return lattice

    def record_focus(
        self,
        study: Study,
        task: Task,
        focus: Focus | FocusSurvey,
        *,
        focal_region_reference: Reference,
    ) -> Study:
        """
        Record a completed focus or its bounded incomplete survey.
        """

        if isinstance(focus, Focus):
            reference = self.admit_task(
                task,
                focus_document(
                    focal_region_reference=focal_region_reference,
                    focus=focus,
                ),
                sources=(focal_region_reference,),
            )
            return self.with_fact(study, task, reference)
        diagnostic = Document(
            FOCUS_SURVEY_SCHEMA,
            {
                "claim": task.claim,
                "focal_region": focal_region_reference.as_mapping(),
                "need": "focus_incomplete",
                "survey": focus.as_mapping(),
            },
        )
        reference = self.admit_document(
            diagnostic,
            sources=(focal_region_reference,),
        )
        return self.with_finding(
            study,
            focus.finding(reference, claim=task.claim),
        )

    def with_fact(
        self,
        study: Study,
        task: Task,
        reference: Reference,
    ) -> Study:
        """
        Recompile a Study with one newly admitted task fact.
        """

        evidence = Evidence(
            task_identity=task.identity,
            claim=task.claim,
            schema=task.schema,
            reference=reference,
            binding_reference=task.binding_reference,
            consultations=task.consultations,
        )
        return self.recompile(study, evidence=(*study.evidence, evidence))

    def with_refusal(
        self,
        study: Study,
        claim: str,
        reason: str,
    ) -> Study:
        """
        Recompile a Study with one expected refusal finding.
        """

        return self.with_finding(
            study,
            Finding(
                claim=claim,
                kind=FindingKind.REFUSAL,
                needs=(reason,),
            ),
        )

    def with_unavailable(
        self,
        study: Study,
        task: Task,
        reason: str,
    ) -> Study:
        """
        Recompile after one ready task meets external unavailability.
        """

        return self.with_finding(
            study,
            Finding(
                claim=task.claim,
                kind=FindingKind.UNAVAILABLE,
                needs=(reason,),
            ),
        )

    def with_finding(self, study: Study, finding: Finding) -> Study:
        """
        Preserve and add one aim-owned reported finding.
        """

        _advice, reported = restore_metalens_inputs(study)
        return self.recompile(
            study,
            reported_findings=tuple(dict.fromkeys((*reported, finding))),
        )

    def recompile(
        self,
        study: Study,
        *,
        advice: tuple[Advice, ...] | None = None,
        evidence: tuple[Evidence, ...] | None = None,
        capabilities: tuple[Capability, ...] | None = None,
        bindings: tuple[Binding, ...] | None = None,
        reported_findings: tuple[Finding, ...] | None = None,
    ) -> Study:
        """
        Recompile from selected facts while preserving omitted inputs.
        """

        restored_advice, restored_findings = restore_metalens_inputs(study)
        selected_advice = restored_advice if advice is None else advice
        selected_advice = self._replay_advice(study, selected_advice)
        selected_findings = (
            restored_findings
            if reported_findings is None
            else reported_findings
        )
        domain_findings = tuple(
            finding
            for finding in selected_findings
            if finding.claim in DOMAIN_OWNED_FINDING_CLAIMS
            and finding.kind in (FindingKind.ADVICE, FindingKind.REFUSAL)
        )
        if len({finding.claim for finding in domain_findings}) != len(
            domain_findings
        ):
            raise ValueError("reported_finding_duplicate")
        compiled = compile_metalens(
            _require_metalens(study.brief),
            advice=selected_advice,
            evidence=study.evidence if evidence is None else evidence,
            capabilities=(
                study.capabilities
                if capabilities is None
                else capabilities
            ),
            bindings=study.bindings if bindings is None else bindings,
            reported_findings=tuple(
                finding
                for finding in selected_findings
                if finding not in domain_findings
            ),
        )
        findings_by_claim = {
            finding.claim: finding for finding in domain_findings
        }
        advice_references = frozenset(
            reference_for(item.document().to_bytes())
            for item in selected_advice
            if isinstance(item, (PeriodAdvice, HeightAdvice))
        )
        for claim in compiled.proof.claims:
            finding = findings_by_claim.get(claim.name)
            if finding is not None:
                compiled = self._record_domain_finding(
                    compiled,
                    selected_advice,
                    finding,
                    advice_references,
                )
        return compiled

    def _replay_advice(
        self,
        study: Study,
        advice: tuple[Advice, ...],
    ) -> tuple[Advice, ...]:
        """
        Authenticate and regenerate retained advice under current rules.
        """

        period = _period_advice(advice)
        height = _height_advice(advice)
        replayed_period = (
            None if period is None else self._replay_period_advice(study, period)
        )
        replayed_height = (
            None if height is None else self._replay_height_advice(study, height)
        )
        replayed: list[Advice] = []
        for item in advice:
            if isinstance(item, PeriodAdvice):
                assert replayed_period is not None
                replayed.append(replayed_period)
            elif isinstance(item, HeightAdvice):
                assert replayed_height is not None
                replayed.append(replayed_height)
            else:
                replayed.append(item)
        return tuple(replayed)

    def _replay_period_advice(
        self,
        study: Study,
        retained: PeriodAdvice,
    ) -> PeriodAdvice:
        retained_bytes = retained.document().to_bytes()
        admitted_bytes = self._admitted_advice_bytes(
            retained_bytes,
            mismatch_reason="period_advice_replay_mismatch",
        )
        retained = PeriodAdvice.from_document(Document.from_bytes(admitted_bytes))
        domain = self.period_domain(study)
        request = _matching_request(
            retained.request_identity,
            tuple(
                form_period_consultation_request(
                    _require_metalens(study.brief),
                    domain,
                    research_mode=mode,
                )
                for mode in ResearchMode
            ),
            stale_reason="period_advice_request_stale",
        )
        try:
            regenerated = accept_period_consultation_answer(
                _require_metalens(study.brief),
                domain,
                request,
                _period_answer(retained, request),
            )
        except InvalidMetalensConsultationAnswer as error:
            if error.question_kind is not QuestionKind.PERIOD:
                raise
            raise ValueError("period_advice_replay_mismatch") from error
        if regenerated.document().to_bytes() != retained_bytes:
            raise ValueError("period_advice_replay_mismatch")
        return regenerated

    def _replay_height_advice(
        self,
        study: Study,
        retained: HeightAdvice,
    ) -> HeightAdvice:
        retained_bytes = retained.document().to_bytes()
        admitted_bytes = self._admitted_advice_bytes(
            retained_bytes,
            mismatch_reason="height_advice_replay_mismatch",
        )
        retained = HeightAdvice.from_document(Document.from_bytes(admitted_bytes))
        domain = self.height_domain(study)
        envelope = (
            self.phase_envelope(study)
            if _require_metalens(study.brief).control_strategy
            is ControlStrategy.PROPAGATION_PHASE
            else None
        )
        request = _matching_request(
            retained.request_identity,
            tuple(
                form_height_consultation_request(
                    _require_metalens(study.brief),
                    domain,
                    envelope=envelope,
                    research_mode=mode,
                )
                for mode in ResearchMode
            ),
            stale_reason="height_advice_request_stale",
        )
        try:
            regenerated = accept_height_consultation_answer(
                _require_metalens(study.brief),
                domain,
                request,
                _height_answer(retained, request),
                envelope=envelope,
            )
        except InvalidMetalensConsultationAnswer as error:
            if error.question_kind is not QuestionKind.HEIGHT:
                raise
            raise ValueError("height_advice_replay_mismatch") from error
        if regenerated.document().to_bytes() != retained_bytes:
            raise ValueError("height_advice_replay_mismatch")
        return regenerated

    def _admitted_advice_bytes(
        self,
        retained_bytes: bytes,
        *,
        mismatch_reason: str,
    ) -> bytes:
        reference = reference_for(retained_bytes)
        self.observe_admitted(reference)
        admitted_bytes = self.fetch(reference)
        if admitted_bytes != retained_bytes:
            raise ValueError(mismatch_reason)
        return admitted_bytes

    def _record_domain_finding(
        self,
        study: Study,
        advice: tuple[Advice, ...],
        finding: Finding,
        advice_references: frozenset[Reference],
    ) -> Study:
        """
        Recompute one domain finding from exact Authority-backed inputs.
        """

        tasks = tuple(
            task for task in study.ready_tasks if task.claim == finding.claim
        )
        if len(tasks) != 1:
            raise ValueError("reported_finding_invalid")
        if finding.claim == "period_choice":
            period_advice = _period_advice(advice)
            validate_period_choice_finding(
                study,
                self.period_domain(study),
                period_advice,
                finding,
            )
        elif finding.claim == "height_domain":
            validate_height_domain_finding(
                study,
                self.period_choice(study),
                self.material_binding(study),
                finding,
            )
        elif finding.claim == "height_choice":
            height_advice = _height_advice(advice)
            envelope = (
                self.phase_envelope(study)
                if require_metalens_design(study).control_strategy
                is ControlStrategy.PROPAGATION_PHASE
                else None
            )
            validate_height_choice_finding(
                study,
                self.height_domain(study),
                height_advice,
                finding,
                envelope=envelope,
            )
        else:
            raise ValueError("reported_finding_invalid")
        for reference in finding.record_references:
            if reference not in advice_references:
                self.observe_admitted(reference)
        return _record_finding(study, finding)

    @staticmethod
    def fact(study: Study, claim: str) -> Evidence:
        """
        Return the sole evidence item for one claim.
        """

        matches = tuple(item for item in study.evidence if item.claim == claim)
        if len(matches) != 1:
            raise RuntimeError(f"evidence_missing:{claim}")
        return matches[0]

    def height_choice(self, study: Study) -> HeightChoice:
        """
        Restore the admitted height choice from a Study.
        """

        reference = self.fact(study, "height_choice").reference
        return HeightChoice.from_document(
            Document.from_bytes(self.fetch(reference))
        )

    def height_domain(self, study: Study) -> HeightDomain:
        """
        Restore the admitted height domain from a Study.
        """

        reference = self.fact(study, "height_domain").reference
        return HeightDomain.from_document(
            Document.from_bytes(self.fetch(reference)),
            evidence_reference=reference,
        )

    def material_binding(self, study: Study) -> MaterialBinding:
        """
        Restore a material binding and verify its direct sources exist.
        """

        reference = self.fact(study, "material_binding").reference
        binding = MaterialBinding.from_document(
            Document.from_bytes(self.fetch(reference)),
            evidence_reference=reference,
        )
        self.fetch(binding.sample_reference)
        self.fetch(binding.solver_binding_reference)
        return binding

    def period_domain(self, study: Study) -> PeriodDomain:
        """
        Restore the admitted period domain from a Study.
        """

        reference = self.fact(study, "period_domain").reference
        return PeriodDomain.from_document(
            Document.from_bytes(self.fetch(reference)),
            evidence_reference=reference,
        )

    def period_choice(self, study: Study) -> PeriodChoice:
        """
        Restore and bind the admitted period choice from a Study.
        """

        reference = self.fact(study, "period_choice").reference
        return PeriodChoice.from_document(
            Document.from_bytes(self.fetch(reference))
        ).bind_evidence(reference)

    def phase_envelope(self, study: Study) -> PhaseEnvelope:
        """
        Restore the admitted propagation envelope from a Study.
        """

        reference = self.fact(study, "phase_envelope").reference
        return PhaseEnvelope.from_document(
            Document.from_bytes(self.fetch(reference)),
            evidence_reference=reference,
        )

    def fetch(self, reference: Reference) -> bytes:
        """
        Fetch exact admitted bytes through the owned session.
        """

        return self._session.fetch(reference)

    def observe_admitted(self, reference: Reference) -> None:
        """
        Require one reference to be admitted in the session view.
        """

        self._session.observe_admitted(reference)

    def admit_document(
        self,
        document: Document,
        *,
        sources: tuple[Reference, ...] = (),
    ) -> Reference:
        """
        Admit one scientific document with its direct sources.
        """

        return self._session.admit_document(document, references=sources)

    def admit_object(
        self,
        body: bytes,
        *,
        media_type: str,
        descriptive_metadata: Mapping[str, Any],
    ) -> Reference:
        """
        Admit one binary scientific object with descriptive metadata.
        """

        return self._session.admit_object(
            body,
            media_type=media_type,
            descriptive_metadata=descriptive_metadata,
        )


def _require_metalens(brief: Brief) -> MetalensBrief:
    if not isinstance(brief, MetalensBrief):
        raise RuntimeError("metalens_brief_required")
    return brief


def _require_reference(
    reference: Reference | None,
    reason: str,
) -> Reference:
    if reference is None:
        raise RuntimeError(reason)
    return reference


def _period_advice(advice: tuple[Advice, ...]) -> PeriodAdvice | None:
    records = tuple(item for item in advice if isinstance(item, PeriodAdvice))
    if len(records) > 1:
        raise ValueError("period_advice_duplicate")
    return None if not records else records[0]


def _height_advice(advice: tuple[Advice, ...]) -> HeightAdvice | None:
    records = tuple(item for item in advice if isinstance(item, HeightAdvice))
    if len(records) > 1:
        raise ValueError("height_advice_duplicate")
    return None if not records else records[0]


def _matching_request(
    retained_identity: str,
    requests: tuple[ConsultationRequest, ...],
    *,
    stale_reason: str,
) -> ConsultationRequest:
    matches = tuple(
        request for request in requests if request.identity == retained_identity
    )
    if len(matches) != 1:
        raise ValueError(stale_reason)
    return matches[0]


def _period_answer(
    advice: PeriodAdvice,
    request: ConsultationRequest,
) -> ConsultationAnswer:
    conclusion = advice.conclusion
    if isinstance(conclusion, EvidenceRequired):
        answer_conclusion = conclusion
    else:
        assert isinstance(conclusion, PeriodRecommendation)
        candidate = _candidate_for_quantity(
            request,
            conclusion.period_nm,
            mismatch_reason="period_advice_replay_mismatch",
        )
        answer_conclusion = Recommendation(
            candidate_identity=candidate.identity,
            reason=conclusion.reason,
            decisive_ground_identities=conclusion.decisive_ground_identities,
            external_claim_identities=conclusion.external_claim_identities,
        )
    return ConsultationAnswer(
        request_identity=request.identity,
        conclusion=answer_conclusion,
        external_claims=advice.external_claims,
    )


def _height_answer(
    advice: HeightAdvice,
    request: ConsultationRequest,
) -> ConsultationAnswer:
    conclusion = advice.conclusion
    if isinstance(conclusion, EvidenceRequired):
        answer_conclusion = conclusion
    else:
        assert isinstance(conclusion, HeightRecommendation)
        candidate = _candidate_for_quantity(
            request,
            conclusion.height_nm,
            mismatch_reason="height_advice_replay_mismatch",
        )
        answer_conclusion = Recommendation(
            candidate_identity=candidate.identity,
            reason=conclusion.reason,
            decisive_ground_identities=conclusion.decisive_ground_identities,
            external_claim_identities=conclusion.external_claim_identities,
        )
    return ConsultationAnswer(
        request_identity=request.identity,
        conclusion=answer_conclusion,
        external_claims=advice.external_claims,
    )


def _candidate_for_quantity(
    request: ConsultationRequest,
    quantity_nm: int,
    *,
    mismatch_reason: str,
) -> ConsultationCandidate:
    matches = tuple(
        candidate
        for candidate in request.candidates
        if candidate.unit == "nm" and candidate.quantity == quantity_nm
    )
    if len(matches) != 1:
        raise ValueError(mismatch_reason)
    return matches[0]


def _record_finding(study: Study, finding: Finding) -> Study:
    findings_by_claim = {
        item.claim: item for item in (*study.findings, finding)
    }
    return replace(
        study,
        ready_tasks=tuple(
            task for task in study.ready_tasks if task.claim != finding.claim
        ),
        findings=tuple(
            findings_by_claim[claim.name]
            for claim in study.proof.claims
            if claim.name in findings_by_claim
        ),
    )
