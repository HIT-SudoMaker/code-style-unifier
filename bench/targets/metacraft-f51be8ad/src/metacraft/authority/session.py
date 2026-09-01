from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from time import sleep
from typing import Any

from .interface import Authority
from .protocol import (
    AuthorityView,
    Decision,
    Document,
    Proposal,
    Reference,
    Structure,
)
from .reference import reference_for


@dataclass(frozen=True, slots=True)
class PermitReservationWaiting:
    """
    Classify one retryable Rust permit admission outcome without text parsing.
    """

    reason: str


class CurrentAdmissionConflict(RuntimeError):
    """
    Report that another session advanced a named current value first.
    """


class AuthoritySession:
    """
    Own one observed Authority head for a related set of Python decisions.
    """

    __slots__ = (
        "_authority",
        "_contention_attempts",
        "_revision",
        "_wait",
    )

    def __init__(
        self,
        authority: Authority,
        *,
        _wait: Callable[[float], object] = sleep,
        _contention_attempts: int = 32,
    ) -> None:
        """
        Begin at the exact head observed from one Authority workspace.
        """

        if _contention_attempts <= 0:
            raise ValueError("authority_contention_attempts_invalid")
        view = authority.view()
        self._authority = authority
        self._contention_attempts = _contention_attempts
        self._revision = view.revision
        self._wait = _wait

    def observe(self) -> AuthorityView:
        """
        Observe and retain the current exact Authority view.
        """

        return self._observe()

    def admit_document(
        self,
        document: Document,
        *,
        references: tuple[Reference, ...] = (),
    ) -> Reference:
        """
        Admit one immutable document and advance to its resulting head.
        """

        sources = tuple(dict.fromkeys(references))
        if sources:
            structure = Structure.for_document(
                document,
                references=sources,
            )
            shape = self._decide(
                Proposal.structure(structure),
                finding="document_structure_rejected",
            )
            assert shape.body_reference is not None
            decision = self._decide(
                Proposal.structured(
                    document,
                    structure_reference=shape.body_reference,
                    references=sources,
                ),
                finding="structured_document_rejected",
            )
        else:
            decision = self._decide(
                Proposal.record(document),
                finding="document_admission_rejected",
            )
        assert decision.body_reference is not None
        return decision.body_reference

    def admit_capacity(
        self,
        *,
        scope: str,
        limit: int,
        qualification_references: tuple[Reference, ...],
        supersedes: Reference | None = None,
    ) -> Reference:
        """
        Admit one current qualified work bound and retain its exact head.
        """

        proposal = Proposal.capacity(
            scope=scope,
            limit=limit,
            qualification_references=qualification_references,
            supersedes=supersedes,
        )
        for _attempt in range(self._contention_attempts):
            decision = self._decide(
                proposal,
                finding="capacity_admission_rejected",
                expected_findings=frozenset(
                    {
                        "capacity_below_open_permits",
                        "current_reference_mismatch",
                    }
                ),
            )
            if decision.admitted:
                assert decision.body_reference is not None
                return decision.body_reference
            if "current_reference_mismatch" in decision.findings:
                current = self.current_reference(f"capacity:{scope}")
                if current is not None and self.fetch(current) == proposal.body:
                    return current
                raise RuntimeError("capacity_admission_conflict")
            self._wait(0.05)
        raise RuntimeError("capacity_open_permits_busy")

    def admit_current(
        self,
        document: Document,
        *,
        key: str,
        supersedes: Reference | None,
        references: tuple[Reference, ...] = (),
        descriptive_metadata: Mapping[str, Any] | None = None,
    ) -> Reference:
        """
        Compare-and-replace one named current value at this session's head.
        """

        sources = tuple(dict.fromkeys(references))
        if sources:
            structure = Structure.for_document(
                document,
                references=sources,
            )
            shape = self._decide(
                Proposal.structure(structure),
                finding="current_structure_rejected",
            )
            assert shape.body_reference is not None
            closure = tuple(
                dict.fromkeys(
                    (
                        shape.body_reference,
                        *sources,
                        *(() if supersedes is None else (supersedes,)),
                    )
                )
            )
            proposal = Proposal(
                body=document.to_bytes(),
                relation={
                    "key": key,
                    "kind": "current",
                    "supersedes": (
                        None if supersedes is None else supersedes.as_mapping()
                    ),
                },
                references=closure,
                structure_reference=shape.body_reference,
                descriptive_metadata=descriptive_metadata or {},
            )
        else:
            proposal = Proposal.current(
                document,
                key=key,
                supersedes=supersedes,
                descriptive_metadata=descriptive_metadata,
            )
        decision = self._decide(
            proposal,
            finding="current_admission_rejected",
            expected_findings=frozenset({"current_reference_mismatch"}),
        )
        if not decision.admitted:
            current = self.current_reference(key)
            expected_reference = reference_for(
                document.to_bytes(),
                descriptive_metadata=descriptive_metadata,
            )
            if (
                current is not None
                and current == expected_reference
                and self.fetch(current) == document.to_bytes()
            ):
                return current
            raise CurrentAdmissionConflict("current_admission_conflict")
        assert decision.body_reference is not None
        return decision.body_reference

    def reserve_work(
        self,
        document: Document,
        *,
        capacity_reference: Reference,
        scope: str,
        expires_at: datetime,
    ) -> Reference | PermitReservationWaiting:
        """
        Reserve one bounded work slot, or report temporary permit contention.
        """

        decision = self._decide(
            Proposal.permit(
                document,
                capacity_reference=capacity_reference,
                scope=scope,
                expires_at=expires_at,
            ),
            finding="permit_admission_rejected",
            expected_findings=frozenset(
                {
                    "permit_already_closed",
                    "permit_already_open",
                    "permit_capacity_exceeded",
                    "permit_capacity_not_current",
                }
            ),
        )
        if not decision.admitted:
            if len(decision.findings) != 1:
                raise RuntimeError("permit_waiting_ambiguous")
            return PermitReservationWaiting(decision.findings[0])
        if decision.proposal_reference is None:
            raise RuntimeError("permit_reference_missing")
        return decision.proposal_reference

    def admit_receipt(
        self,
        document: Document,
        *,
        permit_reference: Reference,
    ) -> Decision:
        """
        Consume one open permit with an exact observation document.
        """

        decision = self._decide(
            Proposal.receipt(
                document,
                permit_reference=permit_reference,
            ),
            finding="receipt_admission_rejected",
        )
        if decision.proposal_reference is None:
            raise RuntimeError("receipt_reference_missing")
        return decision

    def close_permit(
        self,
        document: Document,
        *,
        permit_reference: Reference,
        reason: str,
        is_already_closed_allowed: bool = False,
    ) -> Decision:
        """
        Close one work permit without admitting an observation.
        """

        expected = (
            frozenset({"permit_already_closed"})
            if is_already_closed_allowed
            else frozenset()
        )
        return self._decide(
            Proposal.close(
                document,
                permit_reference=permit_reference,
                reason=reason,
            ),
            finding="permit_close_rejected",
            expected_findings=expected,
        )

    def fetch(self, reference: Reference) -> bytes:
        """
        Fetch exact immutable bytes through this session's Authority handle.
        """

        return self._authority.fetch(reference)

    def current_reference(self, key: str) -> Reference | None:
        """
        Return the single current reference for one exact Authority key.
        """

        matches = tuple(
            item.body_reference for item in self._observe().current if item.key == key
        )
        if len(matches) > 1:
            raise RuntimeError("authority_current_ambiguous")
        return matches[0] if matches else None

    def observe_admitted(self, reference: Reference) -> None:
        """
        Verify delegated admitted bytes before following their Authority head.
        """

        self._authority.fetch(reference)
        observed = self._authority.view()
        if not any(
            decision.body_reference == reference for decision in observed.decisions
        ):
            raise RuntimeError("delegated_object_not_admitted")
        self._revision = observed.revision

    def admit_object(
        self,
        body: bytes,
        *,
        media_type: str,
        descriptive_metadata: Mapping[str, Any],
    ) -> Reference:
        """
        Admit one opaque immutable object and retain its resulting head.
        """

        decision = self._decide(
            Proposal(
                body=body,
                relation={"kind": "record"},
                media_type=media_type,
                descriptive_metadata=descriptive_metadata,
            ),
            finding="object_admission_rejected",
        )
        assert decision.body_reference is not None
        return decision.body_reference

    def _decide(
        self,
        proposal: Proposal,
        *,
        finding: str,
        expected_findings: frozenset[str] = frozenset(),
    ) -> Decision:
        for _attempt in range(self._contention_attempts):
            decision = self._authority.decide(proposal, at=self._revision)
            if "revision_mismatch" in decision.findings:
                self._observe()
                self._wait(0.001)
                continue
            if (
                not decision.admitted
                and frozenset(decision.findings) <= expected_findings
            ):
                return decision
            if not decision.admitted or decision.body_reference is None:
                raise RuntimeError(f"{finding}:" + ",".join(decision.findings))
            self._revision = decision.resulting_revision
            return decision
        raise RuntimeError("authority_contention")

    def _observe(self) -> AuthorityView:
        observed = self._authority.view()
        self._revision = observed.revision
        return observed
