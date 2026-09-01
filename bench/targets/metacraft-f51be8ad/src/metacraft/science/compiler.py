from __future__ import annotations

from collections.abc import Callable, Mapping
import hashlib

from ..authority.protocol import Reference
from ..canonical import encode_bytes

from .brief import Brief
from .relationships import Method, Relationship
from .study import (
    Advice,
    Binding,
    Capability,
    Claim,
    Design,
    Evidence,
    Finding,
    FindingKind,
    Proof,
    Route,
    RouteChoice,
    Study,
    Task,
)


ResolveAdviceFinding = Callable[
    [Claim, Mapping[str, Evidence]],
    Finding | None,
]
ReportedFindingPredicate = Callable[[Finding], bool]


class MissingBriefFacts(ValueError):
    """
    Names user facts that must be supplied before a study can be compiled.
    """

    def __init__(self, *needs: str) -> None:
        """
        Preserve the missing brief facts in their reported order.
        """

        self.missing_facts = tuple(needs)
        super().__init__(
            "brief_incomplete:" + ",".join(self.missing_facts)
        )


def require_objectives(brief: Brief) -> None:
    """
    Require one duplicate-free set of terminal scientific objectives.
    """

    if not brief.objectives:
        raise MissingBriefFacts("objectives")
    if len(set(brief.objectives)) != len(brief.objectives):
        raise ValueError("objectives_duplicate")


def assemble_study(
    brief: Brief,
    *,
    advice: tuple[Advice, ...],
    design: Design,
    route: Route,
    proof: Proof,
    evidence: tuple[Evidence, ...] = (),
    capabilities: tuple[Capability, ...] = (),
    bindings: tuple[Binding, ...] = (),
    consultations: Mapping[str, Reference],
    resolve_advice_finding: ResolveAdviceFinding,
    is_reported_finding_valid: ReportedFindingPredicate,
    reported_findings: tuple[Finding, ...] = (),
) -> Study:
    """
    Assemble one immutable Study from aim-owned meaning and admitted facts.
    """

    brief_identity = _identity(brief.canonical_bytes())
    design_identity = _identity(encode_bytes(design.canonical_value()))
    method_by_claim = {
        choice.claim: choice.method
        for choice in route.choices
    }
    schema_by_claim = {claim.name: claim.schema for claim in proof.claims}
    capability_by_name = _resolve_capabilities(proof, capabilities)
    binding_by_capability = _bind_capabilities(
        proof,
        capabilities,
        bindings,
    )
    evidence_by_claim = _close_evidence(
        proof,
        brief_identity,
        design_identity,
        evidence,
        method_by_claim,
        schema_by_claim,
        consultations,
        binding_by_capability,
    )
    satisfied = set(evidence_by_claim)
    ready_tasks = []
    findings = []
    reported_by_claim = {
        finding.claim: finding for finding in reported_findings
    }
    if len(reported_by_claim) != len(reported_findings):
        raise ValueError("reported_finding_duplicate")
    proof_claims = {item.name for item in proof.claims}
    if any(
        finding.claim not in proof_claims
        or not is_reported_finding_valid(finding)
        for finding in reported_findings
    ):
        raise ValueError("reported_finding_invalid")
    for claim in proof.claims:
        if claim.name in satisfied:
            continue
        if claim.name in reported_by_claim:
            findings.append(reported_by_claim[claim.name])
            continue
        missing_prerequisites = tuple(
            prerequisite
            for prerequisite in claim.requires
            if prerequisite not in satisfied
        )
        if missing_prerequisites:
            findings.append(
                Finding(
                    claim=claim.name,
                    kind=FindingKind.PREREQUISITE,
                    needs=missing_prerequisites,
                )
            )
            continue
        advice_finding = resolve_advice_finding(
            claim,
            evidence_by_claim,
        )
        if advice_finding is not None:
            findings.append(advice_finding)
            continue
        capability = (
            None
            if claim.capability is None
            else capability_by_name.get(claim.capability)
        )
        if claim.capability is not None and capability is None:
            findings.append(
                Finding(
                    claim=claim.name,
                    kind=FindingKind.CAPABILITY,
                    needs=(claim.capability,),
                )
            )
            continue
        binding = (
            None
            if claim.capability is None
            else binding_by_capability.get(claim.capability)
        )
        if claim.capability is not None and binding is None:
            findings.append(
                Finding(
                    claim=claim.name,
                    kind=FindingKind.BINDING,
                    needs=(claim.capability,),
                )
            )
            continue
        ready_tasks.append(
            _bind_task(
                proof_identity=proof.identity,
                claim=claim,
                method=method_by_claim[claim.name],
                brief_identity=brief_identity,
                design_identity=design_identity,
                prerequisite_evidence=tuple(
                    evidence_by_claim[name].reference
                    for name in claim.requires
                ),
                consultation_reference=consultations.get(claim.name),
                binding=binding,
            )
        )
    return Study(
        brief=brief,
        brief_identity=brief_identity,
        advice=tuple(
            sorted(
                advice,
                key=lambda item: encode_bytes(item.canonical_value()),
            )
        ),
        design=design,
        route=route,
        proof=proof,
        evidence=tuple(
            evidence_by_claim[claim.name]
            for claim in proof.claims
            if claim.name in evidence_by_claim
        ),
        capabilities=tuple(
            capability_by_name[name]
            for name in sorted(capability_by_name)
        ),
        bindings=tuple(
            binding_by_capability[name]
            for name in sorted(binding_by_capability)
        ),
        ready_tasks=tuple(ready_tasks),
        findings=tuple(findings),
    )


def prove_relationship(
    relationship: Relationship,
    terminal_claims: tuple[str, ...],
) -> tuple[Route, Proof]:
    """
    Compose one deterministic proof from applicable claim methods.
    """

    if any(
        objective not in relationship.objectives
        for objective in terminal_claims
    ):
        raise ValueError("objective_unsupported")

    applicable: dict[str, Method] = {}
    for method in sorted(
        relationship.methods,
        key=lambda candidate: (candidate.claim, candidate.name),
    ):
        if method.claim in applicable:
            raise ValueError(f"proof_ambiguous:{method.claim}")
        applicable[method.claim] = method

    ordered: list[Method] = []
    proven_claims: set[str] = set()
    active: set[str] = set()

    def prove_claim(claim: str) -> None:
        """
        Add one claim and its prerequisites in proof order.
        """

        if claim in proven_claims:
            return
        if claim in active:
            raise ValueError(f"proof_cycle:{claim}")
        method = applicable.get(claim)
        if method is None:
            raise ValueError(f"proof_incomplete:{claim}")
        active.add(claim)
        for prerequisite in method.requires:
            prove_claim(prerequisite)
        active.remove(claim)
        proven_claims.add(claim)
        ordered.append(method)

    for terminal_claim in terminal_claims:
        prove_claim(terminal_claim)
    choices = tuple(
        RouteChoice(
            claim=method.claim,
            method=method.name,
            requires=method.requires,
        )
        for method in ordered
    )
    route = Route(
        aim=relationship.aim,
        objectives=relationship.objectives,
        applicability=relationship.applicability,
        choices=choices,
    )
    proof = Proof(
        route=route,
        terminal_claims=terminal_claims,
        claims=tuple(
            Claim(
                name=method.claim,
                requires=method.requires,
                capability=method.capability,
                schema=method.schema,
            )
            for method in ordered
        ),
    )
    return route, proof


def _bind_task(
    *,
    proof_identity: str,
    claim: Claim,
    method: str,
    brief_identity: str,
    design_identity: str,
    prerequisite_evidence: tuple[Reference, ...],
    consultation_reference: Reference | None,
    binding: Binding | None,
) -> Task:
    """
    Build one ready task with its identity derived from bound meaning.
    """

    return Task(
        proof_identity=proof_identity,
        claim=claim.name,
        method=method,
        schema=claim.schema,
        brief_identity=brief_identity,
        design_identity=design_identity,
        prerequisite_evidence=prerequisite_evidence,
        consultations=(
            () if consultation_reference is None
            else (consultation_reference,)
        ),
        binding_reference=(
            None if binding is None else binding.reference
        ),
        capacity_scope=(
            None if binding is None else binding.capacity_scope
        ),
    )


def _identity(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _close_evidence(
    proof: Proof,
    brief_identity: str,
    design_identity: str,
    evidence: tuple[Evidence, ...],
    method_by_claim: dict[str, str],
    schema_by_claim: dict[str, str],
    consultations: Mapping[str, Reference],
    binding_by_capability: dict[str, Binding],
) -> dict[str, Evidence]:
    """
    Validate that admitted facts follow this proof's task topology.

    Each Evidence must cite the exact task_identity computed from
    this proof's identity, the target claim and method, the brief and
    design identities, the prerequisite evidence references, the
    consultations, and the binding and capacity scope. Same-schema
    evidence prepared for another task is rejected.
    """

    known = {claim.name: claim for claim in proof.claims}
    selected: dict[str, Evidence] = {}
    for fact in evidence:
        if fact.claim not in known:
            raise ValueError("evidence_obligation_unknown")
        if fact.claim in selected:
            raise ValueError("evidence_obligation_duplicate")
        if fact.schema != known[fact.claim].schema:
            raise ValueError("evidence_schema_mismatch")
        selected[fact.claim] = fact
    admitted: dict[str, Evidence] = {}
    for claim in proof.claims:
        fact = selected.get(claim.name)
        if fact is None:
            continue
        if any(name not in admitted for name in claim.requires):
            raise ValueError("evidence_prerequisites_incomplete")
        consultation_reference = consultations.get(claim.name)
        binding = (
            None
            if claim.capability is None
            else binding_by_capability.get(claim.capability)
        )
        prerequisite_evidence = _resolve_prerequisite_evidence(
            claim,
            admitted,
        )
        expected_task = _derive_task_identity(
            proof_identity=proof.identity,
            claim=claim,
            method=method_by_claim[claim.name],
            brief_identity=brief_identity,
            design_identity=design_identity,
            prerequisite_evidence=prerequisite_evidence,
            schema=schema_by_claim[claim.name],
            consultation_reference=consultation_reference,
            binding=binding,
        )
        if fact.task_identity != expected_task:
            raise ValueError("evidence_task_identity_mismatch")
        if fact.consultations != (
            ()
            if consultation_reference is None
            else (consultation_reference,)
        ):
            raise ValueError("evidence_consultation_mismatch")
        admitted[claim.name] = fact
    return admitted


def _resolve_prerequisite_evidence(
    claim: Claim,
    selected: dict[str, Evidence],
) -> tuple[Reference, ...]:
    """
    Return prerequisite references already selected for one claim.
    """

    return tuple(
        selected[name].reference
        for name in claim.requires
        if name in selected
    )


def _derive_task_identity(
    *,
    proof_identity: str,
    claim: Claim,
    method: str,
    brief_identity: str,
    design_identity: str,
    prerequisite_evidence: tuple[Reference, ...],
    schema: str,
    consultation_reference: Reference | None = None,
    binding: Binding | None = None,
) -> str:
    """
    Recompute the canonical task identity for one claim.

    Mirrors ``_bind_task`` so that admitted Evidence can be matched
    against the proof topology while the proof is still being assembled.
    """

    task = _bind_task(
        proof_identity=proof_identity,
        claim=claim,
        method=method,
        brief_identity=brief_identity,
        design_identity=design_identity,
        prerequisite_evidence=prerequisite_evidence,
        consultation_reference=consultation_reference,
        binding=binding,
    )
    return task.identity


def _resolve_capabilities(
    proof: Proof,
    capabilities: tuple[Capability, ...],
) -> dict[str, Capability]:
    """
    Accept only unique capabilities named by this proof.
    """

    allowed = {
        claim.capability
        for claim in proof.claims
        if claim.capability is not None
    }
    selected: dict[str, Capability] = {}
    for capability in capabilities:
        if capability.name not in allowed:
            raise ValueError("capability_not_allowed")
        if capability.name in selected:
            raise ValueError("capability_duplicate")
        selected[capability.name] = capability
    return selected


def _bind_capabilities(
    proof: Proof,
    capabilities: tuple[Capability, ...],
    bindings: tuple[Binding, ...],
) -> dict[str, Binding]:
    """
    Keep qualified abilities separate from selected realizations.
    """

    allowed = {
        claim.capability
        for claim in proof.claims
        if claim.capability is not None
    }
    qualified_capabilities = {
        capability.name for capability in capabilities
    }
    selected: dict[str, Binding] = {}
    for binding in bindings:
        if binding.capability not in allowed:
            raise ValueError("binding_not_allowed")
        if binding.capability not in qualified_capabilities:
            raise ValueError("binding_without_capability")
        if binding.capability in selected:
            raise ValueError("binding_duplicate")
        selected[binding.capability] = binding
    return selected
