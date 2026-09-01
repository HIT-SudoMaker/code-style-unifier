from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any, Protocol

from ..authority.protocol import Document, Reference
from ..canonical import canonicalize, encode_bytes

from .brief import Brief


STUDY_SCHEMA = "metacraft.science.study"


class Advice(Protocol):
    """
    Describes one immutable, untrusted consultation without naming its aim.
    """

    def canonical_value(self) -> Any:
        """
        Return the durable advice value used inside a canonical Study.
        """

        ...


class FindingKind(str, Enum):
    """
    Names one ordinary reason why a proof is waiting.
    """

    PREREQUISITE = "prerequisite"
    ADVICE = "advice"
    CAPABILITY = "capability"
    BINDING = "binding"
    REFUSAL = "refusal"
    UNAVAILABLE = "unavailable"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True, slots=True, kw_only=True)
class Design:
    """
    Resolves one aim without imposing aim-specific scientific fields.
    """

    aim: str
    objectives: tuple[str, ...]
    capabilities: tuple[str, ...]
    budget: str

    def canonical_value(self) -> Any:
        """
        Return the durable resolved-design value used at identity boundaries.
        """

        return self


@dataclass(frozen=True, slots=True)
class Claim:
    """
    Names one evidence requirement, its prerequisite claims, and the
    schema identifier of the value that establishes it.
    """

    name: str
    requires: tuple[str, ...]
    capability: str | None
    schema: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RouteChoice:
    """
    Records one selected method and the claim it establishes.
    """

    claim: str
    method: str
    requires: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class Route:
    """
    Content-addressed selection of aim, objectives, claims, methods, and
    applicability choices. Identity is canonical content only; no
    hand-written name is carried.
    """

    aim: str
    objectives: tuple[str, ...]
    applicability: str
    choices: tuple[RouteChoice, ...]

    def canonical_bytes(self) -> bytes:
        """
        Encode this route for deterministic comparison and identity.
        """

        return encode_bytes(_route_value(self))

    @property
    def identity(self) -> str:
        """
        Return the canonical digest of this route's complete meaning.
        """

        return _identity_digest(self.canonical_bytes())


@dataclass(frozen=True, slots=True, kw_only=True)
class Proof:
    """
    Holds one route's complete prerequisite and evidence topology. Its
    identity states the exact scientific meaning of the route it expands.
    """

    route: Route
    terminal_claims: tuple[str, ...]
    claims: tuple[Claim, ...]

    def canonical_bytes(self) -> bytes:
        """
        Encode this proof for deterministic comparison and identity.
        """

        return encode_bytes(_proof_value(self))

    @property
    def identity(self) -> str:
        """
        Return the canonical digest of this proof's complete meaning.
        """

        return _identity_digest(self.canonical_bytes())


@dataclass(frozen=True, slots=True)
class Caution:
    """
    Discloses one evidence-backed limitation without blocking a proof.
    """

    concern: str
    explanation: str
    source_reference: Reference

    def as_mapping(self) -> dict[str, object]:
        """
        Return the concern beside the exact evidence that supports it.
        """

        return {
            "concern": self.concern,
            "explanation": self.explanation,
            "source": self.source_reference.as_mapping(),
        }


@dataclass(frozen=True, slots=True)
class Finding:
    """
    Explains one claim that cannot yet become ready.
    """

    claim: str
    kind: FindingKind
    needs: tuple[str, ...]
    record_references: tuple[Reference, ...] = ()

    def __post_init__(self) -> None:
        """
        Keep diagnostic provenance immutable and duplicate-free.
        """

        if not isinstance(self.record_references, tuple):
            raise ValueError("finding_record_references_invalid")
        if len(set(self.record_references)) != len(
            self.record_references
        ):
            raise ValueError("finding_record_reference_duplicate")
        if self.kind is FindingKind.UNAVAILABLE and (
            not isinstance(self.needs, tuple)
            or len(self.needs) != 1
            or not isinstance(self.needs[0], str)
            or not self.needs[0]
            or self.record_references
        ):
            raise ValueError("finding_unavailable_invalid")


@dataclass(frozen=True, slots=True, kw_only=True)
class Evidence:
    """
    Names one admitted task evidence value and its exact identity.

    ``task_identity`` binds this fact to the one task whose compiled inputs
    produced it; same-schema evidence prepared for a different task cannot
    close this proof.
    """

    task_identity: str
    claim: str
    schema: str
    reference: Reference
    binding_reference: Reference | None = None
    consultations: tuple[Reference, ...] = ()


@dataclass(frozen=True, slots=True)
class Capability:
    """
    Names one scientifically qualified ability.
    """

    name: str


@dataclass(frozen=True, slots=True)
class Binding:
    """
    Selects one exact realization for one qualified capability.
    """

    capability: str
    reference: Reference
    capacity_scope: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class Task:
    """
    Describes one immutable operation ready under exact prerequisites.

    ``identity`` derives from the proof meaning, target claim and method,
    immutable brief and resolved-design inputs, prerequisite evidence
    references, exact consultations, and the selected binding and capacity
    scope when its method requires them.
    """

    proof_identity: str
    claim: str
    method: str
    schema: str
    brief_identity: str
    design_identity: str
    prerequisite_evidence: tuple[Reference, ...]
    consultations: tuple[Reference, ...]
    binding_reference: Reference | None
    capacity_scope: str | None

    @property
    def identity(self) -> str:
        """
        Return the canonical digest of this task's complete bound meaning.
        """

        payload = encode_bytes(
            {
                "proof_identity": self.proof_identity,
                "claim": self.claim,
                "method": self.method,
                "brief_identity": self.brief_identity,
                "design_identity": self.design_identity,
                "prerequisite_evidence": [
                    reference.as_mapping()
                    for reference in self.prerequisite_evidence
                ],
                "consultations": [
                    reference.as_mapping()
                    for reference in self.consultations
                ],
                "binding_reference": (
                    None
                    if self.binding_reference is None
                    else self.binding_reference.as_mapping()
                ),
                "capacity_scope": self.capacity_scope,
            }
        )
        return _identity_digest(payload)


@dataclass(frozen=True, slots=True)
class Study:
    """
    Captures one immutable compilation over exact known facts.
    """

    brief: Brief
    brief_identity: str
    advice: tuple[Advice, ...]
    design: Design
    route: Route
    proof: Proof
    evidence: tuple[Evidence, ...]
    capabilities: tuple[Capability, ...]
    bindings: tuple[Binding, ...]
    ready_tasks: tuple[Task, ...]
    findings: tuple[Finding, ...]

    def __post_init__(self) -> None:
        """
        Require one complete, internally coherent scientific snapshot.
        """

        _validate_study(self)

    def document(self) -> Document:
        """
        Return the sole canonical document for this scientific state.
        """

        return Document(
            STUDY_SCHEMA,
            {
                "advice": {
                    f"advice_{index:03d}": canonicalize(
                        item.canonical_value()
                    )
                    for index, item in enumerate(self.advice, start=1)
                },
                "bindings": {
                    f"binding_{index:03d}": {
                        "capability": binding.capability,
                        "capacity_scope": binding.capacity_scope,
                        "reference": binding.reference.as_mapping(),
                    }
                    for index, binding in enumerate(
                        self.bindings,
                        start=1,
                    )
                },
                "brief": canonicalize(self.brief.canonical_value()),
                "brief_identity": self.brief_identity,
                "capabilities": [
                    capability.name for capability in self.capabilities
                ],
                "design": canonicalize(self.design.canonical_value()),
                "evidence": {
                    f"evidence_{index:03d}": {
                        "binding_reference": (
                            None
                            if item.binding_reference is None
                            else item.binding_reference.as_mapping()
                        ),
                        "consultations": _references_value(
                            item.consultations,
                            prefix="consultation",
                        ),
                        "obligation": item.claim,
                        "reference": item.reference.as_mapping(),
                        "schema": item.schema,
                        "task_identity": item.task_identity,
                    }
                    for index, item in enumerate(
                        self.evidence,
                        start=1,
                    )
                },
                "findings": {
                    f"finding_{index:03d}": {
                        "claim": finding.claim,
                        "kind": finding.kind.value,
                        "needs": list(finding.needs),
                        "record_references": _references_value(
                            finding.record_references,
                            prefix="record",
                        ),
                    }
                    for index, finding in enumerate(
                        self.findings,
                        start=1,
                    )
                },
                "proof": _proof_value(self.proof),
                "ready_tasks": {
                    f"task_{index:03d}": {
                        "binding_reference": (
                            None
                            if task.binding_reference is None
                            else task.binding_reference.as_mapping()
                        ),
                        "brief_identity": task.brief_identity,
                        "capacity_scope": task.capacity_scope,
                        "consultations": _references_value(
                            task.consultations,
                            prefix="consultation",
                        ),
                        "design_identity": task.design_identity,
                        "method": task.method,
                        "obligation": task.claim,
                        "prerequisite_evidence": _references_value(
                            task.prerequisite_evidence,
                            prefix="evidence",
                        ),
                        "proof_identity": task.proof_identity,
                        "schema": task.schema,
                    }
                    for index, task in enumerate(
                        self.ready_tasks,
                        start=1,
                    )
                },
                "route": _route_value(self.route),
            },
        )

    def canonical_bytes(self) -> bytes:
        """
        Encode this study for deterministic comparison and identity.
        """

        return self.document().to_bytes()

    @property
    def identity(self) -> str:
        """
        Identify the complete canonical Study document.
        """

        return _identity_digest(self.canonical_bytes())

    def direct_references(self) -> tuple[Reference, ...]:
        """
        Return every exact reference named directly by this Study.
        """

        ordered = (
            *(
                reference
                for advice in self.advice
                for reference in _references_in_value(
                    advice.canonical_value()
                )
            ),
            *(binding.reference for binding in self.bindings),
            *(
                reference
                for fact in self.evidence
                for reference in (
                    fact.binding_reference,
                    fact.reference,
                    *fact.consultations,
                )
                if reference is not None
            ),
            *(
                reference
                for task in self.ready_tasks
                for reference in (
                    *task.prerequisite_evidence,
                    *task.consultations,
                    task.binding_reference,
                )
                if reference is not None
            ),
            *(
                reference
                for finding in self.findings
                for reference in finding.record_references
            ),
        )
        return tuple(dict.fromkeys(ordered))

    @classmethod
    def from_document(cls, document: Document) -> Study:
        """
        Strictly restore generic science without selecting an aim consumer.
        """

        captured = Document.from_bytes(document.to_bytes())
        if captured.schema_identifier != STUDY_SCHEMA:
            raise ValueError("study_schema_mismatch")
        values = _mapping(
            captured.values,
            finding="study_document_invalid",
        )
        if set(values) != {
            "advice",
            "bindings",
            "brief",
            "brief_identity",
            "capabilities",
            "design",
            "evidence",
            "findings",
            "proof",
            "ready_tasks",
            "route",
        }:
            raise ValueError("study_document_invalid")
        route = _restore_route(values["route"])
        proof = _restore_proof(values["proof"])
        return cls(
            brief=_restore_brief(values["brief"]),
            brief_identity=_text(
                values["brief_identity"],
                "study_brief_identity_invalid",
            ),
            advice=tuple(
                _restore_advice(value)
                for value in _indexed_values(
                    values["advice"],
                    prefix="advice",
                    finding="study_advice_invalid",
                )
            ),
            design=_restore_design(values["design"]),
            route=route,
            proof=proof,
            evidence=tuple(
                _restore_evidence(value)
                for value in _indexed_values(
                    values["evidence"],
                    prefix="evidence",
                    finding="study_evidence_invalid",
                )
            ),
            capabilities=tuple(
                Capability(
                    _text(value, "study_capability_invalid")
                )
                for value in _sequence(
                    values["capabilities"],
                    "study_capability_invalid",
                )
            ),
            bindings=tuple(
                _restore_binding(value)
                for value in _indexed_values(
                    values["bindings"],
                    prefix="binding",
                    finding="study_binding_invalid",
                )
            ),
            ready_tasks=tuple(
                _restore_task(value)
                for value in _indexed_values(
                    values["ready_tasks"],
                    prefix="task",
                    finding="study_task_invalid",
                )
            ),
            findings=tuple(
                _restore_finding(value)
                for value in _indexed_values(
                    values["findings"],
                    prefix="finding",
                    finding="study_finding_invalid",
                )
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class _RestoredBrief(Brief):
    """
    Preserve one aim-owned brief subtree without interpreting its language.
    """

    _encoded_value: bytes = field(repr=False, compare=False)

    def canonical_value(self) -> Any:
        return json.loads(self._encoded_value)


@dataclass(frozen=True, slots=True, kw_only=True)
class _RestoredDesign(Design):
    """
    Preserve one aim-owned design subtree without importing its owner.
    """

    _encoded_value: bytes = field(repr=False, compare=False)

    def canonical_value(self) -> Any:
        return json.loads(self._encoded_value)


@dataclass(frozen=True, slots=True)
class _RestoredAdvice:
    """
    Preserve one aim-owned advice subtree behind the structural interface.
    """

    _encoded_value: bytes = field(repr=False, compare=False)

    def canonical_value(self) -> Any:
        return json.loads(self._encoded_value)


def _route_value(route: Route) -> dict[str, object]:
    return {
        "aim": route.aim,
        "applicability": route.applicability,
        "choices": {
            f"choice_{index:03d}": {
                "claim": choice.claim,
                "method": choice.method,
                "requires": list(choice.requires),
            }
            for index, choice in enumerate(route.choices, start=1)
        },
        "objectives": list(route.objectives),
    }


def _proof_value(proof: Proof) -> dict[str, object]:
    return {
        "obligations": {
            f"obligation_{index:03d}": {
                "capability": claim.capability,
                "name": claim.name,
                "requires": list(claim.requires),
                "schema": claim.schema,
            }
            for index, claim in enumerate(proof.claims, start=1)
        },
        "route": _route_value(proof.route),
        "terminals": list(proof.terminal_claims),
    }


def _references_value(
    references: tuple[Reference, ...],
    *,
    prefix: str,
) -> dict[str, object]:
    return {
        f"{prefix}_{index:03d}": reference.as_mapping()
        for index, reference in enumerate(references, start=1)
    }


def _references_in_value(value: object) -> tuple[Reference, ...]:
    canonical = canonicalize(value)
    if isinstance(canonical, Mapping):
        if set(canonical) == {
            "content_hash",
            "media_type",
            "metadata_content_hash",
            "size_bytes",
        }:
            try:
                return (Reference.from_mapping(canonical),)
            except (KeyError, TypeError, ValueError):
                return ()
        return tuple(
            reference
            for child in canonical.values()
            for reference in _references_in_value(child)
        )
    if isinstance(canonical, list):
        return tuple(
            reference
            for child in canonical
            for reference in _references_in_value(child)
        )
    return ()


def _validate_study(study: Study) -> None:
    if study.brief_identity != _identity_digest(
        study.brief.canonical_bytes()
    ):
        raise ValueError("study_brief_identity_mismatch")
    if study.route != study.proof.route:
        raise ValueError("study_proof_mismatch")
    if (
        study.route.aim != study.brief.aim
        or study.route.aim != study.design.aim
        or study.route.objectives != study.brief.objectives
        or study.route.objectives != study.design.objectives
    ):
        raise ValueError("study_route_mismatch")

    claims = {claim.name: claim for claim in study.proof.claims}
    if len(claims) != len(study.proof.claims):
        raise ValueError("study_claim_duplicate")
    if (
        len(set(study.proof.terminal_claims))
        != len(study.proof.terminal_claims)
        or any(
            terminal not in claims
            for terminal in study.proof.terminal_claims
        )
    ):
        raise ValueError("study_terminal_invalid")
    choices = {choice.claim: choice for choice in study.route.choices}
    if (
        len(choices) != len(study.route.choices)
        or set(choices) != set(claims)
        or any(
            choices[name].requires != claim.requires
            for name, claim in claims.items()
        )
    ):
        raise ValueError("study_proof_mismatch")

    advice_identities = tuple(
        encode_bytes(item.canonical_value())
        for item in study.advice
    )
    if len(set(advice_identities)) != len(advice_identities):
        raise ValueError("study_advice_duplicate")

    proof_capabilities = {
        claim.capability
        for claim in study.proof.claims
        if claim.capability is not None
    }
    capability_names = tuple(
        capability.name for capability in study.capabilities
    )
    if (
        len(set(capability_names)) != len(capability_names)
        or any(name not in proof_capabilities for name in capability_names)
    ):
        raise ValueError("study_capability_invalid")
    bindings = {
        binding.capability: binding for binding in study.bindings
    }
    if (
        len(bindings) != len(study.bindings)
        or any(
            capability not in capability_names
            for capability in bindings
        )
    ):
        raise ValueError("study_binding_invalid")

    evidence = {fact.claim: fact for fact in study.evidence}
    if len(evidence) != len(study.evidence):
        raise ValueError("study_evidence_duplicate")
    if tuple(evidence) != tuple(
        claim.name
        for claim in study.proof.claims
        if claim.name in evidence
    ):
        raise ValueError("study_evidence_order_invalid")
    for claim_name, fact in evidence.items():
        claim = claims.get(claim_name)
        choice = choices.get(claim_name)
        binding = (
            None
            if claim is None or claim.capability is None
            else bindings.get(claim.capability)
        )
        has_prerequisites = (
            claim is not None
            and all(name in evidence for name in claim.requires)
        )
        expected_task = (
            Task(
                proof_identity=study.proof.identity,
                claim=claim.name,
                method=choice.method,
                schema=claim.schema,
                brief_identity=study.brief_identity,
                design_identity=_identity_digest(
                    encode_bytes(study.design.canonical_value())
                ),
                prerequisite_evidence=tuple(
                    evidence[name].reference for name in claim.requires
                ),
                consultations=fact.consultations,
                binding_reference=(
                    None if binding is None else binding.reference
                ),
                capacity_scope=(
                    None if binding is None else binding.capacity_scope
                ),
            )
            if claim is not None
            and choice is not None
            and has_prerequisites
            else None
        )
        if (
            claim is None
            or fact.schema != claim.schema
            or not has_prerequisites
            or len(set(fact.consultations)) != len(fact.consultations)
            or expected_task is None
            or fact.task_identity != expected_task.identity
            or fact.binding_reference
            != (None if binding is None else binding.reference)
            or (
                fact.binding_reference is not None
                and (
                    claim.capability is None
                    or claim.capability not in bindings
                    or bindings[claim.capability].reference
                    != fact.binding_reference
                )
            )
        ):
            raise ValueError("study_evidence_invalid")

    tasks = {task.claim: task for task in study.ready_tasks}
    if len(tasks) != len(study.ready_tasks):
        raise ValueError("study_task_duplicate")
    if tuple(tasks) != tuple(
        claim.name
        for claim in study.proof.claims
        if claim.name in tasks
    ):
        raise ValueError("study_task_order_invalid")
    design_identity = _identity_digest(
        encode_bytes(study.design.canonical_value())
    )
    for claim_name, task in tasks.items():
        claim = claims.get(claim_name)
        choice = choices.get(claim_name)
        binding = (
            None
            if claim is None or claim.capability is None
            else bindings.get(claim.capability)
        )
        if (
            claim is None
            or choice is None
            or task.proof_identity != study.proof.identity
            or task.brief_identity != study.brief_identity
            or task.design_identity != design_identity
            or task.method != choice.method
            or task.schema != claim.schema
            or task.prerequisite_evidence
            != tuple(evidence[name].reference for name in claim.requires)
            or task.binding_reference
            != (None if binding is None else binding.reference)
            or task.capacity_scope
            != (None if binding is None else binding.capacity_scope)
        ):
            raise ValueError("study_task_invalid")

    findings = {finding.claim: finding for finding in study.findings}
    if len(findings) != len(study.findings):
        raise ValueError("study_finding_duplicate")
    if tuple(findings) != tuple(
        claim.name
        for claim in study.proof.claims
        if claim.name in findings
    ):
        raise ValueError("study_finding_order_invalid")
    if any(claim not in claims for claim in findings):
        raise ValueError("study_finding_invalid")
    states = set(evidence) | set(tasks) | set(findings)
    if (
        states != set(claims)
        or set(evidence) & set(tasks)
        or set(evidence) & set(findings)
        or set(tasks) & set(findings)
    ):
        raise ValueError("study_claim_state_invalid")


def _restore_brief(value: object) -> Brief:
    values = _mapping(value, finding="study_brief_invalid")
    if "name" in values:
        raise ValueError("study_brief_invalid")
    required = {
        "aim",
        "budget",
        "objectives",
        "omissions",
        "wording",
    }
    if not required <= set(values):
        raise ValueError("study_brief_invalid")
    return _RestoredBrief(
        wording=_text(values["wording"], "study_brief_invalid"),
        aim=_text(values["aim"], "study_brief_invalid"),
        objectives=_text_tuple(
            values["objectives"],
            "study_brief_invalid",
        ),
        budget=_text(values["budget"], "study_brief_invalid"),
        omissions=_text_tuple(
            values["omissions"],
            "study_brief_invalid",
        ),
        _encoded_value=encode_bytes(values),
    )


def _restore_design(value: object) -> Design:
    values = _mapping(value, finding="study_design_invalid")
    if "name" in values:
        raise ValueError("study_design_invalid")
    required = {"aim", "budget", "objectives"}
    if not required <= set(values):
        raise ValueError("study_design_invalid")
    if "capabilities" not in values:
        raise ValueError("study_design_invalid")
    return _RestoredDesign(
        aim=_text(values["aim"], "study_design_invalid"),
        objectives=_text_tuple(
            values["objectives"],
            "study_design_invalid",
        ),
        capabilities=_text_tuple(
            values["capabilities"],
            "study_design_invalid",
        ),
        budget=_text(values["budget"], "study_design_invalid"),
        _encoded_value=encode_bytes(values),
    )


def _restore_advice(value: object) -> Advice:
    values = _mapping(value, finding="study_advice_invalid")
    return _RestoredAdvice(
        _encoded_value=encode_bytes(values),
    )


def _restore_route(value: object) -> Route:
    values = _mapping(value, finding="study_route_invalid")
    if set(values) != {
        "aim",
        "applicability",
        "choices",
        "objectives",
    }:
        raise ValueError("study_route_invalid")
    return Route(
        aim=_text(values["aim"], "study_route_invalid"),
        objectives=_text_tuple(
            values["objectives"],
            "study_route_invalid",
        ),
        applicability=_text(
            values["applicability"],
            "study_route_invalid",
        ),
        choices=tuple(
            _restore_route_choice(item)
            for item in _indexed_values(
                values["choices"],
                prefix="choice",
                finding="study_route_invalid",
            )
        ),
    )


def _restore_route_choice(value: object) -> RouteChoice:
    values = _mapping(value, finding="study_route_invalid")
    if set(values) != {"claim", "method", "requires"}:
        raise ValueError("study_route_invalid")
    return RouteChoice(
        claim=_text(values["claim"], "study_route_invalid"),
        method=_text(values["method"], "study_route_invalid"),
        requires=_text_tuple(
            values["requires"],
            "study_route_invalid",
        ),
    )


def _restore_proof(value: object) -> Proof:
    values = _mapping(value, finding="study_proof_invalid")
    if set(values) != {"obligations", "route", "terminals"}:
        raise ValueError("study_proof_invalid")
    return Proof(
        route=_restore_route(values["route"]),
        terminal_claims=_text_tuple(
            values["terminals"],
            "study_proof_invalid",
        ),
        claims=tuple(
            _restore_claim(item)
            for item in _indexed_values(
                values["obligations"],
                prefix="obligation",
                finding="study_proof_invalid",
            )
        ),
    )


def _restore_claim(value: object) -> Claim:
    values = _mapping(value, finding="study_proof_invalid")
    if set(values) != {"capability", "name", "requires", "schema"}:
        raise ValueError("study_proof_invalid")
    return Claim(
        name=_text(values["name"], "study_proof_invalid"),
        requires=_text_tuple(
            values["requires"],
            "study_proof_invalid",
        ),
        capability=_optional_text(
            values["capability"],
            "study_proof_invalid",
        ),
        schema=_text(values["schema"], "study_proof_invalid"),
    )


def _restore_evidence(value: object) -> Evidence:
    values = _mapping(value, finding="study_evidence_invalid")
    if set(values) != {
        "binding_reference",
        "consultations",
        "obligation",
        "reference",
        "schema",
        "task_identity",
    }:
        raise ValueError("study_evidence_invalid")
    return Evidence(
        task_identity=_text(
            values["task_identity"],
            "study_evidence_invalid",
        ),
        claim=_text(values["obligation"], "study_evidence_invalid"),
        schema=_text(values["schema"], "study_evidence_invalid"),
        reference=_reference(
            values["reference"],
            "study_evidence_invalid",
        ),
        binding_reference=_optional_reference(
            values["binding_reference"],
            "study_evidence_invalid",
        ),
        consultations=tuple(
            _reference(item, "study_evidence_invalid")
            for item in _indexed_values(
                values["consultations"],
                prefix="consultation",
                finding="study_evidence_invalid",
            )
        ),
    )


def _restore_binding(value: object) -> Binding:
    values = _mapping(value, finding="study_binding_invalid")
    if set(values) != {"capability", "capacity_scope", "reference"}:
        raise ValueError("study_binding_invalid")
    return Binding(
        capability=_text(
            values["capability"],
            "study_binding_invalid",
        ),
        reference=_reference(
            values["reference"],
            "study_binding_invalid",
        ),
        capacity_scope=_optional_text(
            values["capacity_scope"],
            "study_binding_invalid",
        ),
    )


def _restore_task(value: object) -> Task:
    values = _mapping(value, finding="study_task_invalid")
    if set(values) != {
        "binding_reference",
        "brief_identity",
        "capacity_scope",
        "consultations",
        "design_identity",
        "method",
        "obligation",
        "prerequisite_evidence",
        "proof_identity",
        "schema",
    }:
        raise ValueError("study_task_invalid")
    return Task(
        proof_identity=_text(
            values["proof_identity"],
            "study_task_invalid",
        ),
        claim=_text(values["obligation"], "study_task_invalid"),
        method=_text(values["method"], "study_task_invalid"),
        schema=_text(values["schema"], "study_task_invalid"),
        brief_identity=_text(
            values["brief_identity"],
            "study_task_invalid",
        ),
        design_identity=_text(
            values["design_identity"],
            "study_task_invalid",
        ),
        prerequisite_evidence=tuple(
            _reference(item, "study_task_invalid")
            for item in _indexed_values(
                values["prerequisite_evidence"],
                prefix="evidence",
                finding="study_task_invalid",
            )
        ),
        consultations=tuple(
            _reference(item, "study_task_invalid")
            for item in _indexed_values(
                values["consultations"],
                prefix="consultation",
                finding="study_task_invalid",
            )
        ),
        binding_reference=_optional_reference(
            values["binding_reference"],
            "study_task_invalid",
        ),
        capacity_scope=_optional_text(
            values["capacity_scope"],
            "study_task_invalid",
        ),
    )


def _restore_finding(value: object) -> Finding:
    values = _mapping(value, finding="study_finding_invalid")
    if set(values) != {
        "claim",
        "kind",
        "needs",
        "record_references",
    }:
        raise ValueError("study_finding_invalid")
    try:
        kind = FindingKind(
            _text(values["kind"], "study_finding_invalid")
        )
    except ValueError as error:
        raise ValueError("study_finding_invalid") from error
    return Finding(
        claim=_text(values["claim"], "study_finding_invalid"),
        kind=kind,
        needs=_text_tuple(
            values["needs"],
            "study_finding_invalid",
        ),
        record_references=tuple(
            _reference(item, "study_finding_invalid")
            for item in _indexed_values(
                values["record_references"],
                prefix="record",
                finding="study_finding_invalid",
            )
        ),
    )


def _mapping(value: object, *, finding: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(finding)
    return value


def _sequence(value: object, finding: str) -> tuple[object, ...]:
    if not isinstance(value, list):
        raise ValueError(finding)
    return tuple(value)


def _indexed_values(
    value: object,
    *,
    prefix: str,
    finding: str,
) -> tuple[object, ...]:
    values = _mapping(value, finding=finding)
    expected = tuple(
        f"{prefix}_{index:03d}"
        for index in range(1, len(values) + 1)
    )
    if tuple(values) != expected:
        raise ValueError(finding)
    return tuple(values[key] for key in expected)


def _text(value: object, finding: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(finding)
    return value


def _optional_text(value: object, finding: str) -> str | None:
    if value is None:
        return None
    return _text(value, finding)


def _text_tuple(value: object, finding: str) -> tuple[str, ...]:
    return tuple(
        _text(item, finding)
        for item in _sequence(value, finding)
    )


def _reference(value: object, finding: str) -> Reference:
    values = _mapping(value, finding=finding)
    if set(values) != {
        "content_hash",
        "media_type",
        "metadata_content_hash",
        "size_bytes",
    }:
        raise ValueError(finding)
    try:
        return Reference.from_mapping(values)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(finding) from error


def _optional_reference(
    value: object,
    finding: str,
) -> Reference | None:
    return None if value is None else _reference(value, finding)


def _is_identity(value: str) -> bool:
    return (
        value.startswith("sha256:")
        and len(value) == len("sha256:") + 64
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def _identity_digest(payload: bytes) -> str:
    """
    Return the canonical sha256 digest form used by all science identity.
    """

    return f"sha256:{hashlib.sha256(payload).hexdigest()}"
