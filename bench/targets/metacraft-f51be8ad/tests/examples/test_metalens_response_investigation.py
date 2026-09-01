from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from examples.metalens_field_diagnostics import (
    DiagnosticField,
    DiagnosticFieldAssumptions,
    FieldAssumptionDiagnostic,
    VectorFieldProvenance,
)
from examples.metalens_response_investigation import (
    InvestigationDecision,
    ResponseEvidenceFamily,
    select_response_investigation,
)
from metacraft.authority import Reference
from metacraft.authority.reference import reference_for
from tests.examples.metalens_diagnostic_support import (
    DIAGNOSTIC_ENDPOINT_DISPOSITIONS,
    admitted_result,
    diagnostic_case_identity,
    diagnostic_contract_results,
    diagnostic_endpoint_identity,
)
from examples.metalens_field_diagnostics import diagnose_field_assumptions


def test_first_divergence_reads_only_its_recorded_evidence_family() -> None:
    phase_reference = reference_for(b"phase evidence")
    unrelated_reference = reference_for(b"unrelated evidence")
    diagnostic = _diagnostic(
        step="realized phase",
        source_references=(phase_reference,),
        response_references=(phase_reference, unrelated_reference),
    )
    fetched: list[Reference] = []

    investigation = select_response_investigation(
        diagnostic,
        fetch=lambda reference: (
            fetched.append(reference) or b"phase evidence"
        ),
    )

    assert investigation.decision is InvestigationDecision.EXPLANATION
    assert (
        investigation.evidence_family
        is ResponseEvidenceFamily.PROPAGATION_PHASE_RESPONSE
    )
    assert investigation.evidence_references == (phase_reference,)
    assert fetched == [phase_reference]
    assert investigation.case_identity == diagnostic.case_identity
    assert investigation.result_reference == diagnostic.result_reference
    assert investigation.diagnostic_identity.startswith("sha256:")
    assert investigation.exact_live_observation is None
    assert "hypothesis" in investigation.interpretation.lower()


def test_assignment_difference_reads_only_the_admitted_aperture() -> None:
    response_reference = reference_for(b"response evidence")
    diagnostic = _diagnostic(
        step="assigned orientation",
        source_references=(response_reference,),
        response_references=(response_reference,),
    )
    reads: list[Reference] = []

    investigation = select_response_investigation(
        diagnostic,
        fetch=lambda reference: (
            reads.append(reference) or b"baseline"
        ),
    )

    assert (
        investigation.evidence_family
        is ResponseEvidenceFamily.FIELD_ASSIGNMENT
    )
    assert investigation.evidence_references == (
        diagnostic.aperture_reference,
    )
    assert reads == [diagnostic.aperture_reference]
    assert response_reference not in investigation.evidence_references


def test_sampled_surface_keeps_vector_provenance_and_no_cell_sweep() -> None:
    surface_reference = reference_for(b"surface evidence")
    field_reference = reference_for(b"field evidence")
    diagnostic = _diagnostic(
        step="sampled surface",
        source_references=(surface_reference, field_reference),
        response_references=(surface_reference,),
    )
    bodies = {
        surface_reference: b"surface evidence",
        field_reference: b"field evidence",
    }

    investigation = select_response_investigation(
        diagnostic,
        fetch=bodies.__getitem__,
    )

    assert (
        investigation.evidence_family
        is ResponseEvidenceFamily.SAMPLED_SURFACE
    )
    assert investigation.evidence_references == (
        surface_reference,
        field_reference,
    )
    assert "rectilinear" in investigation.explanation
    assert "vector" in investigation.explanation
    assert "cell sweep" not in investigation.explanation


def test_no_divergence_selects_no_evidence_and_performs_no_read() -> None:
    diagnostic = _diagnostic(step=None)
    reads = 0

    def reject_read(_reference: Reference) -> bytes:
        nonlocal reads
        reads += 1
        raise AssertionError("no-sweep decision must perform no evidence read")

    investigation = select_response_investigation(
        diagnostic,
        fetch=reject_read,
    )

    assert investigation.decision is InvestigationDecision.NO_SWEEP
    assert investigation.evidence_family is None
    assert investigation.evidence_references == ()
    assert investigation.exact_live_observation is None
    assert reads == 0


def test_missing_selected_object_returns_one_bounded_need() -> None:
    reference = reference_for(b"missing")
    diagnostic = _diagnostic(
        step="realized coefficient",
        source_references=(reference,),
        response_references=(reference,),
    )

    investigation = select_response_investigation(
        diagnostic,
        fetch=lambda _reference: (_ for _ in ()).throw(KeyError("missing")),
    )

    assert investigation.decision is InvestigationDecision.MISSING_OBSERVATION
    assert investigation.evidence_references == ()
    assert investigation.missing_observation is not None
    assert investigation.exact_live_observation is None


def test_malformed_retained_evidence_raises_directly() -> None:
    reference = reference_for(b"expected")
    diagnostic = _diagnostic(
        step="realized jones",
        source_references=(reference,),
        response_references=(reference,),
    )

    with pytest.raises(ValueError, match="response_evidence_reference_mismatch"):
        select_response_investigation(
            diagnostic,
            fetch=lambda _reference: b"different",
        )


def test_contract_fixtures_select_hypotheses_not_exact_live_claims(
    tmp_path: Path,
) -> None:
    investigations = []
    for family, record in diagnostic_contract_results(tmp_path):
        result = admitted_result(record)
        diagnostic = diagnose_field_assumptions(
            case_identity=diagnostic_case_identity(family),
            result=result,
            endpoint_comparison_identity=diagnostic_endpoint_identity(result),
            endpoint_dispositions=DIAGNOSTIC_ENDPOINT_DISPOSITIONS,
            fetch=record.authority.fetch,
        )
        investigations.append(
            select_response_investigation(
                diagnostic,
                fetch=record.authority.fetch,
            )
        )

    assert len(investigations) == 8
    assert {
        item.evidence_family for item in investigations
    } == {
        ResponseEvidenceFamily.FIELD_ASSIGNMENT,
        ResponseEvidenceFamily.PROPAGATION_PHASE_RESPONSE,
    }
    assert all(item.exact_live_observation is None for item in investigations)
    assert all(
        "not an exact" in item.interpretation.lower()
        for item in investigations
    )


def _diagnostic(
    *,
    step: str | None,
    source_references: tuple[Reference, ...] | None = None,
    response_references: tuple[Reference, ...] | None = None,
) -> FieldAssumptionDiagnostic:
    baseline_reference = reference_for(b"baseline")
    selected_references = source_references or (baseline_reference,)
    assumptions = DiagnosticFieldAssumptions(
        phase_response="ideal",
        useful_response="unity",
        polarization_response="ideal",
        surface_response="grid",
    )
    baseline = DiagnosticField(
        name="ideal continuous",
        assumptions=assumptions,
        field_signature="sha256:" + "0" * 64,
        changed_assumption=None,
        is_different_from_previous=None,
        attribution="Fixed ideal baseline.",
        source_references=(baseline_reference,),
    )
    variants = (baseline,)
    if step is not None:
        changed_name = {
            "assigned target": "phase_response",
            "assigned orientation": "phase_response",
            "realized phase": "phase_response",
            "realized coefficient": "useful_response",
            "realized jones": "polarization_response",
            "sampled surface": "surface_response",
        }[step]
        changed = replace(
            assumptions,
            **{changed_name: f"changed {changed_name}"},
        )
        variants = (
            baseline,
            DiagnosticField(
                name=step,
                assumptions=changed,
                field_signature="sha256:" + "1" * 64,
                changed_assumption=changed_name,
                is_different_from_previous=True,
                attribution="One bounded diagnostic assumption changed.",
                source_references=selected_references,
            ),
        )
    return FieldAssumptionDiagnostic(
        case_identity="sha256:" + "2" * 64,
        result_reference=reference_for(b"result"),
        aperture_reference=baseline_reference,
        response_references=response_references or selected_references,
        field_reference=reference_for(b"field"),
        focus_reference=reference_for(b"focus"),
        focal_region_reference=reference_for(b"region"),
        endpoint_comparison_identity="sha256:" + "3" * 64,
        endpoint_dispositions=(("focus efficiency", "context only"),),
        assignment="synthetic contract fixture",
        fixed_context=(("normalization", "fixed"),),
        variants=variants,
        first_divergent_step=step,
        no_divergence_reason=(
            "Every applicable diagnostic field agrees." if step is None else None
        ),
        vector_provenance=(
            VectorFieldProvenance(
                component_names=("x", "y", "z"),
                rectilinear_surface_references=selected_references,
                formation="uniform",
                propagation="vector",
                longitudinal_power_reference=reference_for(b"longitudinal"),
            )
            if step == "sampled surface"
            else None
        ),
    )
