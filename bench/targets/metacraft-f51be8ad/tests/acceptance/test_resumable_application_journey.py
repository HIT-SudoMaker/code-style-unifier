from __future__ import annotations

from dataclasses import replace
import base64
from decimal import Decimal
import hashlib
import gzip
import json
import os
from pathlib import Path
import shutil

import pytest

from metacraft.authority import Authority, Document, Reference
from metacraft.authority.session import AuthoritySession
from metacraft.canonical import encode_bytes
from metacraft.science import Result
from metacraft.science.consultation import (
    ConsultationAnswer,
    EvidenceRequired,
)
from metacraft.science.metalens import project_run_manifest
from metacraft.science.metalens.checkpoint import FRONTIER_SCHEMA
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.brief import MetalensBrief
from metacraft.science.result import ResultClosure
from metacraft.science.study import Study
from tests.resumable_journey_fixtures import (
    REPOSITORY_ROOT as ROOT,
    RESUMABLE_ROLE_NAMES,
    answer_consultation as _answer,
    consultation_request as _request,
    invoke_resumable_journey as _invoke,
    resumable_role_briefs as _role_briefs,
    run_resumable_journey as _run,
    run_resumable_journey_failure as _run_failure,
)


def _complete_role_journey(
    brief: MetalensBrief,
    tmp_path: Path,
    *,
    role_name: str,
) -> tuple[dict[str, object], tuple[tuple[str, str], ...]]:
    root = tmp_path / role_name
    root.mkdir()
    brief_path = root / "brief.json"
    brief_path.write_bytes(brief.canonical_bytes())
    material_path = root / "materials.toml"
    shutil.copyfile(ROOT / "materials" / "lumerical.toml", material_path)
    application_root = root / "application-root"
    original_brief = brief_path.read_bytes()

    period = _run(
        brief_path,
        application_root,
        material_path,
        evidence="recorded",
    )
    assert period["outcome"] == "consultation_required"
    authority = Authority(application_root / "authority")
    binding_reference = _external_binding_references(period)
    assert _advice_identities(period) == ()
    period_run = _project_observed_run(period, authority)
    period_revision = authority.view().revision
    assert _run(brief_path, application_root, material_path, evidence="none") == period
    assert authority.view().revision == period_revision
    period_answer = root / "period-answer.json"
    period_answer.write_bytes(_answer(period).document().to_bytes())
    stale_answer = root / "stale-answer.json"
    stale_answer.write_bytes(
        replace(
            _answer(period),
            request_identity="sha256:stale-request",
        )
        .document()
        .to_bytes()
    )
    assert (
        _run_failure(
            brief_path,
            application_root,
            material_path,
            evidence="none",
            answer=stale_answer,
        )
        == "consultation_answer_rejected:stale"
    )
    assert authority.view().revision == period_revision

    waiting = _run(
        brief_path,
        application_root,
        material_path,
        evidence="none",
        answer=period_answer,
    )
    assert waiting["outcome"] == "consultation_required"
    assert _request(waiting).question_kind.value == "height"
    assert _external_binding_references(waiting) == binding_reference
    period_advice = _advice_identities(waiting)
    assert len(period_advice) == 1
    height_run = _project_observed_run(waiting, authority)
    height_revision = authority.view().revision
    duplicate = _run_failure(
        brief_path,
        application_root,
        material_path,
        evidence="none",
        answer=period_answer,
    )
    assert duplicate == "consultation_answer_rejected:duplicate"
    assert authority.view().revision == height_revision
    height_answer = root / "height-answer.json"
    height_answer.write_bytes(_answer(waiting).document().to_bytes())
    waiting = _run(
        brief_path,
        application_root,
        material_path,
        evidence="none",
        answer=height_answer,
    )
    assert waiting["outcome"] == "waiting_studies"
    assert _external_binding_references(waiting) == binding_reference
    closed_advice = _advice_identities(waiting)
    assert len(closed_advice) == 2 and set(period_advice) < set(closed_advice)
    waiting_run = _project_observed_run(waiting, authority)
    waiting_revision = authority.view().revision
    assert _run(brief_path, application_root, material_path, evidence="none") == waiting
    assert authority.view().revision == waiting_revision

    work_before_interruption = _permit_work_identities(authority)
    interrupted = _invoke(
        brief_path,
        application_root,
        material_path,
        evidence="recorded-interrupt-after-receipt",
    )
    assert interrupted.returncode == 75
    assert interrupted.stdout == b""
    assert interrupted.stderr == b""
    interrupted_work = _permit_work_identities(authority)
    assert work_before_interruption < interrupted_work
    interrupted_receipts = _receipt_references(authority)
    assert interrupted_receipts
    assert all(permit.state == "closed" for permit in authority.view().permits)
    solves_after_interruption = _solve_identities(root)
    assert solves_after_interruption
    post_receipt = _run(
        brief_path,
        application_root,
        material_path,
        evidence="none",
    )
    assert post_receipt["outcome"] == "waiting_studies"
    assert _external_binding_references(post_receipt) == binding_reference
    assert _advice_identities(post_receipt) == closed_advice
    post_receipt_run = _project_observed_run(post_receipt, authority)

    completed = _run(
        brief_path,
        application_root,
        material_path,
        evidence="recorded",
    )
    assert completed["outcome"] == "completed_results", (
        _waiting_claims(completed),
        len(_receipt_references(authority)),
        tuple(
            (permit.state, permit.receipt_reference is not None)
            for permit in authority.view().permits
        ),
    )
    completed_work = _permit_work_identities(authority)
    assert interrupted_work < completed_work
    completed_result = _restore_result(completed, authority)
    assert binding_reference <= {
        reference.content_hash for reference in completed_result.closure.bindings
    }
    assert _compiled_advice_identities(completed_result) == closed_advice
    completed_run = _project_completed_run(completed_result, authority)
    completed_solves = _solve_identities(root)
    assert solves_after_interruption <= completed_solves
    assert len(completed_solves) == len(set(completed_solves))
    observed_runs = (
        period_run,
        height_run,
        waiting_run,
        post_receipt_run,
        completed_run,
    )
    assert tuple(item[0] for item in observed_runs) == tuple(
        sorted(item[0] for item in observed_runs)
    )
    assert all(item[1] for item in observed_runs)
    completed_revision = authority.view().revision
    replayed = _run(brief_path, application_root, material_path, evidence="poison")
    assert replayed == completed
    assert authority.view().revision == completed_revision
    assert authority.check().is_workspace_valid
    permits = authority.view().permits
    assert permits
    assert all(permit.state == "closed" for permit in permits)
    assert len({permit.permit_reference for permit in permits}) == len(permits)
    receipt_references = tuple(
        permit.receipt_reference
        for permit in permits
        if permit.receipt_reference is not None
    )
    assert len(set(receipt_references)) == len(receipt_references)
    authority_bytes = sum(
        path.stat().st_size
        for path in (application_root / "authority").iterdir()
        if path.is_file()
    )
    authority_budget = 8 * 1024 * 1024 + len(permits) ** 2 * 36 * 1024
    assert authority_bytes < authority_budget
    assert brief_path.read_bytes() == original_brief

    not_required = _run_failure(
        brief_path,
        application_root,
        material_path,
        evidence="poison",
        answer=height_answer,
    )
    assert not_required == "consultation_answer_rejected:duplicate"
    assert authority.view().revision == completed_revision

    run_signature = tuple((name, "admitted") for name in completed_run[1])
    return completed, run_signature


@pytest.mark.parametrize(
    ("role_name", "brief"),
    tuple(zip(RESUMABLE_ROLE_NAMES, _role_briefs(), strict=True)),
    ids=RESUMABLE_ROLE_NAMES,
)
@pytest.mark.integration
def test_four_roles_resume_one_authority_life_across_processes(
    role_name: str,
    brief: MetalensBrief,
    tmp_path: Path,
) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    first, first_run = _complete_role_journey(
        brief,
        first_root,
        role_name=role_name,
    )
    second, second_run = _complete_role_journey(
        brief,
        second_root,
        role_name=role_name,
    )
    assert _compact_science_signature(first) == _compact_science_signature(second)
    assert first_run == second_run


def test_unrequested_answer_does_not_begin_an_authority_life(tmp_path: Path) -> None:
    brief = _role_briefs()[0]
    brief_path = tmp_path / "brief.json"
    brief_path.write_bytes(brief.canonical_bytes())
    material_path = tmp_path / "materials.toml"
    shutil.copyfile(ROOT / "materials" / "lumerical.toml", material_path)
    answer_path = tmp_path / "unrequested-answer.json"
    answer_path.write_bytes(
        ConsultationAnswer(
            request_identity="sha256:unrequested",
            conclusion=EvidenceRequired(
                missing_fact="an emitted consultation",
                reason="no consultation has been emitted",
            ),
            external_claims=(),
        )
        .document()
        .to_bytes()
    )
    application_root = tmp_path / "unrequested-application-root"

    assert (
        _run_failure(
            brief_path,
            application_root,
            material_path,
            evidence="poison",
            answer=answer_path,
        )
        == "consultation_answer_rejected:not_required"
    )
    assert not application_root.exists()


def test_duplicate_answer_cannot_mutate_the_next_consultation(tmp_path: Path) -> None:
    base = _role_briefs()[0]
    brief = replace(
        base,
        aperture=None,
        omissions=tuple(dict.fromkeys((*base.omissions, "aperture"))),
    )
    brief_path = tmp_path / "brief.json"
    brief_path.write_bytes(brief.canonical_bytes())
    material_path = tmp_path / "materials.toml"
    shutil.copyfile(ROOT / "materials" / "lumerical.toml", material_path)
    application_root = tmp_path / "application-root"
    first = _run(brief_path, application_root, material_path, evidence="recorded")
    answer_path = tmp_path / "answer.json"
    answer_path.write_bytes(_answer(first).document().to_bytes())
    second = _run(
        brief_path,
        application_root,
        material_path,
        evidence="none",
        answer=answer_path,
    )
    assert second["outcome"] == "consultation_required"
    authority = Authority(application_root / "authority")
    revision = authority.view().revision

    assert (
        _run_failure(
            brief_path,
            application_root,
            material_path,
            evidence="none",
            answer=answer_path,
        )
        == "consultation_answer_rejected:duplicate"
    )
    assert authority.view().revision == revision


def test_pre_cutover_command_root_is_rejected_without_mutation(tmp_path: Path) -> None:
    historical_body = gzip.decompress(
        base64.b64decode(
            (
                ROOT
                / "tests/fixtures/aplanatic_reference/pre-cutover-high-na-study.b64"
            ).read_bytes()
        )
    )
    historical_study = Document.from_bytes(historical_body)
    brief = _role_briefs()[2]
    brief_identity = compile_metalens(brief).brief_identity
    brief_path = tmp_path / "brief.json"
    brief_path.write_bytes(brief.canonical_bytes())
    materials = tmp_path / "materials.toml"
    shutil.copyfile(ROOT / "materials" / "lumerical.toml", materials)
    application_root = tmp_path / "pre-cutover-root"
    application_root.mkdir()
    (application_root / "runs").mkdir()
    (application_root / "runs/.conduct.lock").write_bytes(b"\x00")
    authority = Authority(application_root / "authority")
    session = AuthoritySession(authority)
    encoded_objects = json.loads(
        gzip.decompress(
            base64.b64decode(
                (
                    ROOT
                    / "tests/fixtures/aplanatic_reference/pre-cutover-high-na-replay-objects.b64"
                ).read_bytes()
            )
        )
    )
    replay_references = tuple(
        session.admit_document(Document.from_bytes(base64.b64decode(body)))
        for body in encoded_objects.values()
    )
    session.admit_current(
        Document(
            FRONTIER_SCHEMA,
            {
                "brief_identity": brief_identity,
                "studies": {"study_001": historical_study.as_mapping()},
            },
        ),
        key=f"study_frontier:{brief_identity}",
        supersedes=None,
        references=replay_references,
    )
    before = _tree_bytes(application_root)

    completed = _invoke(
        brief_path,
        application_root,
        materials,
        evidence="none",
    )
    assert completed.returncode == 1
    assert completed.stdout == b""
    assert completed.stderr.rstrip().endswith(b"ValueError: study_frontier_invalid")
    assert _tree_bytes(application_root) == before


def test_compact_science_signature_ignores_closure_but_detects_physics() -> None:
    first = _signature_fixture("sha256:first-root", 1.0)
    equivalent = _signature_fixture("sha256:second-root", 1.0)
    changed = _signature_fixture("sha256:first-root", 1.1)
    assert _compact_science_signature(first) == _compact_science_signature(equivalent)
    assert _compact_science_signature(first) != _compact_science_signature(changed)
    ordered_run = (("brief", "complete"), ("evidence:field", "complete"))
    assert ordered_run != tuple(reversed(ordered_run))
    assert _without_authority_references(
        {"source": _reference_mapping("sha256:first")}
    ) == _without_authority_references({"source": _reference_mapping("sha256:second")})


def _signature_fixture(closure: str, peak: float) -> dict[str, object]:
    return {
        "value": {
            "results": [
                {
                    "document": {
                        "schema_identifier": "metacraft.result.fixture",
                        "values": {"closure": closure, "peak": peak},
                    }
                }
            ]
        }
    }


def _reference_mapping(content_hash: str) -> dict[str, object]:
    return {
        "content_hash": content_hash,
        "media_type": "application/json",
        "metadata_content_hash": "sha256:metadata",
        "size_bytes": 1,
    }


def _tree_bytes(root: Path) -> dict[Path, bytes]:
    return {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _waiting_claims(outcome: dict[str, object]) -> set[str]:
    value = outcome["value"]
    assert isinstance(value, dict)
    studies = value["studies"]
    assert isinstance(studies, list)
    claims: set[str] = set()
    for study in studies:
        assert isinstance(study, dict)
        values = study["values"]
        assert isinstance(values, dict)
        findings = values["findings"]
        assert isinstance(findings, dict)
        for finding in findings.values():
            assert isinstance(finding, dict)
            claims.add(str(finding["claim"]))
    return claims


def _external_binding_references(outcome: dict[str, object]) -> set[str]:
    value = outcome["value"]
    assert isinstance(value, dict)
    studies = value["studies"]
    assert isinstance(studies, list)
    references: set[str] = set()
    for study in studies:
        assert isinstance(study, dict)
        values = study["values"]
        assert isinstance(values, dict)
        bindings = values["bindings"]
        assert isinstance(bindings, dict)
        for binding in bindings.values():
            assert isinstance(binding, dict)
            if binding["capacity_scope"] is not None:
                reference = binding["reference"]
                assert isinstance(reference, dict)
                references.add(str(reference["content_hash"]))
    assert len(references) == 1
    return references


def _advice_identities(outcome: dict[str, object]) -> tuple[str, ...]:
    studies = _outcome_studies(outcome)
    assert len(studies) == 1
    return tuple(
        "sha256:" + hashlib.sha256(encode_bytes(advice.canonical_value())).hexdigest()
        for advice in studies[0].advice
    )


def _compiled_advice_identities(result: Result) -> tuple[str, ...]:
    return tuple(
        "sha256:" + hashlib.sha256(encode_bytes(advice.canonical_value())).hexdigest()
        for advice in result.closure.compiled.advice
    )


def _outcome_studies(outcome: dict[str, object]) -> tuple[Study, ...]:
    value = outcome["value"]
    assert isinstance(value, dict)
    encoded = value["studies"]
    assert isinstance(encoded, list)
    studies: list[Study] = []
    for mapping in encoded:
        assert isinstance(mapping, dict)
        studies.append(
            Study.from_document(
                Document(str(mapping["schema_identifier"]), mapping["values"])
            )
        )
    return tuple(studies)


def _project_observed_run(
    outcome: dict[str, object],
    authority: Authority,
) -> tuple[int, tuple[str, ...]]:
    studies = _outcome_studies(outcome)
    assert len(studies) == 1
    return _project_run(studies[0], authority)


def _project_completed_run(
    result: Result,
    authority: Authority,
) -> tuple[int, tuple[str, ...]]:
    return _project_run(
        result.closure.compiled,
        authority,
        provenance={
            "brief": result.closure.brief.reference,
            "study": result.closure.study.reference,
        },
    )


def _project_run(
    study: Study,
    authority: Authority,
    *,
    provenance: dict[str, Reference] | None = None,
) -> tuple[int, tuple[str, ...]]:
    view = authority.view()
    revision = len(view.decisions)
    references = {} if provenance is None else provenance
    manifest = project_run_manifest(
        study,
        authority_revision=revision,
        references=references,
    )
    expected = tuple(
        [*(name for name in ("brief", "study") if name in references)]
        + [*(f"evidence:{fact.claim}" for fact in study.evidence)]
        + [
            f"advice:{index:03d}"
            for index, advice in enumerate(study.advice, start=1)
            if tuple(_references_in(advice.canonical_value()))
        ]
        + [
            f"finding:{finding.claim}"
            for finding in study.findings
            if finding.record_references
        ]
    )
    assert manifest.authority_revision == len(authority.view().decisions)
    assert tuple(step.name for step in manifest.steps) == expected
    for reference in references.values():
        assert authority.fetch(reference)
    for step in manifest.steps:
        for reference in step.references:
            assert authority.fetch(reference)
    return revision, expected


def _references_in(value: object):
    if isinstance(value, Reference):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _references_in(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _references_in(item)


def _solve_identities(root: Path) -> tuple[tuple[str, str, str], ...]:
    ledger = root / "fixture-adapter" / "solve-ledger.jsonl"
    records = tuple(json.loads(line) for line in ledger.read_text().splitlines())
    identities = tuple(
        (str(item["work"]), str(item["before"]), str(item["after"])) for item in records
    )
    assert len(identities) == len(set(identities))
    return identities


def _permit_work_identities(authority: Authority) -> set[str]:
    identities: set[str] = set()
    permits = authority.view().permits
    for permit in permits:
        document = Document.from_bytes(authority.fetch(permit.body_reference))
        work_identity = document.values["work"]
        assert isinstance(work_identity, str)
        identities.add(work_identity)
    assert len(identities) == len(permits)
    return identities


def _receipt_references(authority: Authority) -> set[str]:
    return {
        permit.receipt_reference.content_hash
        for permit in authority.view().permits
        if permit.receipt_reference is not None
    }


def _restore_result(outcome: dict[str, object], authority: Authority) -> Result:
    value = outcome["value"]
    assert isinstance(value, dict)
    results = value["results"]
    assert isinstance(results, list) and len(results) == 1
    encoded = results[0]
    assert isinstance(encoded, dict)
    reference = Reference.from_mapping(encoded["reference"])
    document_mapping = encoded["document"]
    assert isinstance(document_mapping, dict)
    document = Document(
        str(document_mapping["schema_identifier"]),
        document_mapping["values"],
    )
    source_values = encoded["sources"]
    assert isinstance(source_values, list)
    sources = tuple(Reference.from_mapping(item) for item in source_values)
    closure_mapping = encoded["closure"]
    assert isinstance(closure_mapping, dict)
    study_reference = Reference.from_mapping(closure_mapping["study"])
    return Result(
        reference,
        document,
        sources,
        ResultClosure.restore(study_reference, fetch=authority.fetch),
    )


def _compact_science_signature(outcome: dict[str, object]) -> bytes:
    value = outcome["value"]
    assert isinstance(value, dict)
    results = value["results"]
    assert isinstance(results, list)
    scientific_documents: list[object] = []
    for encoded in results:
        assert isinstance(encoded, dict)
        document = encoded["document"]
        assert isinstance(document, dict)
        values = document["values"]
        assert isinstance(values, dict)
        # Closure references prove provenance separately.  The remaining
        # conclusion values are the root-independent scientific observation.
        scientific_documents.append(
            {
                "schema_identifier": document["schema_identifier"],
                "values": _without_authority_references(
                    {key: item for key, item in values.items() if key != "closure"}
                ),
            }
        )
    return json.dumps(
        scientific_documents,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def _without_authority_references(value: object) -> object:
    if isinstance(value, dict):
        if {"content_hash", "media_type", "metadata_content_hash", "size_bytes"} <= set(
            value
        ):
            return "<authority-reference>"
        return {key: _without_authority_references(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_without_authority_references(item) for item in value]
    return value
