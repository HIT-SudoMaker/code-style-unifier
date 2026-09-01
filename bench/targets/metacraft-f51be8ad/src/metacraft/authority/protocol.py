from __future__ import annotations

import base64
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any

from ..canonical import canonicalize, encode_bytes, encode_text


@dataclass(frozen=True, slots=True)
class Revision:
    """
    Identifies one exact authority ledger head.
    """

    value: str

    @classmethod
    def root(cls) -> Revision:
        """
        Return the empty-workspace revision.
        """

        return cls("root")

    def __post_init__(self) -> None:
        """
        Accept only a public root or canonical ledger-head revision.
        """

        if self.value != "root" and _HASH_PATTERN.fullmatch(self.value) is None:
            raise ValueError("revision_invalid")


@dataclass(frozen=True, slots=True)
class Reference:
    """
    Identifies immutable bytes and their descriptive metadata.
    """

    content_hash: str
    media_type: str
    metadata_content_hash: str
    size_bytes: int

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> Reference:
        """
        Decode one exact reference from protocol data with no coercion.
        """

        _require_mapping(value, "reference")
        if set(value) != {
            "content_hash",
            "media_type",
            "metadata_content_hash",
            "size_bytes",
        }:
            raise ValueError("reference_shape_invalid")
        content_hash = _require_hash(
            value["content_hash"],
            "reference_content_hash",
        )
        media_type = _require_nonempty_str(
            value["media_type"],
            "reference_media_type",
        )
        metadata_content_hash = _require_hash(
            value["metadata_content_hash"],
            "reference_metadata_content_hash",
        )
        size_bytes = _require_unsigned_int(
            value["size_bytes"],
            "reference_size_bytes",
        )
        return cls(
            content_hash=content_hash,
            media_type=media_type,
            metadata_content_hash=metadata_content_hash,
            size_bytes=size_bytes,
        )

    def as_mapping(self) -> dict[str, Any]:
        """
        Return the protocol representation of this reference.
        """

        return {
            "content_hash": self.content_hash,
            "media_type": self.media_type,
            "metadata_content_hash": self.metadata_content_hash,
            "size_bytes": self.size_bytes,
        }

    def canonical_text(self) -> str:
        """
        Encode this reference for the native fetch verb.
        """

        return encode_text(self.as_mapping())


@dataclass(frozen=True, slots=True)
class Document:
    """
    Wraps one typed JSON record stored as opaque authority bytes.
    """

    schema_identifier: str
    values: Mapping[str, Any]

    def __post_init__(self) -> None:
        """
        Reject an empty document schema identifier.
        """

        if not self.schema_identifier.strip():
            raise ValueError("document_schema_empty")

    def as_mapping(self) -> dict[str, Any]:
        """
        Return the stable document envelope.
        """

        return {
            "schema_identifier": self.schema_identifier,
            "values": canonicalize(self.values),
        }

    def to_bytes(self) -> bytes:
        """
        Encode this document as canonical UTF-8 JSON.
        """

        return encode_bytes(self.as_mapping())

    @classmethod
    def from_bytes(cls, value: bytes) -> Document:
        """
        Decode and verify one canonical document.
        """

        decoded = json.loads(value)
        if (
            not isinstance(decoded, Mapping)
            or set(decoded) != {"schema_identifier", "values"}
        ):
            raise ValueError("document_shape_invalid")
        if not isinstance(decoded["values"], dict):
            raise ValueError("document_values_invalid")
        document = cls(
            schema_identifier=str(decoded["schema_identifier"]),
            values=decoded["values"],
        )
        if document.to_bytes() != value:
            raise ValueError("document_not_canonical")
        return document


@dataclass(frozen=True, slots=True)
class Structure:
    """
    Describes one exact typed document shape and its reference fields.
    """

    shape: Mapping[str, Any]
    references: tuple[Reference, ...]

    @classmethod
    def for_document(
        cls,
        document: Document,
        *,
        references: tuple[Reference, ...],
    ) -> Structure:
        """
        Derive one closed shape from a canonical document and exact references.
        """

        if len(set(references)) != len(references):
            raise ValueError("structure_reference_duplicate")
        return cls(
            shape=_shape_for(document.as_mapping(), references),
            references=references,
        )

    def to_bytes(self) -> bytes:
        """
        Encode this authority structure as canonical JSON.
        """

        return encode_bytes(
            {
                "schema_identifier": "metacraft.authority.structure",
                "shape": self.shape,
            }
        )


@dataclass(frozen=True, slots=True)
class Proposal:
    """
    Describes one canonical transition proposed to Rust.
    """

    body: bytes
    relation: Mapping[str, Any]
    references: tuple[Reference, ...] = ()
    media_type: str = "application/json"
    descriptive_metadata: Mapping[str, Any] = field(default_factory=dict)
    structure_reference: Reference | None = None

    @classmethod
    def record(
        cls,
        document: Document,
        *,
        descriptive_metadata: Mapping[str, Any] | None = None,
    ) -> Proposal:
        """
        Retain one immutable document without making it current.
        """

        return cls(
            body=document.to_bytes(),
            relation={"kind": "record"},
            descriptive_metadata=descriptive_metadata or {},
        )

    @classmethod
    def current(
        cls,
        document: Document,
        *,
        key: str,
        supersedes: Reference | None = None,
        descriptive_metadata: Mapping[str, Any] | None = None,
    ) -> Proposal:
        """
        Propose one named current document and exact predecessor.
        """

        references = () if supersedes is None else (supersedes,)
        return cls(
            body=document.to_bytes(),
            relation={
                "key": key,
                "kind": "current",
                "supersedes": None if supersedes is None else supersedes.as_mapping(),
            },
            references=references,
            descriptive_metadata=descriptive_metadata or {},
        )

    @classmethod
    def structure(cls, structure: Structure) -> Proposal:
        """
        Register one exact document structure and its reference closure.
        """

        return cls(
            body=structure.to_bytes(),
            relation={"kind": "record"},
            references=structure.references,
        )

    @classmethod
    def structured(
        cls,
        document: Document,
        *,
        structure_reference: Reference,
        references: tuple[Reference, ...],
    ) -> Proposal:
        """
        Store a document under one registered exact-reference structure.
        """

        closure = (structure_reference, *references)
        if len(set(closure)) != len(closure):
            raise ValueError("structured_reference_duplicate")
        return cls(
            body=document.to_bytes(),
            relation={"kind": "record"},
            references=closure,
            structure_reference=structure_reference,
        )

    @classmethod
    def capacity(
        cls,
        *,
        scope: str,
        limit: int,
        qualification_references: tuple[Reference, ...],
        supersedes: Reference | None = None,
    ) -> Proposal:
        """
        Propose one qualified capacity under its exact evidence.
        """

        if not scope.strip():
            raise ValueError("capacity_scope_empty")
        if limit <= 0:
            raise ValueError("capacity_limit_invalid")
        references = list(qualification_references)
        if supersedes is not None and supersedes not in references:
            references.append(supersedes)
        return cls(
            body=encode_bytes(
                {
                    "limit": limit,
                    "qualification_references": [
                        reference.as_mapping() for reference in qualification_references
                    ],
                    "schema_identifier": "metacraft.authority.capacity",
                    "scope": scope,
                }
            ),
            relation={
                "key": f"capacity:{scope}",
                "kind": "current",
                "supersedes": (None if supersedes is None else supersedes.as_mapping()),
            },
            references=tuple(references),
        )

    @classmethod
    def permit(
        cls,
        document: Document,
        *,
        capacity_reference: Reference,
        scope: str,
        expires_at: datetime,
    ) -> Proposal:
        """
        Reserve one unit beneath a current capacity.
        """

        return cls(
            body=document.to_bytes(),
            relation={
                "capacity_reference": capacity_reference.as_mapping(),
                "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
                "kind": "permit",
                "scope": scope,
            },
            references=(capacity_reference,),
        )

    @classmethod
    def receipt(
        cls,
        document: Document,
        *,
        permit_reference: Reference,
    ) -> Proposal:
        """
        Close one permit with a valid observation document.
        """

        return cls(
            body=document.to_bytes(),
            relation={
                "kind": "receipt",
                "permit_reference": permit_reference.as_mapping(),
            },
            references=(permit_reference,),
        )

    @classmethod
    def close(
        cls,
        document: Document,
        *,
        permit_reference: Reference,
        reason: str,
    ) -> Proposal:
        """
        Revoke or expire one permit without an observation.
        """

        if reason not in {"revoked", "expired"}:
            raise ValueError("close_reason_invalid")
        return cls(
            body=document.to_bytes(),
            relation={
                "kind": "close",
                "permit_reference": permit_reference.as_mapping(),
                "reason": reason,
            },
            references=(permit_reference,),
        )

    def as_mapping(self) -> dict[str, Any]:
        """
        Return the complete native proposal shape.
        """

        return {
            "body": {
                "bytes_base64": base64.b64encode(self.body).decode("ascii"),
                "descriptive_metadata": canonicalize(self.descriptive_metadata),
                "media_type": self.media_type,
                "structure_reference": (
                    None
                    if self.structure_reference is None
                    else self.structure_reference.as_mapping()
                ),
            },
            "references": [reference.as_mapping() for reference in self.references],
            "relation": canonicalize(self.relation),
            "schema_identifier": "metacraft.authority.proposal",
        }

    def canonical_text(self) -> str:
        """
        Encode this proposal for the native decide verb.
        """

        return encode_text(self.as_mapping())


@dataclass(frozen=True, slots=True)
class Decision:
    """
    Records Rust's immutable answer to one proposal.
    """

    body_reference: Reference | None
    findings: tuple[str, ...]
    observed_revision: Revision
    outcome: str
    proposal_content_hash: str | None
    proposal_reference: Reference | None
    resulting_revision: Revision
    schema_identifier: str

    @property
    def admitted(self) -> bool:
        """
        Report whether this decision advanced authority state.
        """

        return self.outcome == "admitted"

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> Decision:
        """
        Decode one typed decision from protocol data with no coercion.
        """

        _require_mapping(value, "decision_result")
        if set(value) != {
            "body_reference",
            "findings",
            "observed_revision",
            "outcome",
            "proposal_content_hash",
            "proposal_reference",
            "resulting_revision",
            "schema_identifier",
        }:
            raise ValueError("decision_result_shape_invalid")
        schema_identifier = _require_str(
            value["schema_identifier"],
            "decision_result_schema",
        )
        if schema_identifier != DECISION_SCHEMA_IDENTIFIER:
            raise ValueError("decision_result_schema_invalid")
        outcome = _require_str(value["outcome"], "decision_result_outcome")
        if outcome not in {"admitted", "rejected"}:
            raise ValueError("decision_result_outcome_invalid")
        observed_revision = Revision(
            _require_nonempty_str(
                value["observed_revision"],
                "decision_result_observed_revision",
            )
        )
        resulting_revision = Revision(
            _require_nonempty_str(
                value["resulting_revision"],
                "decision_result_resulting_revision",
            )
        )
        findings_value = value["findings"]
        if not isinstance(findings_value, list):
            raise ValueError("decision_result_findings_invalid")
        findings = tuple(
            _require_nonempty_str(item, "decision_result_finding")
            for item in findings_value
        )
        if any(
            finding not in _REJECTION_FINDINGS
            and finding != "structure_mismatch:$"
            and not finding.startswith("structure_mismatch:$.")
            and not finding.startswith("structure_mismatch:$[")
            for finding in findings
        ):
            raise ValueError("decision_result_finding_invalid")
        proposal_content_hash_value = value["proposal_content_hash"]
        if proposal_content_hash_value is None:
            proposal_content_hash: str | None = None
        else:
            proposal_content_hash = _require_hash(
                proposal_content_hash_value,
                "decision_result_proposal_content_hash",
            )
        body_reference = _optional_reference(value["body_reference"])
        proposal_reference = _optional_reference(value["proposal_reference"])
        if proposal_reference is not None:
            _require_proposal_reference(
                proposal_reference,
                "decision_result_proposal_reference",
            )
        _guard_decision_relationship(
            body_reference=body_reference,
            findings=findings,
            observed_revision=observed_revision,
            outcome=outcome,
            proposal_content_hash=proposal_content_hash,
            proposal_reference=proposal_reference,
            resulting_revision=resulting_revision,
        )
        return cls(
            body_reference=body_reference,
            findings=findings,
            observed_revision=observed_revision,
            outcome=outcome,
            proposal_content_hash=proposal_content_hash,
            proposal_reference=proposal_reference,
            resulting_revision=resulting_revision,
            schema_identifier=schema_identifier,
        )


PERMIT_STATES = frozenset({"open", "closed"})
PERMIT_CLOSE_REASONS = frozenset({"consumed", "revoked", "expired"})
DECISION_RELATIONS = frozenset({"record", "current", "permit", "receipt", "close"})

#: The schema identifiers Rust stamps on its public wire documents.
VIEW_SCHEMA_IDENTIFIER = "metacraft.authority.view"
DECISION_SCHEMA_IDENTIFIER = "metacraft.authority.decision"
CHECK_SCHEMA_IDENTIFIER = "metacraft.authority.check"
AUTHORITY_PROTOCOL_IDENTIFIER = "metacraft.authority"

#: Accepted content and metadata hash form: one lowercase SHA-256 digest.
_HASH_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
_PROPOSAL_MEDIA_TYPE = "application/vnd.metacraft.authority.proposal+json"
_REJECTION_FINDINGS = frozenset(
    {
        "capacity_below_open_permits",
        "capacity_invalid",
        "close_permit_missing",
        "close_permit_reference_missing",
        "current_key_invalid",
        "current_reference_mismatch",
        "current_reference_missing",
        "json_invalid",
        "permit_already_closed",
        "permit_already_open",
        "permit_capacity_exceeded",
        "permit_capacity_not_current",
        "permit_capacity_reference_missing",
        "permit_expired",
        "permit_expiry_invalid",
        "permit_not_expired",
        "proposal_body_invalid",
        "proposal_body_not_canonical",
        "receipt_permit_missing",
        "receipt_permit_reference_missing",
        "reference_closure_duplicate",
        "reference_closure_incomplete",
        "reference_closure_surplus",
        "reference_unresolvable",
        "revision_mismatch",
        "structure_invalid",
        "structure_mismatch",
        "structure_schema_mismatch",
    }
)

_SCHEMA_CONTENT_HASHES = {
    "capacity": "sha256:b3f8f4089f897c9cb9b9bfe4db2f2cc1e043841834109f3ebeb4f28ab8e919e7",
    "decision": "sha256:2d6a0e816fa1c9cf973f68fe90e3b119f960690afb198a959bc4376128e199a7",
    "proposal": "sha256:3ac33ccc4183fcbd63534824a3d8ae24bdf4094fe4ac4b5865efa114ca6fda5a",
    "reference": "sha256:bab101133f0f759d8201581c5e68c47391f8c84fe079f3b73a1e276f297330ea",
    "structure": "sha256:69517363134539f624477f451f9973b4ba872a2dcdaa171d0eea52dbc421f56e",
    "view": "sha256:ffef8a6d313c417cd89384bdda1b7c99aaef4d11d8181a4245e53d8894bc0ba3",
}

#: Accepted permit expiry form: one normalized UTC wire value.
_RFC3339_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}" r"(?:\.\d{3}|\.\d{6}|\.\d{9})?\+00:00"
)

_PERMIT_FIELDS_WITH_RECEIPT = frozenset(
    {
        "body_reference",
        "capacity_reference",
        "close_reason",
        "expires_at",
        "permit_reference",
        "receipt_body_reference",
        "receipt_reference",
        "scope",
        "state",
    }
)
_PERMIT_FIELDS_WITHOUT_RECEIPT = _PERMIT_FIELDS_WITH_RECEIPT - {
    "receipt_body_reference"
}


@dataclass(frozen=True, slots=True)
class Current:
    """
    The sole admitted object for one named authority key.
    """

    key: str
    body_reference: Reference
    superseded: tuple[Reference, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> Current:
        """
        Decode one current entry from its protocol mapping with no coercion.
        """

        _require_mapping(value, "current")
        if set(value) != {"body_reference", "key", "superseded"}:
            raise ValueError("current_entry_shape_invalid")
        key = _require_nonempty_str(value["key"], "current_key")
        superseded_value = value["superseded"]
        if not isinstance(superseded_value, list):
            raise ValueError("current_superseded_invalid")
        try:
            body_reference = Reference.from_mapping(value["body_reference"])
            superseded = tuple(
                Reference.from_mapping(item) for item in superseded_value
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("current_reference_invalid") from error
        return cls(
            key=key,
            body_reference=body_reference,
            superseded=superseded,
        )


@dataclass(frozen=True, slots=True)
class AdmittedDecision:
    """
    One admitted proposal and the body reference replay needs.
    """

    body_reference: Reference
    proposal_reference: Reference
    relation: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> AdmittedDecision:
        """
        Decode one admitted decision from its protocol mapping with no coercion.
        """

        _require_mapping(value, "decision")
        if set(value) != {
            "body_reference",
            "outcome",
            "proposal_reference",
            "relation",
        }:
            raise ValueError("decision_entry_shape_invalid")
        outcome = _require_str(value["outcome"], "decision_outcome")
        if outcome != "admitted":
            raise ValueError("decision_outcome_invalid")
        relation = _require_str(value["relation"], "decision_relation")
        if relation not in DECISION_RELATIONS:
            raise ValueError("decision_relation_invalid")
        try:
            body_reference = Reference.from_mapping(value["body_reference"])
            proposal_reference = Reference.from_mapping(value["proposal_reference"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("decision_reference_invalid") from error
        _require_proposal_reference(
            proposal_reference,
            "decision_proposal_reference",
        )
        return cls(
            body_reference=body_reference,
            proposal_reference=proposal_reference,
            relation=relation,
        )


@dataclass(frozen=True, slots=True)
class Permit:
    """
    One bounded reservation for one proposed unit of work.
    """

    scope: str
    state: str
    close_reason: str | None
    body_reference: Reference
    capacity_reference: Reference
    permit_reference: Reference
    receipt_reference: Reference | None
    receipt_body_reference: Reference | None
    expires_at: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> Permit:
        """
        Decode one permit entry from its protocol mapping with no coercion.
        """

        _require_mapping(value, "permit")
        # ``receipt_body_reference`` is omitted by Rust when a permit has no
        # receipt yet (serde ``skip_serializing_if = "Option::is_none"``); it is
        # never emitted as ``null``. A present value must therefore be a real
        # reference, and the field set selects between the two legal shapes.
        has_receipt_body = "receipt_body_reference" in value
        observed = set(value)
        if (
            observed != _PERMIT_FIELDS_WITH_RECEIPT
            and observed != _PERMIT_FIELDS_WITHOUT_RECEIPT
        ):
            raise ValueError("permit_entry_shape_invalid")
        state = _require_str(value["state"], "permit_state")
        if state not in PERMIT_STATES:
            raise ValueError("permit_state_invalid")
        close_reason_value = value["close_reason"]
        if close_reason_value is None:
            close_reason: str | None = None
        else:
            close_reason = _require_str(close_reason_value, "permit_close_reason")
            if close_reason not in PERMIT_CLOSE_REASONS:
                raise ValueError("permit_close_reason_invalid")
        scope = _require_nonempty_str(value["scope"], "permit_scope")
        expires_at = _require_rfc3339(value["expires_at"], "permit_expiry")
        try:
            body_reference = Reference.from_mapping(value["body_reference"])
            capacity_reference = Reference.from_mapping(value["capacity_reference"])
            permit_reference = Reference.from_mapping(value["permit_reference"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("permit_reference_invalid") from error
        _require_proposal_reference(
            permit_reference,
            "permit_proposal_reference",
        )
        if has_receipt_body:
            try:
                receipt_body_reference: Reference | None = Reference.from_mapping(
                    value["receipt_body_reference"]
                )
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError("permit_reference_invalid") from error
        else:
            receipt_body_reference = None
        receipt_reference = _optional_reference(value["receipt_reference"])
        if receipt_reference is not None:
            _require_proposal_reference(
                receipt_reference,
                "permit_receipt_reference",
            )
        _guard_permit_relationship(
            state=state,
            close_reason=close_reason,
            receipt_reference=receipt_reference,
            receipt_body_reference=receipt_body_reference,
        )
        return cls(
            scope=scope,
            state=state,
            close_reason=close_reason,
            body_reference=body_reference,
            capacity_reference=capacity_reference,
            permit_reference=permit_reference,
            receipt_reference=receipt_reference,
            receipt_body_reference=receipt_body_reference,
            expires_at=expires_at,
        )


@dataclass(frozen=True, slots=True)
class AuthorityView:
    """
    Holds replayed current facts, decisions, and permits as typed values.
    """

    revision: Revision
    current: tuple[Current, ...]
    decisions: tuple[AdmittedDecision, ...]
    permits: tuple[Permit, ...]
    schema_identifier: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> AuthorityView:
        """
        Decode and validate one replayed view at the Adapter seam.
        """

        _require_mapping(value, "authority_view")
        if set(value) != {
            "current",
            "decisions",
            "permits",
            "revision",
            "schema_identifier",
        }:
            raise ValueError("authority_view_shape_invalid")
        schema_identifier = _require_str(
            value["schema_identifier"],
            "authority_view_schema",
        )
        if schema_identifier != VIEW_SCHEMA_IDENTIFIER:
            raise ValueError("authority_view_schema_invalid")
        revision = Revision(
            _require_nonempty_str(
                value["revision"],
                "authority_view_revision",
            )
        )
        if not isinstance(value["current"], list):
            raise ValueError("authority_view_current_invalid")
        if not isinstance(value["decisions"], list):
            raise ValueError("authority_view_decisions_invalid")
        if not isinstance(value["permits"], list):
            raise ValueError("authority_view_permits_invalid")
        current = tuple(Current.from_mapping(item) for item in value["current"])
        decisions = tuple(
            AdmittedDecision.from_mapping(item) for item in value["decisions"]
        )
        permits = tuple(Permit.from_mapping(item) for item in value["permits"])
        _guard_view_order(current=current, permits=permits)
        _guard_view_relationships(
            current=current,
            decisions=decisions,
            permits=permits,
            revision=revision,
        )
        return cls(
            revision=revision,
            current=current,
            decisions=decisions,
            permits=permits,
            schema_identifier=schema_identifier,
        )


@dataclass(frozen=True, slots=True)
class CheckReport:
    """
    Holds the complete native workspace integrity report.
    """

    findings: tuple[str, ...]
    ledger_event_count: int
    protocol_identifier: str
    schema_identifier: str
    schema_content_hashes: Mapping[str, str]
    is_workspace_valid: bool

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> CheckReport:
        """
        Decode one exact native integrity report without coercion.
        """

        _require_mapping(value, "check_report")
        if set(value) != {
            "findings",
            "ledger_event_count",
            "protocol_identifier",
            "schema_identifier",
            "schema_content_hashes",
            "workspace_valid",
        }:
            raise ValueError("check_report_shape_invalid")
        findings_value = value["findings"]
        if not isinstance(findings_value, list):
            raise ValueError("check_report_findings_invalid")
        findings = tuple(
            _require_nonempty_str(item, "check_report_finding")
            for item in findings_value
        )
        if findings != tuple(sorted(set(findings))):
            raise ValueError("check_report_findings_invalid")
        ledger_event_count = _require_unsigned_int(
            value["ledger_event_count"],
            "check_report_ledger_event_count",
        )
        protocol_identifier = _require_str(
            value["protocol_identifier"],
            "check_report_protocol",
        )
        if protocol_identifier != AUTHORITY_PROTOCOL_IDENTIFIER:
            raise ValueError("check_report_protocol_invalid")
        schema_identifier = _require_str(
            value["schema_identifier"],
            "check_report_schema",
        )
        if schema_identifier != CHECK_SCHEMA_IDENTIFIER:
            raise ValueError("check_report_schema_invalid")
        schema_content_hashes = _decode_schema_content_hashes(
            value["schema_content_hashes"]
        )
        is_workspace_valid = _require_bool(
            value["workspace_valid"],
            "check_report_workspace_valid",
        )
        if is_workspace_valid != (not findings):
            raise ValueError("check_report_relation_invalid")
        return cls(
            findings=findings,
            ledger_event_count=ledger_event_count,
            protocol_identifier=protocol_identifier,
            schema_identifier=schema_identifier,
            schema_content_hashes=schema_content_hashes,
            is_workspace_valid=is_workspace_valid,
        )


def workspace_path(value: str | Path) -> str:
    """
    Resolve the explicit workspace path passed to Rust.
    """

    return str(Path(value).expanduser().resolve())


def _require_mapping(value: Any, finding: str) -> None:
    if not isinstance(value, Mapping):
        raise ValueError(f"{finding}_invalid")


def _require_str(value: Any, finding: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{finding}_invalid")
    return value


def _require_nonempty_str(value: Any, finding: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{finding}_invalid")
    return value


def _require_hash(value: Any, finding: str) -> str:
    if not isinstance(value, str) or _HASH_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{finding}_invalid")
    return value


def _require_unsigned_int(value: Any, finding: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{finding}_invalid")
    return value


def _require_bool(value: Any, finding: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{finding}_invalid")
    return value


def _require_rfc3339(value: Any, finding: str) -> str:
    if not isinstance(value, str) or _RFC3339_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{finding}_invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{finding}_invalid") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{finding}_invalid")
    return value


def _optional_reference(value: Any) -> Reference | None:
    if value is None:
        return None
    return Reference.from_mapping(value)


def _require_proposal_reference(
    reference: Reference,
    finding: str,
) -> None:
    metadata = {
        "content_hash": reference.content_hash,
        "descriptive_metadata": {"object_kind": "Proposal"},
        "media_type": reference.media_type,
        "size_bytes": reference.size_bytes,
    }
    metadata_content_hash = (
        f"sha256:{hashlib.sha256(encode_bytes(metadata)).hexdigest()}"
    )
    if (
        reference.media_type != _PROPOSAL_MEDIA_TYPE
        or reference.metadata_content_hash != metadata_content_hash
    ):
        raise ValueError(f"{finding}_invalid")


def _guard_permit_relationship(
    *,
    state: str,
    close_reason: str | None,
    receipt_reference: Reference | None,
    receipt_body_reference: Reference | None,
) -> None:
    """
    Enforce the open/closed permit meanings Rust admits.

    Rust assigns a close reason only when a permit transitions to closed; an
    open permit carries no close reason and no receipt. A consumed permit is
    the only close path that admits a receipt; revoked and expired permits
    never carry a receipt.
    """

    if state == "open":
        if (
            close_reason is not None
            or receipt_reference is not None
            or receipt_body_reference is not None
        ):
            raise ValueError("permit_open_state_invalid")
        return
    if close_reason is None:
        raise ValueError("permit_closed_reason_missing")
    if close_reason == "consumed":
        if receipt_reference is None or receipt_body_reference is None:
            raise ValueError("permit_consumed_receipt_missing")
    elif receipt_reference is not None or receipt_body_reference is not None:
        raise ValueError("permit_closed_receipt_forbidden")


def _guard_decision_relationship(
    *,
    body_reference: Reference | None,
    findings: tuple[str, ...],
    observed_revision: Revision,
    outcome: str,
    proposal_content_hash: str | None,
    proposal_reference: Reference | None,
    resulting_revision: Revision,
) -> None:
    if outcome == "admitted":
        is_decision_relationship_valid = (
            body_reference is not None
            and not findings
            and proposal_content_hash is not None
            and proposal_reference is not None
            and proposal_reference.content_hash == proposal_content_hash
            and resulting_revision != Revision.root()
            and resulting_revision != observed_revision
        )
    else:
        is_decision_relationship_valid = (
            body_reference is None
            and len(findings) == 1
            and proposal_content_hash is not None
            and proposal_reference is None
            and resulting_revision == observed_revision
        )
    if not is_decision_relationship_valid:
        raise ValueError("decision_result_relation_invalid")


def _guard_view_order(
    *,
    current: tuple[Current, ...],
    permits: tuple[Permit, ...],
) -> None:
    current_keys = tuple(item.key for item in current)
    if current_keys != tuple(sorted(set(current_keys))):
        raise ValueError("authority_view_current_order_invalid")
    permit_identities = tuple(
        permit.permit_reference.content_hash for permit in permits
    )
    if permit_identities != tuple(sorted(set(permit_identities))):
        raise ValueError("authority_view_permit_order_invalid")


def _guard_view_relationships(
    *,
    current: tuple[Current, ...],
    decisions: tuple[AdmittedDecision, ...],
    permits: tuple[Permit, ...],
    revision: Revision,
) -> None:
    if (revision == Revision.root()) != (not decisions):
        raise ValueError("authority_view_revision_relation_invalid")

    single_use_proposals = tuple(
        decision.proposal_reference
        for decision in decisions
        if decision.relation in {"permit", "receipt", "close"}
    )
    if len(single_use_proposals) != len(set(single_use_proposals)):
        raise ValueError("authority_view_decision_duplicate")

    current_decisions = tuple(
        decision for decision in decisions if decision.relation == "current"
    )
    current_history = tuple(
        reference
        for entry in current
        for reference in (*entry.superseded, entry.body_reference)
    )
    observed_current = tuple(decision.body_reference for decision in current_decisions)
    current_sequence = tuple(
        decision.body_reference
        for decision in decisions
        if decision.relation == "current"
    )
    if Counter(current_history) != Counter(observed_current) or any(
        not _is_subsequence(
            (*entry.superseded, entry.body_reference),
            current_sequence,
        )
        for entry in current
    ):
        raise ValueError("authority_view_current_history_invalid")

    permit_pairs = {
        (permit.permit_reference, permit.body_reference) for permit in permits
    }
    observed_permit_pairs = {
        (decision.proposal_reference, decision.body_reference)
        for decision in decisions
        if decision.relation == "permit"
    }
    permit_decision_count = sum(decision.relation == "permit" for decision in decisions)
    if permit_pairs != observed_permit_pairs or permit_decision_count != len(
        permit_pairs
    ):
        raise ValueError("authority_view_permit_history_invalid")

    current_by_key = {entry.key: entry for entry in current}
    for permit in permits:
        capacity = current_by_key.get(f"capacity:{permit.scope}")
        if capacity is None or permit.capacity_reference not in (
            *capacity.superseded,
            capacity.body_reference,
        ):
            raise ValueError("authority_view_permit_capacity_invalid")

    receipt_pairs = {
        (permit.receipt_reference, permit.receipt_body_reference)
        for permit in permits
        if permit.close_reason == "consumed"
    }
    observed_receipt_pairs = {
        (decision.proposal_reference, decision.body_reference)
        for decision in decisions
        if decision.relation == "receipt"
    }
    receipt_decision_count = sum(
        decision.relation == "receipt" for decision in decisions
    )
    if receipt_pairs != observed_receipt_pairs or receipt_decision_count != len(
        receipt_pairs
    ):
        raise ValueError("authority_view_receipt_history_invalid")

    closed_without_receipt = sum(
        permit.close_reason in {"revoked", "expired"} for permit in permits
    )
    close_decision_count = sum(decision.relation == "close" for decision in decisions)
    if close_decision_count != closed_without_receipt:
        raise ValueError("authority_view_close_history_invalid")

    decision_positions: dict[tuple[str, Reference, Reference], int] = {}
    earliest_current_positions: dict[Reference, int] = {}
    for index, decision in enumerate(decisions):
        decision_positions[
            (
                decision.relation,
                decision.proposal_reference,
                decision.body_reference,
            )
        ] = index
        if decision.relation == "current":
            earliest_current_positions.setdefault(
                decision.body_reference,
                index,
            )
    for permit in permits:
        permit_position = decision_positions[
            ("permit", permit.permit_reference, permit.body_reference)
        ]
        capacity_position = earliest_current_positions.get(permit.capacity_reference)
        if capacity_position is None or capacity_position >= permit_position:
            raise ValueError("authority_view_decision_order_invalid")
        if permit.receipt_reference is None or permit.receipt_body_reference is None:
            continue
        receipt_position = decision_positions[
            ("receipt", permit.receipt_reference, permit.receipt_body_reference)
        ]
        if receipt_position <= permit_position:
            raise ValueError("authority_view_decision_order_invalid")

    open_permits = 0
    for decision in decisions:
        if decision.relation == "permit":
            open_permits += 1
        elif decision.relation in {"receipt", "close"}:
            open_permits -= 1
            if open_permits < 0:
                raise ValueError("authority_view_decision_order_invalid")
    if open_permits != sum(permit.state == "open" for permit in permits):
        raise ValueError("authority_view_permit_history_invalid")


def _is_subsequence(
    expected: Sequence[Reference],
    observed: Sequence[Reference],
) -> bool:
    position = 0
    for reference in observed:
        if position < len(expected) and reference == expected[position]:
            position += 1
    return position == len(expected)


def _decode_schema_content_hashes(value: Any) -> Mapping[str, str]:
    _require_mapping(value, "check_report_schema_content_hashes")
    if dict(value) != _SCHEMA_CONTENT_HASHES:
        raise ValueError("check_report_schema_content_hashes_invalid")
    return MappingProxyType(dict(_SCHEMA_CONTENT_HASHES))


def _shape_for(
    value: Any,
    references: tuple[Reference, ...],
) -> dict[str, Any]:
    for reference in references:
        if value == reference.as_mapping():
            return {
                "exact": reference.as_mapping(),
                "kind": "reference",
            }
    if isinstance(value, Mapping):
        fields = {
            str(key): _shape_for(child, references)
            for key, child in sorted(value.items(), key=lambda item: str(item[0]))
        }
        return {
            "fields": fields,
            "kind": "object",
            "required": list(fields),
        }
    if isinstance(value, list):
        if not value:
            return {"items": {"kind": "string"}, "kind": "array"}
        shapes = [_shape_for(child, references) for child in value]
        if any(shape != shapes[0] for shape in shapes[1:]):
            raise ValueError("structure_array_shape_mixed")
        return {"items": shapes[0], "kind": "array"}
    if isinstance(value, str):
        return {"kind": "string"}
    if isinstance(value, bool):
        return {"kind": "boolean"}
    if isinstance(value, int):
        return {"kind": "integer"}
    if value is None:
        return {"kind": "null"}
    raise TypeError(f"structure_value_unsupported:{type(value).__name__}")
