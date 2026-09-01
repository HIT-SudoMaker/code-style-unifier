from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
import hashlib

from ...authority.protocol import Document, Reference
from ...authority.session import AuthoritySession
from ..brief import Brief
from ...canonical import encode_bytes
from ..study import Finding, FindingKind, Study

FRONTIER_SCHEMA = "metacraft.science.metalens.study_frontier"


@dataclass(frozen=True, slots=True)
class StudyFrontier:
    """
    Own one ordered, identity-distinct family of complete metalens Studies.

    This is a package-private lifecycle value. It is intentionally absent
    from every package export; conduct is its only production caller.
    """

    studies: tuple[Study, ...]

    def __post_init__(self) -> None:
        """
        Require one non-empty, distinct frontier for a single brief.
        """

        if not isinstance(self.studies, tuple) or not self.studies:
            raise ValueError("frontier_studies_empty")
        identities = tuple(study.identity for study in self.studies)
        if len(set(identities)) != len(identities):
            raise ValueError("frontier_study_duplicate")
        brief_identity = self.studies[0].brief_identity
        if any(study.brief_identity != brief_identity for study in self.studies):
            raise ValueError("frontier_brief_mismatch")

    @classmethod
    def start(cls, study: Study) -> StudyFrontier:
        """
        Start one fresh scientific lineage.
        """

        return cls((study,))

    @property
    def brief_identity(self) -> str:
        """
        Return the exact brief shared by every live Study.
        """

        return self.studies[0].brief_identity

    @property
    def key(self) -> str:
        """
        Name the sole current checkpoint for this brief.
        """

        return f"study_frontier:{self.brief_identity}"

    def replace(
        self,
        predecessor_identity: str,
        successors: tuple[Study, ...],
    ) -> StudyFrontier:
        """
        Replace exactly one live Study with ordered monotonic successors.

        Canonically identical lineages collapse at their first position, so
        convergence cannot duplicate one future conclusion.
        """

        positions = tuple(
            index
            for index, study in enumerate(self.studies)
            if study.identity == predecessor_identity
        )
        if not positions:
            raise RuntimeError("frontier_study_missing")
        if len(positions) != 1:
            raise RuntimeError("frontier_study_duplicate")
        if not isinstance(successors, tuple) or not successors:
            raise ValueError("frontier_successors_empty")
        position = positions[0]
        predecessor = self.studies[position]
        for successor in successors:
            if successor.identity == predecessor.identity:
                raise RuntimeError("frontier_successor_unchanged")
            if (
                successor.brief_identity != predecessor.brief_identity
                or successor.brief.canonical_bytes()
                != predecessor.brief.canonical_bytes()
            ):
                raise RuntimeError("frontier_brief_changed")
            if encode_bytes(successor.design.canonical_value()) != encode_bytes(
                predecessor.design.canonical_value()
            ):
                raise RuntimeError("frontier_design_changed")
            if (
                successor.route != predecessor.route
                or successor.proof != predecessor.proof
            ):
                raise RuntimeError("frontier_proof_changed")
            if not self._advice_is_preserved(predecessor, successor):
                raise RuntimeError("frontier_advice_lost")
            if not self._items_are_preserved(
                predecessor.evidence,
                successor.evidence,
            ):
                raise RuntimeError("frontier_evidence_lost")
            if not self._items_are_preserved(
                predecessor.capabilities,
                successor.capabilities,
            ):
                raise RuntimeError("frontier_capability_lost")
            if not self._items_are_preserved(
                predecessor.bindings,
                successor.bindings,
            ):
                raise RuntimeError("frontier_binding_lost")
            lost_findings = tuple(
                finding
                for finding in predecessor.findings
                if not self._finding_is_accounted_for(finding, successor)
            )
            if lost_findings:
                lost = lost_findings[0]
                raise RuntimeError(
                    "frontier_finding_lost:"
                    f"{lost.claim}:{lost.kind.value}:{','.join(lost.needs)}"
                )
        candidates = (
            *self.studies[:position],
            *successors,
            *self.studies[position + 1 :],
        )
        distinct: list[Study] = []
        identities: set[str] = set()
        for study in candidates:
            if study.identity in identities:
                continue
            identities.add(study.identity)
            distinct.append(study)
        return StudyFrontier(tuple(distinct))

    def _advice_is_preserved(
        self,
        predecessor: Study,
        successor: Study,
    ) -> bool:
        """
        Report whether every predecessor consultation survives replacement.
        """

        successor_values = tuple(
            encode_bytes(advice.canonical_value()) for advice in successor.advice
        )
        return all(
            encode_bytes(advice.canonical_value()) in successor_values
            for advice in predecessor.advice
        )

    def _items_are_preserved(
        self,
        previous: tuple[object, ...],
        current: tuple[object, ...],
    ) -> bool:
        """
        Report whether every predecessor item survives replacement.
        """

        return all(item in current for item in previous)

    def _finding_is_accounted_for(
        self,
        finding: Finding,
        successor: Study,
    ) -> bool:
        """
        Report whether one prior finding remains or has been answered.
        """

        return (
            finding in successor.findings
            or self._prerequisites_advanced(finding, successor)
            or any(evidence.claim == finding.claim for evidence in successor.evidence)
            or any(task.claim == finding.claim for task in successor.ready_tasks)
        )

    def _prerequisites_advanced(
        self,
        finding: Finding,
        successor: Study,
    ) -> bool:
        """
        Report strict, evidenced progress on one prerequisite finding.
        """

        if finding.kind is not FindingKind.PREREQUISITE:
            return False
        evidence_claims = {evidence.claim for evidence in successor.evidence}
        previous_needs = set(finding.needs)
        current = next(
            (
                candidate
                for candidate in successor.findings
                if candidate.claim == finding.claim
            ),
            None,
        )
        if current is None:
            return False
        if current.kind is not FindingKind.PREREQUISITE:
            return previous_needs <= evidence_claims
        current_needs = set(current.needs)
        resolved = previous_needs - current_needs
        return (
            bool(resolved)
            and current_needs < previous_needs
            and resolved <= evidence_claims
        )

    def document(self) -> Document:
        """
        Encode the complete frontier in one strict canonical checkpoint.
        """

        return Document(
            FRONTIER_SCHEMA,
            {
                "brief_identity": self.brief_identity,
                "studies": {
                    f"study_{index:03d}": study.document().as_mapping()
                    for index, study in enumerate(self.studies, start=1)
                },
            },
        )

    def references(self) -> tuple[Reference, ...]:
        """
        Return every exact reference needed by every checkpointed Study.
        """

        return tuple(
            dict.fromkeys(
                reference
                for study in self.studies
                for reference in study.direct_references()
            )
        )

    @classmethod
    def from_document(
        cls,
        document: Document,
        *,
        brief: Brief,
        session: AuthoritySession,
    ) -> StudyFrontier:
        """
        Strictly restore and scientifically recompile one complete frontier.
        """

        try:
            captured = Document.from_bytes(document.to_bytes())
            if captured.schema_identifier != FRONTIER_SCHEMA:
                raise ValueError("study_frontier_schema_mismatch")
            values = _mapping(captured.values)
            if set(values) != {"brief_identity", "studies"}:
                raise ValueError("study_frontier_shape_invalid")
            brief_identity = _text(values["brief_identity"])
            expected_brief_identity = _brief_identity(brief)
            if brief_identity != expected_brief_identity:
                raise ValueError("study_frontier_brief_mismatch")
            encoded_studies = _mapping(values["studies"])
            expected_keys = tuple(
                f"study_{index:03d}" for index in range(1, len(encoded_studies) + 1)
            )
            if not expected_keys or tuple(encoded_studies) != expected_keys:
                raise ValueError("study_frontier_shape_invalid")
            studies = tuple(
                _restore_study(
                    encoded_studies[key],
                    brief=brief,
                    brief_identity=brief_identity,
                    session=session,
                )
                for key in expected_keys
            )
            return cls(studies)
        except (TypeError, ValueError) as error:
            raise ValueError("study_frontier_invalid") from error


def _restore_study(
    value: object,
    *,
    brief: Brief,
    brief_identity: str,
    session: AuthoritySession,
) -> Study:
    encoded = _mapping(value)
    if set(encoded) != {"schema_identifier", "values"}:
        raise ValueError("study_frontier_shape_invalid")
    restored = Study.from_document(Document.from_bytes(encode_bytes(encoded)))
    if restored.brief_identity != brief_identity:
        raise ValueError("study_frontier_brief_mismatch")
    from .evidence import MetalensEvidence

    recompiled = MetalensEvidence(session).recompile(
        replace(restored, brief=brief)
    )
    if recompiled.canonical_bytes() != restored.canonical_bytes():
        raise ValueError("study_frontier_study_mismatch")
    return recompiled


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("study_frontier_shape_invalid")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("study_frontier_shape_invalid")
    return value


def _brief_identity(brief: Brief) -> str:
    return f"sha256:{hashlib.sha256(brief.canonical_bytes()).hexdigest()}"
