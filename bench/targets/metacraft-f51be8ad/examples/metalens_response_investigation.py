from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
import hashlib

from examples.metalens_field_diagnostics import FieldAssumptionDiagnostic
from metacraft.authority import Document, Reference
from metacraft.canonical import canonicalize


_INVESTIGATION_SCHEMA = (
    "metacraft.examples.metalens_response_investigation"
)

Fetch = Callable[[Reference], bytes]


class InvestigationDecision(str, Enum):
    """
    Names the three bounded outcomes of recorded-evidence selection.
    """

    EXPLANATION = "evidence-backed explanation"
    MISSING_OBSERVATION = "bounded missing observation"
    NO_SWEEP = "no sweep"


class ResponseEvidenceFamily(str, Enum):
    """
    Names one non-overlapping family of retained response evidence.
    """

    FIELD_ASSIGNMENT = "field assignment"
    PROPAGATION_PHASE_RESPONSE = "propagation phase response"
    PROPAGATION_USEFUL_RESPONSE = "propagation useful response"
    GEOMETRIC_JONES_RESPONSE = "geometric Jones response"
    SAMPLED_SURFACE = "sampled surface"


@dataclass(frozen=True, slots=True)
class ResponseInvestigation:
    """
    Records one bounded response question selected by a diagnostic.
    """

    case_identity: str
    result_reference: Reference
    diagnostic_identity: str
    endpoint_comparison_identity: str
    first_divergent_step: str | None
    decision: InvestigationDecision
    evidence_family: ResponseEvidenceFamily | None
    evidence_references: tuple[Reference, ...]
    explanation: str
    missing_observation: str | None
    exact_live_observation: str | None
    interpretation: str = (
        "Diagnostic fixture evidence supports an investigation hypothesis, not an "
        "exact published-case claim or an exact Live requirement."
    )

    def __post_init__(self) -> None:
        """
        Require one coherent explanation, missing need, or stop decision.
        """

        if (
            not self.case_identity.startswith("sha256:")
            or not self.diagnostic_identity.startswith("sha256:")
            or not self.endpoint_comparison_identity.startswith("sha256:")
            or not self.explanation.strip()
        ):
            raise ValueError("response_investigation_invalid")
        if self.decision is InvestigationDecision.NO_SWEEP:
            if (
                self.first_divergent_step is not None
                or self.evidence_family is not None
                or self.evidence_references
                or self.missing_observation is not None
            ):
                raise ValueError("response_no_sweep_invalid")
        elif self.evidence_family is None or self.first_divergent_step is None:
            raise ValueError("response_investigation_family_missing")
        if self.decision is InvestigationDecision.EXPLANATION:
            if not self.evidence_references or self.missing_observation is not None:
                raise ValueError("response_explanation_invalid")
        if self.decision is InvestigationDecision.MISSING_OBSERVATION:
            if not self.missing_observation or self.evidence_references:
                raise ValueError("response_missing_observation_invalid")

    def document(self) -> Document:
        """
        Encode the immutable external investigation document.
        """

        values = canonicalize(self)
        assert isinstance(values, dict)
        return Document(_INVESTIGATION_SCHEMA, values)


def select_response_investigation(
    diagnostic: FieldAssumptionDiagnostic,
    *,
    fetch: Fetch,
) -> ResponseInvestigation:
    """
    Read only the retained evidence named by the first divergent step.
    """

    diagnostic_identity = _document_identity(diagnostic.document())
    step = diagnostic.first_divergent_step
    if step is None:
        return ResponseInvestigation(
            case_identity=diagnostic.case_identity,
            result_reference=diagnostic.result_reference,
            diagnostic_identity=diagnostic_identity,
            endpoint_comparison_identity=(
                diagnostic.endpoint_comparison_identity
            ),
            first_divergent_step=None,
            decision=InvestigationDecision.NO_SWEEP,
            evidence_family=None,
            evidence_references=(),
            explanation=(
                diagnostic.no_divergence_reason
                or "Every applicable diagnostic field agrees; no response "
                "evidence family is opened."
            ),
            missing_observation=None,
            exact_live_observation=None,
        )

    variant = next(item for item in diagnostic.variants if item.name == step)
    family, explanation = _select_evidence_family(step, diagnostic)
    selected_references = _selected_references(
        family,
        diagnostic,
        variant.source_references,
    )
    try:
        bodies = tuple(fetch(reference) for reference in selected_references)
    except LookupError:
        return ResponseInvestigation(
            case_identity=diagnostic.case_identity,
            result_reference=diagnostic.result_reference,
            diagnostic_identity=diagnostic_identity,
            endpoint_comparison_identity=(
                diagnostic.endpoint_comparison_identity
            ),
            first_divergent_step=step,
            decision=InvestigationDecision.MISSING_OBSERVATION,
            evidence_family=family,
            evidence_references=(),
            explanation=(
                f"The {family.value} hypothesis cannot be inspected from the "
                "bounded retained evidence."
            ),
            missing_observation=(
                f"Restore the exact retained {family.value} object named by "
                "the divergent diagnostic before proposing any new work."
            ),
            exact_live_observation=None,
        )
    for reference, body in zip(selected_references, bodies, strict=True):
        _require_exact_body(reference, body)
    return ResponseInvestigation(
        case_identity=diagnostic.case_identity,
        result_reference=diagnostic.result_reference,
        diagnostic_identity=diagnostic_identity,
        endpoint_comparison_identity=diagnostic.endpoint_comparison_identity,
        first_divergent_step=step,
        decision=InvestigationDecision.EXPLANATION,
        evidence_family=family,
        evidence_references=selected_references,
        explanation=explanation,
        missing_observation=None,
        exact_live_observation=None,
    )


def _select_evidence_family(
    step: str,
    diagnostic: FieldAssumptionDiagnostic,
) -> tuple[ResponseEvidenceFamily, str]:
    if step in {"assigned target", "assigned orientation"}:
        return (
            ResponseEvidenceFamily.FIELD_ASSIGNMENT,
            f"The first diagnostic difference is {step}; inspect only "
            "the fixed aperture assignment and its admitted provenance. This "
            "locates an assignment hypothesis and selects no cell-response work.",
        )
    if step == "realized phase":
        return (
            ResponseEvidenceFamily.PROPAGATION_PHASE_RESPONSE,
            "The first diagnostic difference enters with admitted cell "
            "phase; inspect phase coverage and deterministic selection from "
            "the selected response evidence while holding period and height fixed.",
        )
    if step == "realized coefficient":
        return (
            ResponseEvidenceFamily.PROPAGATION_USEFUL_RESPONSE,
            "The first diagnostic difference enters with useful amplitude; "
            "inspect admitted useful and leakage power from the same propagation "
            "response while holding period and height fixed.",
        )
    if step == "realized jones":
        return (
            ResponseEvidenceFamily.GEOMETRIC_JONES_RESPONSE,
            "The first diagnostic difference enters with the admitted Jones "
            "response; inspect converted power and retained-channel leakage for "
            "the selected anisotropic cell. Analytic rotations add no solver work.",
        )
    if step == "sampled surface":
        if diagnostic.vector_provenance is None:
            raise ValueError("sampled_surface_vector_provenance_missing")
        return (
            ResponseEvidenceFamily.SAMPLED_SURFACE,
            "The first diagnostic difference enters at the sampled surface; "
            "inspect exact rectilinear sources, uniform surface formation, complete "
            "complex components, and vector propagation provenance.",
        )
    raise ValueError("diagnostic_divergence_step_unsupported")


def _selected_references(
    family: ResponseEvidenceFamily,
    diagnostic: FieldAssumptionDiagnostic,
    variant_references: tuple[Reference, ...],
) -> tuple[Reference, ...]:
    if family is ResponseEvidenceFamily.FIELD_ASSIGNMENT:
        return (diagnostic.aperture_reference,)
    return tuple(dict.fromkeys(variant_references))


def _require_exact_body(reference: Reference, body: bytes) -> None:
    if (
        len(body) != reference.size_bytes
        or "sha256:" + hashlib.sha256(body).hexdigest()
        != reference.content_hash
    ):
        raise ValueError("response_evidence_reference_mismatch")


def _document_identity(document: Document) -> str:
    return "sha256:" + hashlib.sha256(document.to_bytes()).hexdigest()


__all__ = [
    "InvestigationDecision",
    "ResponseEvidenceFamily",
    "ResponseInvestigation",
    "select_response_investigation",
]
