from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Protocol

from ..authority.protocol import Document, Reference
from ..authority.reference import reference_matches
from ..canonical import canonicalize, encode_bytes

from .brief import Brief
from .study import Study


BRIEF_SCHEMA = "metacraft.science.brief"
DESIGN_SCHEMA = "metacraft.science.design"
STUDY_CLOSURE_SCHEMA = "metacraft.science.study_closure"
Fetch = Callable[[Reference], bytes]


class _ScientificConclusion(Protocol):
    @property
    def closure(self) -> ResultClosure:
        """
        Return the admitted Study closure behind this conclusion.
        """

        ...

    def document(self) -> Document:
        """
        Return the canonical scientific conclusion document.
        """

        ...

    def references(self) -> tuple[Reference, ...]:
        """
        Return every direct scientific source exactly once.
        """

        ...


class _ConclusionRestorer(Protocol):
    def __call__(
        self,
        document: Document,
        *,
        fetch: Fetch,
    ) -> _ScientificConclusion:
        """
        Restore one aim-owned conclusion from its canonical document.
        """

        ...


class EvidenceOrigin(str, Enum):
    """
    Names whether one scientific fact came from native or synthetic evidence.
    """

    NATIVE = "native"
    SYNTHETIC = "synthetic"


@dataclass(frozen=True, slots=True)
class BoundDocument:
    """
    Couples canonical document bytes to their exact authority reference.
    """

    reference: Reference
    document: Document
    _body: bytes = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """
        Freeze and verify the referenced document bytes.
        """

        body = self.document.to_bytes()
        if not reference_matches(self.reference, body):
            raise ValueError("document_reference_mismatch")
        object.__setattr__(self, "document", Document.from_bytes(body))
        object.__setattr__(self, "_body", body)

    def matches(self, document: Document) -> bool:
        """
        Compare against the immutable bytes captured at construction.
        """

        return self._body == document.to_bytes()


def brief_document(brief: Brief) -> Document:
    """
    Preserve the complete user brief behind its compiled identity.
    """

    return Document(BRIEF_SCHEMA, canonicalize(brief.canonical_value()))


def design_document(
    compiled: Study,
    brief_reference: Reference,
) -> Document:
    """
    Bind one resolved design to the exact brief it interprets.
    """

    return Document(
        DESIGN_SCHEMA,
        {
            "brief": brief_reference.as_mapping(),
            "design": canonicalize(compiled.design.canonical_value()),
        },
    )


def study_document(
    compiled: Study,
    brief_reference: Reference,
    design_reference: Reference,
) -> Document:
    """
    Bind one compiled snapshot to its complete direct reference closure.
    """

    return Document(
        STUDY_CLOSURE_SCHEMA,
        {
            "brief": brief_reference.as_mapping(),
            "design": design_reference.as_mapping(),
            "study": compiled.document().as_mapping(),
        },
    )


def require_exact_evidence(
    compiled: Study,
    claim: str,
    document: Document,
) -> Reference:
    """
    Require one compiled fact to address the exact generated document.
    """

    facts = tuple(
        fact for fact in compiled.evidence
        if fact.claim == claim
    )
    if len(facts) != 1:
        raise ValueError(f"{claim}_evidence_missing")
    reference = facts[0].reference
    try:
        BoundDocument(reference, document)
    except ValueError as error:
        raise ValueError(f"{claim}_evidence_mismatch") from error
    return reference


@dataclass(frozen=True, slots=True)
class Result:
    """
    Holds one admitted scientific conclusion and its complete Study closure.

    External benchmark comparison reads scientific inputs through
    ``closure.compiled``; case identity and published truth never enter this
    production value.
    """

    reference: Reference
    document: Document
    sources: tuple[Reference, ...]
    closure: ResultClosure

    def __post_init__(self) -> None:
        """
        Freeze exact conclusion bytes and require its admitted Study source.
        """

        body = self.document.to_bytes()
        if not reference_matches(self.reference, body):
            raise ValueError("result_reference_mismatch")
        if len(set(self.sources)) != len(self.sources):
            raise ValueError("result_source_duplicate")
        if self.closure.study.reference not in self.sources:
            raise ValueError("result_provenance_incomplete")
        object.__setattr__(self, "document", Document.from_bytes(body))


@dataclass(frozen=True, slots=True)
class ResultClosure:
    """
    Binds one conclusion to its exact compiled authority closure.
    """

    brief: BoundDocument
    design: BoundDocument
    study: BoundDocument
    bindings: tuple[Reference, ...]
    evidence: tuple[Reference, ...]

    @property
    def brief_identity(self) -> str:
        """
        Return the compiled identity of the exact closed brief values.
        """

        return (
            "sha256:"
            + hashlib.sha256(
                encode_bytes(self.brief.document.values)
            ).hexdigest()
        )

    @classmethod
    def bind(
        cls,
        compiled: Study,
        *,
        brief: BoundDocument,
        design: BoundDocument,
        study: BoundDocument,
    ) -> ResultClosure:
        """
        Close one compiled study over exactly the facts it names.
        """

        closure = cls(
            brief=brief,
            design=design,
            study=study,
            bindings=_required_bindings(compiled),
            evidence=tuple(fact.reference for fact in compiled.evidence),
        )
        closure.validate(compiled)
        return closure

    @classmethod
    def restore(
        cls,
        study_reference: Reference,
        *,
        fetch: Fetch,
    ) -> ResultClosure:
        """
        Restore one complete immutable closure without recompiling its study.
        """

        study = _fetch_document(fetch, study_reference)
        if study.schema_identifier != STUDY_CLOSURE_SCHEMA:
            raise ValueError("result_study_mismatch")
        values = _mapping(study.values, "result_study_mismatch")
        if set(values) != {"brief", "design", "study"}:
            raise ValueError("result_study_mismatch")
        brief_reference = _reference(values["brief"])
        design_reference = _reference(values["design"])
        brief = _fetch_document(fetch, brief_reference)
        design = _fetch_document(fetch, design_reference)
        compiled = _restore_closure_study(study)
        _validate_restored_closure(
            compiled,
            brief=brief,
            brief_reference=brief_reference,
            design=design,
            design_reference=design_reference,
        )
        evidence = tuple(fact.reference for fact in compiled.evidence)
        bindings = _required_bindings(compiled)
        direct = tuple(
            dict.fromkeys(
                (
                    brief_reference,
                    design_reference,
                    *compiled.direct_references(),
                )
            )
        )
        for reference in direct:
            body = fetch(reference)
            if not reference_matches(reference, body):
                raise ValueError("result_closure_reference_mismatch")
        return cls(
            brief=BoundDocument(brief_reference, brief),
            design=BoundDocument(design_reference, design),
            study=BoundDocument(study_reference, study),
            bindings=bindings,
            evidence=evidence,
        )

    def validate(self, compiled: Study) -> None:
        """
        Require a result-ready study and its complete admitted closure.
        """

        evidence = {fact.claim for fact in compiled.evidence}
        if (
            compiled.ready_tasks
            or compiled.findings
            or any(
                terminal not in evidence
                for terminal in compiled.proof.terminal_claims
            )
        ):
            raise ValueError("study_not_ready_for_result")
        if self.brief.document.schema_identifier != BRIEF_SCHEMA:
            raise ValueError("result_brief_mismatch")
        # The compiler identifies the canonical brief values, not its document
        # envelope.
        if (
            "sha256:"
            + hashlib.sha256(
                encode_bytes(self.brief.document.values)
            ).hexdigest()
            != compiled.brief_identity
        ):
            raise ValueError("result_brief_mismatch")
        if not self.design.matches(
            design_document(compiled, self.brief.reference)
        ):
            raise ValueError("result_design_mismatch")
        if not self.study.matches(
            study_document(
                compiled,
                self.brief.reference,
                self.design.reference,
            )
        ):
            raise ValueError("result_study_mismatch")
        required_evidence = tuple(
            fact.reference for fact in compiled.evidence
        )
        if self.evidence != required_evidence:
            raise ValueError("result_evidence_closure_mismatch")
        if self.bindings != _required_bindings(compiled):
            raise ValueError("result_binding_closure_mismatch")

    def as_mapping(self) -> dict[str, object]:
        """
        Return the named, exact reference closure.
        """

        return {
            "bindings": {
                f"binding_{index:03d}": reference.as_mapping()
                for index, reference in enumerate(self.bindings, start=1)
            },
            "brief": self.brief.reference.as_mapping(),
            "design": self.design.reference.as_mapping(),
            "evidence": {
                f"evidence_{index:03d}": reference.as_mapping()
                for index, reference in enumerate(self.evidence, start=1)
            },
            "study": self.study.reference.as_mapping(),
        }

    def references(self) -> tuple[Reference, ...]:
        """
        Return the duplicate-free authority closure in mental order.
        """

        ordered = (
            self.brief.reference,
            self.design.reference,
            self.study.reference,
            *self.bindings,
            *self.evidence,
        )
        return tuple(dict.fromkeys(ordered))

    @property
    def compiled(self) -> Study:
        """
        Restore the one canonical Study carried by this closure.
        """

        return _restore_closure_study(self.study.document)


def restore_admitted_result(
    reference: Reference,
    *,
    fetch: Fetch,
    restore_conclusion: _ConclusionRestorer,
) -> Result:
    """
    Restore one admitted Result while leaving aim fields to their owner.
    """

    document = _fetch_document(fetch, reference)
    conclusion = restore_conclusion(document, fetch=fetch)
    if conclusion.document().to_bytes() != document.to_bytes():
        raise ValueError("result_document_mismatch")
    direct_sources = conclusion.references()
    sources = tuple(dict.fromkeys(direct_sources))
    if len(sources) != len(direct_sources):
        raise ValueError("result_source_duplicate")
    return Result(
        reference=reference,
        document=document,
        sources=sources,
        closure=conclusion.closure,
    )


def _required_bindings(compiled: Study) -> tuple[Reference, ...]:
    return tuple(
        dict.fromkeys(
            fact.binding_reference
            for fact in compiled.evidence
            if fact.binding_reference is not None
        )
    )


def _restore_closure_study(document: Document) -> Study:
    """
    Restore the canonical Study nested in one result-closure document.
    """

    if document.schema_identifier != STUDY_CLOSURE_SCHEMA:
        raise ValueError("result_study_mismatch")
    values = _mapping(document.values, "result_study_mismatch")
    if set(values) != {"brief", "design", "study"}:
        raise ValueError("result_study_mismatch")
    encoded = _mapping(values["study"], "result_study_mismatch")
    if set(encoded) != {"schema_identifier", "values"}:
        raise ValueError("result_study_mismatch")
    try:
        study_document = Document.from_bytes(encode_bytes(encoded))
        return Study.from_document(study_document)
    except (TypeError, ValueError) as error:
        raise ValueError("result_study_mismatch") from error


def _validate_restored_closure(
    compiled: Study,
    *,
    brief: Document,
    brief_reference: Reference,
    design: Document,
    design_reference: Reference,
) -> None:
    """
    Prove that one stored Study owns the exact direct closure around it.
    """

    if compiled.ready_tasks or compiled.findings:
        raise ValueError("study_not_ready_for_result")
    if brief.schema_identifier != BRIEF_SCHEMA:
        raise ValueError("result_brief_mismatch")
    if canonicalize(compiled.brief.canonical_value()) != canonicalize(
        brief.values
    ):
        raise ValueError("result_brief_mismatch")
    if (
        "sha256:"
        + hashlib.sha256(encode_bytes(brief.values)).hexdigest()
        != compiled.brief_identity
    ):
        raise ValueError("result_brief_mismatch")
    expected_design = Document(
        DESIGN_SCHEMA,
        {
            "brief": brief_reference.as_mapping(),
            "design": canonicalize(compiled.design.canonical_value()),
        },
    )
    if design_reference == brief_reference or (
        design.schema_identifier != DESIGN_SCHEMA
        or design.to_bytes() != expected_design.to_bytes()
    ):
        raise ValueError("result_design_mismatch")
    evidence_claims = {fact.claim for fact in compiled.evidence}
    if any(
        claim not in evidence_claims
        for claim in compiled.proof.terminal_claims
    ):
        raise ValueError("study_not_ready_for_result")


def _fetch_document(
    fetch: Fetch,
    reference: Reference,
) -> Document:
    body = fetch(reference)
    if not reference_matches(reference, body):
        raise ValueError("document_reference_mismatch")
    try:
        return Document.from_bytes(body)
    except ValueError as error:
        raise ValueError("result_closure_document_invalid") from error


def _reference(value: object) -> Reference:
    mapping = _mapping(value, "result_reference_invalid")
    if set(mapping) != {
        "content_hash",
        "media_type",
        "metadata_content_hash",
        "size_bytes",
    }:
        raise ValueError("result_reference_invalid")
    try:
        return Reference.from_mapping(mapping)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("result_reference_invalid") from error


def _mapping(value: object, finding: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(finding)
    return value
