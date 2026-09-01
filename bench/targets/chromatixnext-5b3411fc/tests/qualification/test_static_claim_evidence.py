from __future__ import annotations

import copy
from dataclasses import replace
import itertools
import math
from pathlib import Path
import tomllib

import pytest
import torch

from tests.qualification.michelson_claim_support import (
    MichelsonWitnessPrograms,
    construct_michelson_witness_programs,
)
from tools.qualify_example_evidence import (
    ANCHOR_KINDS,
    QUALIFICATION_FINDING_IDENTITIES,
    WITNESS_KINDS,
    ClosureDecision,
    ExampleEvidence,
    QualificationFinding,
    ResponseWitnessRecord,
    load_example_evidence,
    parse_example_evidence,
    qualify_example_claims,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_PATH = (
    PROJECT_ROOT
    / "examples"
    / "analytic_michelson_interferometer"
    / "evidence.toml"
)


@pytest.fixture(scope="module")
def static_data() -> dict[str, object]:
    """
    Load mutable test input independently from the strict parser

    """

    with EVIDENCE_PATH.open("rb") as evidence_file:
        return tomllib.load(evidence_file)


@pytest.fixture(scope="module")
def evidence() -> ExampleEvidence:
    """
    Return the valid parsed Michelson static evidence

    """

    parsed = load_example_evidence(EVIDENCE_PATH, project_root=PROJECT_ROOT)
    assert parsed.findings == ()
    assert parsed.evidence is not None
    return parsed.evidence


@pytest.fixture(scope="module")
def programs() -> MichelsonWitnessPrograms:
    """
    Construct the baseline and counterfactual once for this test module

    """

    return construct_michelson_witness_programs()


def _finding_identities(findings: tuple[QualificationFinding, ...]) -> tuple[str, ...]:
    return tuple(finding.identity for finding in findings)


def _parsed_mutation(data: dict[str, object]) -> ExampleEvidence:
    parsed = parse_example_evidence(data, project_root=PROJECT_ROOT)
    assert parsed.findings == ()
    assert parsed.evidence is not None
    return parsed.evidence


def _claim(data: dict[str, object]) -> dict[str, object]:
    claims = data["claims"]
    assert isinstance(claims, list)
    claim = claims[0]
    assert isinstance(claim, dict)
    return claim


def _witnesses(data: dict[str, object]) -> list[dict[str, object]]:
    witnesses = _claim(data)["challenge_witnesses"]
    assert isinstance(witnesses, list)
    assert all(isinstance(witness, dict) for witness in witnesses)
    return witnesses  # type: ignore[return-value]


def _qualify(
    evidence: ExampleEvidence,
    programs: MichelsonWitnessPrograms,
    records: tuple[ResponseWitnessRecord, ...],
) -> tuple[QualificationFinding, ...]:
    return qualify_example_claims(
        evidence,
        frozen_facts=programs.baseline_facts,
        witness_records=records,
    ).findings


def test_static_schema_and_closed_kinds_are_exact(
    static_data: dict[str, object],
    evidence: ExampleEvidence,
) -> None:
    assert set(static_data) == {"claims"}
    claim = _claim(static_data)
    assert set(claim) == {
        "name",
        "subject_anchors",
        "observable_name",
        "acceptance",
        "challenge_witnesses",
    }
    assert {anchor.kind for anchor in evidence.claims[0].subject_anchors} <= (
        ANCHOR_KINDS
    )
    assert {
        witness.kind for witness in evidence.claims[0].challenge_witnesses
    } <= WITNESS_KINDS
    assert QUALIFICATION_FINDING_IDENTITIES == {
        "example_claim_name_invalid",
        "example_claim_subject_anchor_invalid",
        "example_claim_observable_invalid",
        "example_claim_ancestry_invalid",
        "example_claim_acceptance_invalid",
        "example_claim_witness_missing",
        "example_claim_witness_nondiscriminating",
        "example_claim_witness_coverage_incomplete",
    }


@pytest.mark.parametrize(
    ("location", "field", "identity"),
    (
        ("root", "device_selector", "example_claim_name_invalid"),
        ("claim", "mutation_callback", "example_claim_name_invalid"),
        ("acceptance", "optimizer", "example_claim_acceptance_invalid"),
        ("witness", "callable", "example_claim_witness_missing"),
        ("witness", "module", "example_claim_witness_missing"),
        ("witness", "tensor", "example_claim_witness_missing"),
        ("witness", "executable_code", "example_claim_witness_missing"),
    ),
)
def test_executable_device_and_mutation_fields_are_rejected(
    static_data: dict[str, object],
    location: str,
    field: str,
    identity: str,
) -> None:
    mutated = copy.deepcopy(static_data)
    target: dict[str, object]
    if location == "root":
        target = mutated
    elif location == "claim":
        target = _claim(mutated)
    elif location == "acceptance":
        acceptance = _claim(mutated)["acceptance"]
        assert isinstance(acceptance, dict)
        target = acceptance
    else:
        target = _witnesses(mutated)[0]
    target[field] = "lambda_payload"

    parsed = parse_example_evidence(mutated, project_root=PROJECT_ROOT)

    assert _finding_identities(parsed.findings) == (identity,)


@pytest.mark.parametrize(
    "forbidden_identity",
    (
        "cuda_device_zero",
        "mutation_callback",
        "callable_witness",
        "optimizer_step",
        "tensor_payload",
        "python_object_id",
        "executable_code",
    ),
)
def test_forbidden_runtime_meanings_cannot_hide_in_static_identities(
    static_data: dict[str, object],
    forbidden_identity: str,
) -> None:
    mutated = copy.deepcopy(static_data)
    _witnesses(mutated)[0]["challenge_action"] = forbidden_identity

    parsed = parse_example_evidence(mutated, project_root=PROJECT_ROOT)

    assert _finding_identities(parsed.findings) == (
        "example_claim_witness_nondiscriminating",
    )


@pytest.mark.parametrize("kind", ("port", "component", "callable"))
def test_unknown_anchor_kinds_have_the_frozen_finding(
    static_data: dict[str, object],
    kind: str,
) -> None:
    mutated = copy.deepcopy(static_data)
    anchors = _claim(mutated)["subject_anchors"]
    assert isinstance(anchors, list)
    assert isinstance(anchors[0], dict)
    anchors[0]["kind"] = kind

    parsed = parse_example_evidence(mutated, project_root=PROJECT_ROOT)

    assert _finding_identities(parsed.findings) == (
        "example_claim_subject_anchor_invalid",
    )


@pytest.mark.parametrize("kind", ("runtime", "callback", "hard_error"))
def test_unknown_witness_kinds_have_the_frozen_finding(
    static_data: dict[str, object],
    kind: str,
) -> None:
    mutated = copy.deepcopy(static_data)
    _witnesses(mutated)[0]["kind"] = kind

    parsed = parse_example_evidence(mutated, project_root=PROJECT_ROOT)

    assert _finding_identities(parsed.findings) == (
        "example_claim_witness_nondiscriminating",
    )


@pytest.mark.parametrize(
    "missing_field",
    (
        "name",
        "kind",
        "targeted_anchors",
        "supported_baseline_point",
        "challenge_action",
        "required_observable_name",
        "expected_relation",
        "finite_tolerance",
        "stable_failure_identity",
        "oracle_node_id",
        "expected_discrimination",
    ),
)
def test_every_witness_card_field_is_required(
    static_data: dict[str, object],
    missing_field: str,
) -> None:
    mutated = copy.deepcopy(static_data)
    del _witnesses(mutated)[0][missing_field]

    parsed = parse_example_evidence(mutated, project_root=PROJECT_ROOT)

    assert _finding_identities(parsed.findings) == (
        "example_claim_witness_missing",
    )


def test_malformed_or_unlocatable_pytest_node_id_is_rejected(
    static_data: dict[str, object],
) -> None:
    mutated = copy.deepcopy(static_data)
    _witnesses(mutated)[0]["oracle_node_id"] = "not_a_pytest_node"

    parsed = parse_example_evidence(mutated, project_root=PROJECT_ROOT)

    assert _finding_identities(parsed.findings) == (
        "example_claim_witness_nondiscriminating",
    )


def test_michelson_static_claim_qualifies_from_one_frozen_fact(
    evidence: ExampleEvidence,
    programs: MichelsonWitnessPrograms,
) -> None:
    result = qualify_example_claims(
        evidence,
        frozen_facts=programs.baseline_facts,
        witness_records=programs.records,
    )

    assert result.findings == ()
    assert result.observationally_closed
    assert result.witness_records == programs.records
    assert result.witness_records[0].baseline_observable != (
        result.witness_records[0].challenged_observable
    )


def test_phase_omission_witness_is_nonzero(
    programs: MichelsonWitnessPrograms,
) -> None:
    record = programs.records[0]

    assert record.witness_name == "phase_omission_counterfactual"
    assert record.baseline_observable != record.challenged_observable
    assert record.actual_discrimination >= 0.20
    assert record.actual_discrimination > record.finite_tolerance
    assert record.sensitivity_magnitude is None


def test_metamorphic_port_ratio_rejects_wrong_model(
    programs: MichelsonWitnessPrograms,
) -> None:
    record = programs.records[1]
    assert record.wrong_model_observable is not None

    correct_error = abs(
        record.baseline_observable[0] - record.challenged_observable[0],
    )
    wrong_model_error = abs(
        record.baseline_observable[0] - record.wrong_model_observable[0],
    )
    assert correct_error <= record.finite_tolerance
    assert wrong_model_error >= 0.20
    assert wrong_model_error > record.finite_tolerance
    assert record.wrong_model_name == "split_then_add_intensity_wrong_model"


def test_separate_counterfactual_does_not_mutate_hosted_baseline(
    programs: MichelsonWitnessPrograms,
) -> None:
    assert tuple(name for name, _value in programs.baseline_state_before) == tuple(
        name for name, _value in programs.baseline_state_after
    )
    assert all(
        (
            torch.equal(before, after)
            if isinstance(before, torch.Tensor)
            and isinstance(after, torch.Tensor)
            else before == after
        )
        for (_name, before), (_same_name, after) in zip(
            programs.baseline_state_before,
            programs.baseline_state_after,
            strict=True,
        )
    )


def test_empty_ancestry_cannot_be_replaced_by_a_second_graph(
    evidence: ExampleEvidence,
    programs: MichelsonWitnessPrograms,
) -> None:
    without_ancestry = replace(programs.baseline_facts, ancestry=())

    result = qualify_example_claims(
        evidence,
        frozen_facts=without_ancestry,
        witness_records=programs.records,
    )

    assert _finding_identities(result.findings) == (
        "example_claim_ancestry_invalid",
    )


def test_unrelated_detection_cannot_close_the_claim(
    static_data: dict[str, object],
    programs: MichelsonWitnessPrograms,
) -> None:
    mutated = copy.deepcopy(static_data)
    anchors = _claim(mutated)["subject_anchors"]
    assert isinstance(anchors, list)
    detection = next(
        anchor
        for anchor in anchors
        if isinstance(anchor, dict) and anchor.get("kind") == "detection_law"
    )
    detection["coordinate"] = "bottom_detector"
    for witness in _witnesses(mutated):
        targeted = witness["targeted_anchors"]
        assert isinstance(targeted, list)
        for anchor in targeted:
            if isinstance(anchor, dict) and anchor.get("kind") == "detection_law":
                anchor["coordinate"] = "bottom_detector"
    changed_evidence = _parsed_mutation(mutated)

    findings = _qualify(changed_evidence, programs, programs.records)

    assert _finding_identities(findings) == (
        "example_claim_ancestry_invalid",
    )
    assert findings[0].render() == (
        "example_claim_ancestry_invalid:"
        "claim=michelson_relative_phase_response:subject=bottom_detector:"
        "observable=left_intensity:acceptance=relative_port_ratio"
    )


@pytest.mark.parametrize(
    ("replacement", "identity"),
    (
        ({"baseline_input_norm": 0.0}, "example_claim_witness_nondiscriminating"),
        (
            {"normalization_denominator": 0.0},
            "example_claim_witness_nondiscriminating",
        ),
        (
            {"challenged_observable": (0.2499999999992463,)},
            "example_claim_witness_nondiscriminating",
        ),
        (
            {"baseline_observable": (math.nan,)},
            "example_claim_witness_nondiscriminating",
        ),
        (
            {"challenged_observable": (math.inf,)},
            "example_claim_witness_nondiscriminating",
        ),
    ),
)
def test_nonadmissible_response_probes_have_exact_finding(
    evidence: ExampleEvidence,
    programs: MichelsonWitnessPrograms,
    replacement: dict[str, object],
    identity: str,
) -> None:
    challenged = replace(programs.records[0], **replacement)
    records = (challenged, programs.records[1])

    findings = _qualify(evidence, programs, records)

    assert identity in _finding_identities(findings)
    assert all(
        finding.identity in QUALIFICATION_FINDING_IDENTITIES
        for finding in findings
    )


def test_zero_sensitivity_point_is_not_admitted(
    static_data: dict[str, object],
    programs: MichelsonWitnessPrograms,
) -> None:
    mutated = copy.deepcopy(static_data)
    _witnesses(mutated)[0]["kind"] = "sensitivity"
    changed_evidence = _parsed_mutation(mutated)
    zero_sensitivity = replace(
        programs.records[0],
        sensitivity_magnitude=0.0,
    )

    findings = _qualify(
        changed_evidence,
        programs,
        (zero_sensitivity, programs.records[1]),
    )

    assert _finding_identities(findings) == (
        "example_claim_witness_nondiscriminating",
    )


def test_missing_tolerance_has_the_frozen_finding(
    static_data: dict[str, object],
) -> None:
    mutated = copy.deepcopy(static_data)
    del _witnesses(mutated)[0]["finite_tolerance"]

    parsed = parse_example_evidence(mutated, project_root=PROJECT_ROOT)

    assert _finding_identities(parsed.findings) == (
        "example_claim_witness_missing",
    )


def test_uncovered_anchor_has_the_frozen_finding(
    static_data: dict[str, object],
    programs: MichelsonWitnessPrograms,
) -> None:
    mutated = copy.deepcopy(static_data)
    second_targets = _witnesses(mutated)[1]["targeted_anchors"]
    assert isinstance(second_targets, list)
    second_targets[:] = [
        anchor
        for anchor in second_targets
        if not (
            isinstance(anchor, dict)
            and anchor.get("kind") == "owner"
            and anchor.get("coordinate") == "cube"
        )
    ]
    changed_evidence = _parsed_mutation(mutated)

    findings = _qualify(changed_evidence, programs, programs.records)

    assert _finding_identities(findings) == (
        "example_claim_witness_coverage_incomplete",
    )


def test_hard_failure_does_not_close_a_response_claim(
    evidence: ExampleEvidence,
    programs: MichelsonWitnessPrograms,
) -> None:
    hard_failure = replace(
        programs.records[0],
        hard_failure_identity="assembly_directional_output_disposition_missing",
    )

    findings = _qualify(
        evidence,
        programs,
        (hard_failure, programs.records[1]),
    )

    assert "example_claim_witness_nondiscriminating" in (
        _finding_identities(findings)
    )


def test_hard_failure_closes_only_an_admission_failure_claim(
    static_data: dict[str, object],
    programs: MichelsonWitnessPrograms,
) -> None:
    mutated = copy.deepcopy(static_data)
    claim = _claim(mutated)
    acceptance = claim["acceptance"]
    assert isinstance(acceptance, dict)
    acceptance["metric"] = "admission_failure"
    acceptance["relation"] = "raises_stable_failure"
    witnesses = _witnesses(mutated)
    witnesses[:] = [witnesses[0]]
    witnesses[0]["kind"] = "counterfactual"
    witnesses[0]["expected_relation"] = "raises_stable_failure"
    witnesses[0]["challenge_action"] = "omit_directional_disposition"
    witnesses[0]["targeted_anchors"] = copy.deepcopy(claim["subject_anchors"])
    admission_evidence = _parsed_mutation(mutated)
    hard_failure = replace(
        programs.records[0],
        challenge_action="omit_directional_disposition",
        expected_relation="raises_stable_failure",
        hard_failure_identity="assembly_directional_output_disposition_missing",
        baseline_observable=(),
        challenged_observable=(),
        actual_discrimination=0.0,
    )

    findings = _qualify(admission_evidence, programs, (hard_failure,))

    assert findings == ()


@pytest.mark.parametrize(
    ("structural", "observational", "execution"),
    tuple(itertools.product((False, True), repeat=3)),
)
def test_three_closures_have_a_noncompensating_truth_table(
    structural: bool,
    observational: bool,
    execution: bool,
) -> None:
    decision = ClosureDecision(
        structural=structural,
        observational=observational,
        execution=execution,
    )

    assert decision.qualified is (
        structural and observational and execution
    )
