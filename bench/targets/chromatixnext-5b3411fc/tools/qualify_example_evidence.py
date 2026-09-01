from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
from pathlib import Path
import re
import tomllib
from typing import Any

ANCHOR_KINDS = frozenset(
    {
        "owner",
        "encounter",
        "produced_value",
        "detection_law",
    },
)
WITNESS_KINDS = frozenset(
    {
        "counterfactual",
        "sensitivity",
        "metamorphic",
    },
)
QUALIFICATION_FINDING_IDENTITIES = frozenset(
    {
        "example_claim_name_invalid",
        "example_claim_subject_anchor_invalid",
        "example_claim_observable_invalid",
        "example_claim_ancestry_invalid",
        "example_claim_acceptance_invalid",
        "example_claim_witness_missing",
        "example_claim_witness_nondiscriminating",
        "example_claim_witness_coverage_incomplete",
    },
)

_CLAIM_FIELDS = frozenset(
    {
        "name",
        "subject_anchors",
        "observable_name",
        "acceptance",
        "challenge_witnesses",
    },
)
_ANCHOR_FIELDS = frozenset({"kind", "coordinate"})
_ACCEPTANCE_COMMON_FIELDS = frozenset(
    {
        "metric",
        "relation",
        "tolerance",
    },
)
_WITNESS_FIELDS = frozenset(
    {
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
    },
)
_RESPONSE_RELATIONS = frozenset(
    {
        "nonzero_separation",
        "metamorphic_equality",
        "raises_stable_failure",
    },
)
_ACCEPTANCE_RELATIONS = frozenset(
    {
        "absolute_error_at_most",
        "within_inclusive_range",
        "raises_stable_failure",
    },
)
_FORBIDDEN_STATIC_IDENTITY_PARTS = frozenset(
    {
        "callable",
        "callback",
        "cpu",
        "cuda",
        "device",
        "eval",
        "exec",
        "executable",
        "import",
        "lambda",
        "module",
        "mutation",
        "optimizer",
        "pythonobjectid",
        "tensor",
    },
)
_SIMPLE_IDENTITY = re.compile(r"[a-z][a-z0-9_]*\Z")
_PRODUCED_COMPONENT = re.compile(
    r"component=[a-z][a-z0-9_]*:port=(?:-|[a-z][a-z0-9_]*)"
    r":direction=(?:input|output)\Z",
)
_PRODUCED_DIRECTIONAL = re.compile(
    r"encounter=[a-z][a-z0-9_]*:owner=[a-z][a-z0-9_]*"
    r":terminal=[a-z][a-z0-9_]*:direction=(?:incident|outgoing)\Z",
)
_PYTEST_NODE_ID = re.compile(
    r"tests/(?:[a-zA-Z0-9_./-]+)\.py::"
    r"[a-zA-Z_][a-zA-Z0-9_]*(?:::[a-zA-Z_][a-zA-Z0-9_]*)?\Z",
)


@dataclass(frozen=True, slots=True)
class ClaimAnchor:
    """
    One closed static subject coordinate

    """

    kind: str
    coordinate: str


@dataclass(frozen=True, slots=True)
class ClaimAcceptance:
    """
    One static response or admission relation

    """

    metric: str
    relation: str
    expected: float | None
    expected_range: tuple[float, float] | None
    tolerance: float
    normalization: str | None
    unit: str | None


@dataclass(frozen=True, slots=True)
class ChallengeWitness:
    """
    The complete static witness card required by the specification

    """

    name: str
    kind: str
    targeted_anchors: tuple[ClaimAnchor, ...]
    supported_baseline_point: str
    challenge_action: str
    required_observable_name: str
    expected_relation: str
    finite_tolerance: float
    stable_failure_identity: str
    oracle_node_id: str
    expected_discrimination: float


@dataclass(frozen=True, slots=True)
class ExampleClaim:
    """
    One parsed static Example claim

    """

    name: str
    subject_anchors: tuple[ClaimAnchor, ...]
    observable_name: str
    acceptance: ClaimAcceptance
    challenge_witnesses: tuple[ChallengeWitness, ...]


@dataclass(frozen=True, slots=True)
class ExampleEvidence:
    """
    The complete static claim document for one Example

    """

    claims: tuple[ExampleClaim, ...]


@dataclass(frozen=True, slots=True)
class QualificationFinding:
    """
    A stable tool finding with the frozen locator field order

    """

    identity: str
    claim: str | None = None
    subject: str | None = None
    observable: str | None = None
    acceptance: str | None = None
    witness: str | None = None

    def render(self) -> str:
        """
        Render the stable identity and all available ordered locators

        """

        values = (
            ("claim", self.claim),
            ("subject", self.subject),
            ("observable", self.observable),
            ("acceptance", self.acceptance),
            ("witness", self.witness),
        )
        last_present = -1
        for index, (_name, value) in enumerate(values):
            if value is not None:
                last_present = index
        if last_present < 0:
            return self.identity
        suffix = ":".join(
            f"{name}={value if value is not None else '-'}"
            for name, value in values[: last_present + 1]
        )
        return f"{self.identity}:{suffix}"


@dataclass(frozen=True, slots=True)
class EvidenceParseResult:
    """
    The parsed evidence or its deterministic schema findings

    """

    evidence: ExampleEvidence | None
    findings: tuple[QualificationFinding, ...]


@dataclass(frozen=True, slots=True)
class ResponseWitnessRecord:
    """
    Retained results from separately constructed ordinary test programs

    """

    claim_name: str
    witness_name: str
    supported_baseline_point: str
    challenge_action: str
    required_observable_name: str
    normalization: str
    expected_relation: str
    finite_tolerance: float
    baseline_observable: tuple[float, ...]
    challenged_observable: tuple[float, ...]
    actual_discrimination: float
    baseline_input_norm: float
    normalization_denominator: float
    sensitivity_magnitude: float | None = None
    wrong_model_name: str | None = None
    wrong_model_observable: tuple[float, ...] | None = None
    hard_failure_identity: str | None = None


@dataclass(frozen=True, slots=True)
class QualificationResult:
    """
    Offline qualification findings and the retained witness records

    """

    findings: tuple[QualificationFinding, ...]
    witness_records: tuple[ResponseWitnessRecord, ...]

    @property
    def observationally_closed(self) -> bool:
        """
        Report whether claim evidence closes without a finding

        """

        return not self.findings


@dataclass(frozen=True, slots=True)
class ClosureDecision:
    """
    The three independent closure inputs and their conjunction

    """

    structural: bool
    observational: bool
    execution: bool

    @property
    def qualified(self) -> bool:
        """
        Require all three closures without mutual compensation

        """

        return self.structural and self.observational and self.execution


def load_example_evidence(
    evidence_path: Path,
    *,
    project_root: Path,
) -> EvidenceParseResult:
    """
    Load and strictly parse one static evidence document

    """

    try:
        with evidence_path.open("rb") as evidence_file:
            data = tomllib.load(evidence_file)
    except (OSError, tomllib.TOMLDecodeError):
        return EvidenceParseResult(
            evidence=None,
            findings=(
                QualificationFinding("example_claim_name_invalid"),
            ),
        )
    return parse_example_evidence(data, project_root=project_root)


def parse_example_evidence(
    data: Mapping[str, Any],
    *,
    project_root: Path,
) -> EvidenceParseResult:
    """
    Parse only the exact section-13 static schema and closed kinds

    """

    if set(data) != {"claims"} or not isinstance(data.get("claims"), list):
        return _parse_failure("example_claim_name_invalid")
    raw_claims = data["claims"]
    if not raw_claims:
        return _parse_failure("example_claim_name_invalid")
    claims: list[ExampleClaim] = []
    names: set[str] = set()
    for raw_claim in raw_claims:
        parsed, finding = _parse_claim(raw_claim, project_root=project_root)
        if finding is not None:
            return EvidenceParseResult(evidence=None, findings=(finding,))
        assert parsed is not None
        if parsed.name in names:
            return _parse_failure(
                "example_claim_name_invalid",
                claim=parsed.name,
            )
        names.add(parsed.name)
        claims.append(parsed)
    return EvidenceParseResult(
        evidence=ExampleEvidence(claims=tuple(claims)),
        findings=(),
    )


def qualify_example_claims(
    evidence: ExampleEvidence,
    *,
    frozen_facts: object,
    witness_records: Sequence[ResponseWitnessRecord],
) -> QualificationResult:
    """
    Qualify claims from one frozen Assembly fact and separate records

    """

    records_by_key: dict[tuple[str, str], ResponseWitnessRecord] = {}
    duplicate_record_keys: set[tuple[str, str]] = set()
    for record in witness_records:
        key = (record.claim_name, record.witness_name)
        if key in records_by_key:
            duplicate_record_keys.add(key)
        records_by_key[key] = record

    findings: list[QualificationFinding] = []
    for claim in evidence.claims:
        observable_value = _observable_value(frozen_facts, claim.observable_name)
        if observable_value is None:
            findings.append(_claim_finding("example_claim_observable_invalid", claim))
            continue
        lineage = _observable_lineage(frozen_facts, observable_value)
        if lineage is None:
            findings.append(_claim_finding("example_claim_ancestry_invalid", claim))
            continue

        ancestry_failed = False
        for anchor in claim.subject_anchors:
            if not _anchor_exists(frozen_facts, anchor):
                findings.append(
                    _claim_finding(
                        "example_claim_subject_anchor_invalid",
                        claim,
                        subject=anchor.coordinate,
                    ),
                )
                ancestry_failed = True
            elif not _anchor_in_lineage(anchor, lineage, observable_value):
                findings.append(
                    _claim_finding(
                        "example_claim_ancestry_invalid",
                        claim,
                        subject=anchor.coordinate,
                    ),
                )
                ancestry_failed = True
        if ancestry_failed:
            continue

        required_anchors = set(claim.subject_anchors)
        covered_anchors = {
            anchor
            for witness in claim.challenge_witnesses
            for anchor in witness.targeted_anchors
        }
        if not required_anchors.issubset(covered_anchors):
            uncovered = next(
                anchor
                for anchor in claim.subject_anchors
                if anchor not in covered_anchors
            )
            findings.append(
                _claim_finding(
                    "example_claim_witness_coverage_incomplete",
                    claim,
                    subject=uncovered.coordinate,
                ),
            )
            continue

        valid_response_records: list[ResponseWitnessRecord] = []
        for witness in claim.challenge_witnesses:
            key = (claim.name, witness.name)
            if key in duplicate_record_keys or key not in records_by_key:
                findings.append(
                    _claim_finding(
                        "example_claim_witness_missing",
                        claim,
                        witness=witness.name,
                    ),
                )
                continue
            record = records_by_key[key]
            record_finding = _response_record_finding(
                claim,
                witness,
                record,
            )
            if record_finding is not None:
                findings.append(record_finding)
            elif record.hard_failure_identity is None:
                valid_response_records.append(record)
        if any(finding.claim == claim.name for finding in findings):
            continue
        if not _acceptance_is_met(claim.acceptance, valid_response_records):
            findings.append(_claim_finding("example_claim_acceptance_invalid", claim))

    return QualificationResult(
        findings=tuple(findings),
        witness_records=tuple(witness_records),
    )


def _parse_failure(
    identity: str,
    *,
    claim: str | None = None,
    subject: str | None = None,
    observable: str | None = None,
    acceptance: str | None = None,
    witness: str | None = None,
) -> EvidenceParseResult:
    return EvidenceParseResult(
        evidence=None,
        findings=(
            QualificationFinding(
                identity=identity,
                claim=claim,
                subject=subject,
                observable=observable,
                acceptance=acceptance,
                witness=witness,
            ),
        ),
    )


def _parse_claim(
    raw_claim: object,
    *,
    project_root: Path,
) -> tuple[ExampleClaim | None, QualificationFinding | None]:
    if not isinstance(raw_claim, dict) or set(raw_claim) != _CLAIM_FIELDS:
        return None, QualificationFinding("example_claim_name_invalid")
    name = raw_claim["name"]
    observable = raw_claim["observable_name"]
    if not _is_identity(name):
        return None, QualificationFinding("example_claim_name_invalid")
    if not _is_identity(observable):
        return None, QualificationFinding(
            "example_claim_observable_invalid",
            claim=name,
        )

    anchors, finding = _parse_anchors(
        raw_claim["subject_anchors"],
        claim=name,
    )
    if finding is not None:
        return None, finding
    acceptance, finding = _parse_acceptance(
        raw_claim["acceptance"],
        claim=name,
        observable=observable,
    )
    if finding is not None:
        return None, finding
    witnesses, finding = _parse_witnesses(
        raw_claim["challenge_witnesses"],
        claim=name,
        observable=observable,
        subject_anchors=anchors,
        project_root=project_root,
    )
    if finding is not None:
        return None, finding
    assert acceptance is not None
    return (
        ExampleClaim(
            name=name,
            subject_anchors=anchors,
            observable_name=observable,
            acceptance=acceptance,
            challenge_witnesses=witnesses,
        ),
        None,
    )


def _parse_anchors(
    raw_anchors: object,
    *,
    claim: str,
) -> tuple[tuple[ClaimAnchor, ...], QualificationFinding | None]:
    if not isinstance(raw_anchors, list) or not raw_anchors:
        return (), QualificationFinding(
            "example_claim_subject_anchor_invalid",
            claim=claim,
        )
    anchors: list[ClaimAnchor] = []
    for raw_anchor in raw_anchors:
        if not isinstance(raw_anchor, dict) or set(raw_anchor) != _ANCHOR_FIELDS:
            return (), QualificationFinding(
                "example_claim_subject_anchor_invalid",
                claim=claim,
            )
        kind = raw_anchor["kind"]
        coordinate = raw_anchor["coordinate"]
        if (
            kind not in ANCHOR_KINDS
            or not isinstance(coordinate, str)
            or not _anchor_coordinate_is_valid(kind, coordinate)
        ):
            return (), QualificationFinding(
                "example_claim_subject_anchor_invalid",
                claim=claim,
                subject=coordinate if isinstance(coordinate, str) else None,
            )
        anchors.append(ClaimAnchor(kind=kind, coordinate=coordinate))
    if len(set(anchors)) != len(anchors):
        return (), QualificationFinding(
            "example_claim_subject_anchor_invalid",
            claim=claim,
        )
    return tuple(anchors), None


def _parse_acceptance(
    raw_acceptance: object,
    *,
    claim: str,
    observable: str,
) -> tuple[ClaimAcceptance | None, QualificationFinding | None]:
    finding = QualificationFinding(
        "example_claim_acceptance_invalid",
        claim=claim,
        observable=observable,
    )
    if not isinstance(raw_acceptance, dict):
        return None, finding
    keys = set(raw_acceptance)
    target_keys = keys & {"expected", "range"}
    scale_keys = keys & {"normalization", "unit"}
    expected_keys = _ACCEPTANCE_COMMON_FIELDS | target_keys | scale_keys
    if (
        keys != expected_keys
        or len(target_keys) != 1
        or len(scale_keys) != 1
    ):
        return None, finding
    metric = raw_acceptance["metric"]
    relation = raw_acceptance["relation"]
    tolerance = raw_acceptance["tolerance"]
    if (
        not _is_identity(metric)
        or relation not in _ACCEPTANCE_RELATIONS
        or not _is_positive_finite(tolerance)
    ):
        return None, finding
    normalization = raw_acceptance.get("normalization")
    unit = raw_acceptance.get("unit")
    if not _is_identity(normalization if normalization is not None else unit):
        return None, finding

    expected: float | None = None
    expected_range: tuple[float, float] | None = None
    if "expected" in raw_acceptance:
        if not _is_finite_number(raw_acceptance["expected"]):
            return None, finding
        expected = float(raw_acceptance["expected"])
    else:
        raw_range = raw_acceptance["range"]
        if (
            not isinstance(raw_range, list)
            or len(raw_range) != 2
            or not all(_is_finite_number(value) for value in raw_range)
            or float(raw_range[0]) > float(raw_range[1])
        ):
            return None, finding
        expected_range = (float(raw_range[0]), float(raw_range[1]))
    if relation == "within_inclusive_range" and expected_range is None:
        return None, finding
    if relation == "absolute_error_at_most" and expected is None:
        return None, finding
    return (
        ClaimAcceptance(
            metric=metric,
            relation=relation,
            expected=expected,
            expected_range=expected_range,
            tolerance=float(tolerance),
            normalization=normalization,
            unit=unit,
        ),
        None,
    )


def _parse_witnesses(
    raw_witnesses: object,
    *,
    claim: str,
    observable: str,
    subject_anchors: tuple[ClaimAnchor, ...],
    project_root: Path,
) -> tuple[tuple[ChallengeWitness, ...], QualificationFinding | None]:
    if not isinstance(raw_witnesses, list) or not raw_witnesses:
        return (), QualificationFinding(
            "example_claim_witness_missing",
            claim=claim,
            observable=observable,
        )
    witnesses: list[ChallengeWitness] = []
    names: set[str] = set()
    for raw_witness in raw_witnesses:
        parsed, finding = _parse_witness(
            raw_witness,
            claim=claim,
            observable=observable,
            subject_anchors=subject_anchors,
            project_root=project_root,
        )
        if finding is not None:
            return (), finding
        assert parsed is not None
        if parsed.name in names:
            return (), QualificationFinding(
                "example_claim_witness_missing",
                claim=claim,
                observable=observable,
                witness=parsed.name,
            )
        names.add(parsed.name)
        witnesses.append(parsed)
    return tuple(witnesses), None


def _parse_witness(
    raw_witness: object,
    *,
    claim: str,
    observable: str,
    subject_anchors: tuple[ClaimAnchor, ...],
    project_root: Path,
) -> tuple[ChallengeWitness | None, QualificationFinding | None]:
    if not isinstance(raw_witness, dict) or set(raw_witness) != _WITNESS_FIELDS:
        return None, QualificationFinding(
            "example_claim_witness_missing",
            claim=claim,
            observable=observable,
        )
    name = raw_witness["name"]
    finding = QualificationFinding(
        "example_claim_witness_nondiscriminating",
        claim=claim,
        observable=observable,
        witness=name if isinstance(name, str) else None,
    )
    if not _is_identity(name) or raw_witness["kind"] not in WITNESS_KINDS:
        return None, finding
    targeted, anchor_finding = _parse_anchors(
        raw_witness["targeted_anchors"],
        claim=claim,
    )
    if anchor_finding is not None or not set(targeted).issubset(subject_anchors):
        return None, QualificationFinding(
            "example_claim_subject_anchor_invalid",
            claim=claim,
            observable=observable,
            witness=name,
        )
    static_identities = (
        raw_witness["supported_baseline_point"],
        raw_witness["challenge_action"],
        raw_witness["required_observable_name"],
    )
    if not all(
        _is_static_scientific_identity(value)
        for value in static_identities
    ):
        return None, finding
    if raw_witness["required_observable_name"] != observable:
        return None, finding
    if raw_witness["expected_relation"] not in _RESPONSE_RELATIONS:
        return None, finding
    if not _is_positive_finite(raw_witness["finite_tolerance"]):
        return None, finding
    if raw_witness["stable_failure_identity"] not in (
        QUALIFICATION_FINDING_IDENTITIES
    ):
        return None, finding
    if not _is_positive_finite(raw_witness["expected_discrimination"]):
        return None, finding
    if float(raw_witness["expected_discrimination"]) <= float(
        raw_witness["finite_tolerance"],
    ):
        return None, finding
    node_id = raw_witness["oracle_node_id"]
    if not isinstance(node_id, str) or not _node_id_is_locatable(
        project_root,
        node_id,
    ):
        return None, finding
    if (
        raw_witness["kind"] == "metamorphic"
        and raw_witness["expected_relation"] != "metamorphic_equality"
    ):
        return None, finding
    return (
        ChallengeWitness(
            name=name,
            kind=raw_witness["kind"],
            targeted_anchors=targeted,
            supported_baseline_point=raw_witness["supported_baseline_point"],
            challenge_action=raw_witness["challenge_action"],
            required_observable_name=raw_witness["required_observable_name"],
            expected_relation=raw_witness["expected_relation"],
            finite_tolerance=float(raw_witness["finite_tolerance"]),
            stable_failure_identity=raw_witness["stable_failure_identity"],
            oracle_node_id=node_id,
            expected_discrimination=float(
                raw_witness["expected_discrimination"],
            ),
        ),
        None,
    )


def _node_id_is_locatable(project_root: Path, node_id: str) -> bool:
    if _PYTEST_NODE_ID.fullmatch(node_id) is None:
        return False
    path_text, *node_parts = node_id.split("::")
    test_path = project_root / path_text
    if not test_path.is_file():
        return False
    try:
        tree = ast.parse(test_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeError):
        return False
    nodes: Sequence[ast.stmt] = tree.body
    for part in node_parts:
        match = next(
            (
                node
                for node in nodes
                if isinstance(
                    node,
                    (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
                )
                and node.name == part
            ),
            None,
        )
        if match is None:
            return False
        nodes = match.body if isinstance(match, ast.ClassDef) else ()
    return True


def _response_record_finding(
    claim: ExampleClaim,
    witness: ChallengeWitness,
    record: ResponseWitnessRecord,
) -> QualificationFinding | None:
    finding = _claim_finding(
        witness.stable_failure_identity,
        claim,
        witness=witness.name,
    )
    expected_normalization = (
        claim.acceptance.normalization or claim.acceptance.unit
    )
    if (
        record.supported_baseline_point != witness.supported_baseline_point
        or record.challenge_action != witness.challenge_action
        or record.required_observable_name != witness.required_observable_name
        or record.normalization != expected_normalization
        or record.expected_relation != witness.expected_relation
        or record.finite_tolerance != witness.finite_tolerance
        or not _record_numbers_are_finite(record)
        or record.baseline_input_norm <= 0.0
        or record.normalization_denominator <= 0.0
    ):
        return finding
    if record.hard_failure_identity is not None:
        if (
            claim.acceptance.metric != "admission_failure"
            or claim.acceptance.relation != "raises_stable_failure"
            or witness.expected_relation != "raises_stable_failure"
            or not _is_identity(record.hard_failure_identity)
        ):
            return finding
        return None
    if claim.acceptance.metric == "admission_failure":
        return finding
    if (
        not record.baseline_observable
        or len(record.baseline_observable) != len(record.challenged_observable)
    ):
        return finding
    if witness.kind == "sensitivity":
        if (
            record.sensitivity_magnitude is None
            or record.sensitivity_magnitude <= witness.finite_tolerance
        ):
            return finding
    if witness.kind in {"counterfactual", "sensitivity"}:
        discrimination = _maximum_difference(
            record.baseline_observable,
            record.challenged_observable,
        )
        if (
            discrimination <= witness.finite_tolerance
            or discrimination < witness.expected_discrimination
            or not math.isclose(
                record.actual_discrimination,
                discrimination,
                rel_tol=0.0,
                abs_tol=16.0 * math.ulp(discrimination),
            )
        ):
            return finding
        return None
    if (
        witness.kind != "metamorphic"
        or record.wrong_model_name != witness.challenge_action
        or record.wrong_model_observable is None
        or len(record.wrong_model_observable) != len(record.baseline_observable)
    ):
        return finding
    equality_error = _maximum_difference(
        record.baseline_observable,
        record.challenged_observable,
    )
    wrong_model_error = _maximum_difference(
        record.baseline_observable,
        record.wrong_model_observable,
    )
    if (
        equality_error > witness.finite_tolerance
        or wrong_model_error <= witness.finite_tolerance
        or wrong_model_error < witness.expected_discrimination
        or not math.isclose(
            record.actual_discrimination,
            wrong_model_error,
            rel_tol=0.0,
            abs_tol=16.0 * math.ulp(wrong_model_error),
        )
    ):
        return finding
    return None


def _record_numbers_are_finite(record: ResponseWitnessRecord) -> bool:
    scalars = (
        record.finite_tolerance,
        record.actual_discrimination,
        record.baseline_input_norm,
        record.normalization_denominator,
    )
    optional_scalars = (
        ()
        if record.sensitivity_magnitude is None
        else (record.sensitivity_magnitude,)
    )
    wrong_model_observable = (
        ()
        if record.wrong_model_observable is None
        else record.wrong_model_observable
    )
    observations = (
        record.baseline_observable
        + record.challenged_observable
        + wrong_model_observable
    )
    return all(
        math.isfinite(value)
        for value in scalars + optional_scalars + observations
    )


def _acceptance_is_met(
    acceptance: ClaimAcceptance,
    records: Sequence[ResponseWitnessRecord],
) -> bool:
    if acceptance.metric == "admission_failure":
        return not records
    if not records:
        return False
    baseline = records[0].baseline_observable
    if len(baseline) != 1:
        return False
    observed = baseline[0]
    if acceptance.relation == "absolute_error_at_most":
        assert acceptance.expected is not None
        return abs(observed - acceptance.expected) <= acceptance.tolerance
    if acceptance.relation == "within_inclusive_range":
        assert acceptance.expected_range is not None
        lower, upper = acceptance.expected_range
        return lower - acceptance.tolerance <= observed <= upper + acceptance.tolerance
    return False


def _observable_value(frozen_facts: object, observable_name: str) -> object | None:
    exposures = getattr(frozen_facts, "exposures", ())
    exposed_identity = next(
        (identity for name, identity in exposures if name == observable_name),
        None,
    )
    if exposed_identity is None:
        return None
    for step in getattr(frozen_facts, "steps", ()):
        for port, value_identity in zip(
            step.output_ports,
            step.output_values,
            strict=True,
        ):
            if value_identity == exposed_identity:
                return ("component", step.component_name, port, "output")
    return None


def _observable_lineage(
    frozen_facts: object,
    observable_value: object,
) -> tuple[object, ...] | None:
    for ancestry_fact in getattr(frozen_facts, "ancestry", ()):
        if _coordinate_key(ancestry_fact.value) == observable_value:
            return ancestry_fact.ancestors
    return None


def _anchor_exists(frozen_facts: object, anchor: ClaimAnchor) -> bool:
    if anchor.kind == "owner":
        return any(
            owner.owner_name == anchor.coordinate
            for owner in getattr(frozen_facts, "directional_owners", ())
        )
    if anchor.kind == "encounter":
        return any(
            encounter.encounter_name == anchor.coordinate
            for encounter in getattr(frozen_facts, "encounters", ())
        )
    if anchor.kind == "produced_value":
        return any(
            _coordinate_text(ancestry.value) == anchor.coordinate
            and getattr(ancestry.value, "direction", None) in {"output", "outgoing"}
            for ancestry in getattr(frozen_facts, "ancestry", ())
        )
    if anchor.kind == "detection_law":
        return any(
            step.component_name == anchor.coordinate
            and any(
                getattr(value_kind, "__name__", "") == "Intensity"
                for value_kind in step.output_value_kinds
            )
            for step in getattr(frozen_facts, "steps", ())
        )
    return False


def _anchor_in_lineage(
    anchor: ClaimAnchor,
    lineage: tuple[object, ...],
    observable_value: object,
) -> bool:
    if anchor.kind == "detection_law":
        return (
            isinstance(observable_value, tuple)
            and len(observable_value) == 4
            and observable_value[0] == "component"
            and observable_value[1] == anchor.coordinate
        )
    if anchor.kind == "owner":
        return any(
            getattr(value, "owner_name", None) == anchor.coordinate
            for value in lineage
        )
    if anchor.kind == "encounter":
        return any(
            getattr(value, "encounter_name", None) == anchor.coordinate
            for value in lineage
        )
    return any(_coordinate_text(value) == anchor.coordinate for value in lineage)


def _coordinate_key(value: object) -> tuple[object, ...] | None:
    if hasattr(value, "component_name"):
        return (
            "component",
            getattr(value, "component_name"),
            getattr(value, "port"),
            getattr(value, "direction"),
        )
    if hasattr(value, "encounter_name"):
        return (
            "encounter",
            getattr(value, "encounter_name"),
            getattr(value, "owner_name"),
            getattr(value, "terminal"),
            getattr(value, "direction"),
        )
    return None


def _coordinate_text(value: object) -> str:
    key = _coordinate_key(value)
    if key is None:
        return ""
    if key[0] == "component":
        port = key[2] if key[2] is not None else "-"
        return f"component={key[1]}:port={port}:direction={key[3]}"
    return (
        f"encounter={key[1]}:owner={key[2]}:terminal={key[3]}"
        f":direction={key[4]}"
    )


def _claim_finding(
    identity: str,
    claim: ExampleClaim,
    *,
    subject: str | None = None,
    witness: str | None = None,
) -> QualificationFinding:
    return QualificationFinding(
        identity=identity,
        claim=claim.name,
        subject=subject,
        observable=claim.observable_name,
        acceptance=claim.acceptance.metric,
        witness=witness,
    )


def _anchor_coordinate_is_valid(kind: object, coordinate: str) -> bool:
    if kind in {"owner", "encounter", "detection_law"}:
        return _is_identity(coordinate)
    if kind == "produced_value":
        return (
            _PRODUCED_COMPONENT.fullmatch(coordinate) is not None
            or _PRODUCED_DIRECTIONAL.fullmatch(coordinate) is not None
        )
    return False


def _is_identity(value: object) -> bool:
    return isinstance(value, str) and _SIMPLE_IDENTITY.fullmatch(value) is not None


def _is_static_scientific_identity(value: object) -> bool:
    if not _is_identity(value):
        return False
    assert isinstance(value, str)
    collapsed = value.replace("_", "")
    parts = set(value.split("_")) | {collapsed}
    return not bool(parts & _FORBIDDEN_STATIC_IDENTITY_PARTS)


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _is_positive_finite(value: object) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    return math.isfinite(float(value)) and float(value) > 0.0


def _maximum_difference(
    baseline: tuple[float, ...],
    challenged: tuple[float, ...],
) -> float:
    return max(
        abs(first - second)
        for first, second in zip(baseline, challenged, strict=True)
    )
