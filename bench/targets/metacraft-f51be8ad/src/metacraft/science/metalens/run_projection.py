from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib

from ...authority.protocol import Document, Reference
from ...canonical import encode_bytes
from ..study import FindingKind, Study

RUN_MANIFEST_SCHEMA = "metacraft.science.metalens.run_manifest"


@dataclass(frozen=True, slots=True)
class RunStep:
    """
    One ordered story step pointing at an Authority record.
    """

    name: str
    references: tuple[Reference, ...]
    status: str = "admitted"

    def __post_init__(self) -> None:
        """
        Require one named step with a stable Authority reference.
        """
        if not self.name or self.status not in {"admitted", "waiting", "warning"}:
            raise ValueError("run_step_invalid")
        if len(set(self.references)) != len(self.references):
            raise ValueError("run_step_reference_duplicate")

    def as_mapping(self) -> dict[str, object]:
        """
        Encode this ordered story step and its Authority references.
        """

        return {
            "name": self.name,
            "references": [reference.as_mapping() for reference in self.references],
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class RunManifest:
    """
    A projection of Authority truth; never a recovery source.
    """

    brief_identity: str
    study_identity: str
    authority_revision: int
    steps: tuple[RunStep, ...]
    warnings: tuple[str, ...] = ()
    next_action: str | None = None

    def __post_init__(self) -> None:
        """
        Require an ordered, identity-stable run manifest.
        """
        if not self.brief_identity or not self.study_identity:
            raise ValueError("run_manifest_identity_missing")
        if self.authority_revision < 0 or not self.steps:
            raise ValueError("run_manifest_context_invalid")
        if any(not isinstance(item, str) or not item for item in self.warnings):
            raise ValueError("run_manifest_warning_invalid")
        if self.next_action is not None and not self.next_action:
            raise ValueError("run_manifest_next_action_invalid")

    @property
    def identity(self) -> str:
        """
        Return the deterministic identity of this run projection.
        """

        return self._identity_without_recursion()

    def as_mapping(self) -> dict[str, object]:
        """
        Encode the projection without making it an Authority truth source.
        """

        return {
            "authority_revision": self.authority_revision,
            "brief_identity": self.brief_identity,
            "identity": self.identity,
            "next_action": self.next_action,
            "steps": [step.as_mapping() for step in self.steps],
            "study_identity": self.study_identity,
            "warnings": list(self.warnings),
        }

    def document(self) -> Document:
        """
        Wrap the read-only projection as a replayable document.
        """

        values = self.as_mapping()
        # An identity must not recursively contain itself.
        values["identity"] = self._identity_without_recursion()
        return Document(RUN_MANIFEST_SCHEMA, values)

    def _identity_without_recursion(self) -> str:
        return (
            "sha256:"
            + hashlib.sha256(
                encode_bytes(
                    {
                        "authority_revision": self.authority_revision,
                        "brief_identity": self.brief_identity,
                        "next_action": self.next_action,
                        "steps": [step.as_mapping() for step in self.steps],
                        "study_identity": self.study_identity,
                        "warnings": list(self.warnings),
                    }
                )
            ).hexdigest()
        )

    @classmethod
    def from_document(cls, document: Document) -> "RunManifest":
        """
        Restore one canonical run manifest.
        """
        if document.schema_identifier != RUN_MANIFEST_SCHEMA:
            raise ValueError("run_manifest_schema_invalid")
        values = document.values
        if set(values) != {
            "authority_revision",
            "brief_identity",
            "identity",
            "next_action",
            "steps",
            "study_identity",
            "warnings",
        }:
            raise ValueError("run_manifest_document_invalid")
        raw_steps = values["steps"]
        if not isinstance(raw_steps, list):
            raise ValueError("run_manifest_steps_invalid")
        steps = tuple(
            RunStep(
                name=str(item["name"]),
                references=tuple(
                    Reference.from_mapping(reference)
                    for reference in item["references"]
                ),
                status=str(item["status"]),
            )
            for item in raw_steps
        )
        raw_warnings = values["warnings"]
        if not isinstance(raw_warnings, list):
            raise ValueError("run_manifest_warnings_invalid")
        manifest = cls(
            brief_identity=str(values["brief_identity"]),
            study_identity=str(values["study_identity"]),
            authority_revision=int(values["authority_revision"]),
            steps=steps,
            warnings=tuple(str(item) for item in raw_warnings),
            next_action=(
                None if values["next_action"] is None else str(values["next_action"])
            ),
        )
        if (
            manifest.identity != values["identity"]
            or manifest.document().to_bytes() != document.to_bytes()
        ):
            raise ValueError("run_manifest_document_mismatch")
        return manifest


def project_run_manifest(
    study: Study,
    *,
    authority_revision: int,
    references: Mapping[str, Reference] | None = None,
    warnings: tuple[str, ...] = (),
    next_action: str | None = None,
) -> RunManifest:
    """
    Project an admitted Study without making the projection authoritative.
    """

    supplied = dict(references or {})
    steps: list[RunStep] = [
        RunStep("brief", (supplied["brief"],) if "brief" in supplied else ()),
        RunStep("study", (supplied["study"],) if "study" in supplied else ()),
    ]
    for fact in study.evidence:
        steps.append(RunStep(f"evidence:{fact.claim}", (fact.reference,)))
    for index, advice in enumerate(study.advice, start=1):
        advice_refs = tuple(
            reference for reference in _references_from_value(advice.canonical_value())
        )
        if advice_refs:
            steps.append(RunStep(f"advice:{index:03d}", advice_refs))
    for finding in study.findings:
        status = "waiting" if finding.kind is FindingKind.UNAVAILABLE else "warning"
        if finding.record_references:
            steps.append(
                RunStep(f"finding:{finding.claim}", finding.record_references, status)
            )
    steps = [step for step in steps if step.references]
    if not steps:
        raise ValueError("run_manifest_no_authority_references")
    return RunManifest(
        brief_identity=study.brief_identity,
        study_identity=study.identity,
        authority_revision=authority_revision,
        steps=tuple(steps),
        warnings=warnings,
        next_action=next_action,
    )


def _references_from_value(value: object) -> tuple[Reference, ...]:
    if isinstance(value, Reference):
        return (value,)
    if isinstance(value, Mapping):
        result: list[Reference] = []
        try:
            if set(value) == {"algorithm", "digest"}:
                return (Reference.from_mapping(value),)
        except (TypeError, ValueError):
            pass
        for child in value.values():
            result.extend(_references_from_value(child))
        return tuple(result)
    if isinstance(value, (list, tuple)):
        result: list[Reference] = []
        for child in value:
            result.extend(_references_from_value(child))
        return tuple(result)
    return ()


__all__ = ["RUN_MANIFEST_SCHEMA", "RunManifest", "RunStep", "project_run_manifest"]
